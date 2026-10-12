// AV-0 read-only scanner. Usage: node av0-input-audit.cjs <snapshotRoot> <tsRoot> <outDir>
const fs = require('fs'), path = require('path');
const [root, tsRoot, outDir] = process.argv.slice(2);
const ts = require(path.join(tsRoot, 'node_modules/typescript'));
const MOLDS = new Set(['Select.tsx', 'TextField.tsx', 'Textarea.tsx']);
const isValidUiAllow = l => /ui-allow:\s+\S+.*\(#\d+\)/.test(l);
const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => {
  const p = path.join(d, e.name);
  return e.isDirectory() ? walk(p) : [p];
});
const files = walk(path.join(root, 'frontend/src')).filter(f => f.endsWith('.tsx'));
const excluded = files.filter(f => /\.(stories|test)\.tsx$/.test(f)).length;
const targets = files.filter(f => !/\.(stories|test)\.tsx$/.test(f)).sort();
const TAGS = new Set(['select', 'textarea', 'input']);
const EVENTS = ['onChange', 'onBlur', 'onKeyDown', 'onFocus', 'onInput'];
const FLAGS = ['value', 'defaultValue', 'checked', 'defaultChecked', 'ref', 'name', 'id', 'disabled', 'required', 'readOnly', 'placeholder', ...EVENTS];
const rows = [], errors = [];
for (const abs of targets) {
  const rel = path.relative(root, abs);
  const src = fs.readFileSync(abs, 'utf8'), lines = src.split('\n');
  const sf = ts.createSourceFile(rel, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  for (const d of sf.parseDiagnostics) errors.push({ file: rel, msg: ts.flattenDiagnosticMessageText(d.messageText, ' ') });
  const comp = n => {
    for (let p = n.parent; p; p = p.parent) {
      if ((ts.isFunctionDeclaration(p) || ts.isClassDeclaration(p)) && p.name && /^[A-Z]/.test(p.name.text)) return p.name.text;
      if (ts.isVariableDeclaration(p) && ts.isIdentifier(p.name) && /^[A-Z]/.test(p.name.text)) return p.name.text;
    }
    return null;
  };
  const visit = n => {
    if (ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) {
      const tag = n.tagName.getText(sf);
      if (TAGS.has(tag)) {
        const attrs = {}, spreads = [];
        for (const a of n.attributes.properties) {
          if (ts.isJsxSpreadAttribute(a)) spreads.push(a.expression.getText(sf));
          else attrs[a.name.getText(sf)] = a.initializer ? a.initializer.getText(sf) : 'true';
        }
        const line = sf.getLineAndCharacterOfPosition(n.getStart(sf)).line;
        let type = null;
        if (tag === 'input') {
          if (!('type' in attrs)) type = spreads.length ? 'omitted+spread' : 'omitted';
          else if (/^"[^"]*"$/.test(attrs.type) || /^\{\s*["'][^"']*["']\s*\}$/.test(attrs.type)) type = attrs.type.replace(/^\{?\s*["']|["']\s*\}?$/g, '');
          else type = 'dynamic:' + attrs.type;
        }
        const t = v => (v ? /\bt\(/.test(v) : null);
        let children = null;
        if (tag === 'select' && ts.isJsxOpeningElement(n)) {
          const ch = n.parent.children.filter(c => !(ts.isJsxText(c) && !c.getText(sf).trim()));
          children = { count: ch.length, hasMap: ch.some(c => /\.map\(/.test(c.getText(sf))), staticOptions: ch.filter(c => (ts.isJsxElement(c) && c.openingElement.tagName.getText(sf) === 'option') || (ts.isJsxSelfClosingElement(c) && c.tagName.getText(sf) === 'option')).length };
        }
        const row = {
          file: rel, line: line + 1, tag, type, component: comp(n),
          scope: MOLDS.has(path.basename(rel)) && rel.startsWith('frontend/src/components/') && path.dirname(rel) === 'frontend/src/components' ? 'mold' : 'page',
          attrNames: Object.keys(attrs).sort(),
          has: Object.fromEntries(FLAGS.map(f => [f, f in attrs])),
          placeholderUsesT: t(attrs.placeholder), ariaLabelUsesT: 'aria-label' in attrs ? t(attrs['aria-label']) : null,
          hasAriaLabel: 'aria-label' in attrs,
          className: 'className' in attrs ? attrs.className : null,
          hasStyle: 'style' in attrs,
          spread: spreads.length > 0, spreads,
          uiAllow: isValidUiAllow(lines[line]) || (line > 0 && isValidUiAllow(lines[line - 1])),
          children,
        };
        rows.push(row);
      }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
}
const cnt = (arr, f) => arr.reduce((m, r) => { const k = f(r); m[k] = (m[k] || 0) + 1; return m; }, {});
const baseType = r => r.tag === 'input' ? (r.type.startsWith('dynamic') ? 'dynamic' : r.type) : '-';
const counts = {
  total: rows.length, byTag: cnt(rows, r => r.tag),
  byTagType: cnt(rows, r => r.tag + '/' + baseType(r)),
  byUiAllow: cnt(rows, r => r.uiAllow ? 'ui-allow' : 'none'),
  byScope: cnt(rows, r => r.scope + ':' + r.tag),
  byFile: cnt(rows, r => r.file),
};
const out = { basis: { snapshotRoot: root, scannedFiles: targets.length, excludedStoriesTests: excluded, ts: ts.version, parseErrors: errors }, counts, rows };
fs.writeFileSync(path.join(outDir, 'av0-input-audit.json'), JSON.stringify(out, null, 2));
const tbl = (o, h) => `|${h[0]}|${h[1]}|\n|---|---:|\n` + Object.entries(o).sort((a, b) => b[1] - a[1]).map(([k, v]) => `|${k}|${v}|`).join('\n');
const top = Object.entries(counts.byFile).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 20);
const BASE = process.env.BASE_SHA || '(unset)';
const md = `# AV-0 入力要素 再棚卸し\n\n基準 SHA: ${BASE} / TypeScript ${ts.version}\n\nTypeScript ${ts.version} AST。対象TSX ${targets.length}ファイル（stories/test ${excluded}件除外）、構文エラー${errors.length}。合計 ${rows.length}。\n\n## タグ別\n${tbl(counts.byTag, ['tag', 'n'])}\n\n## タグ/type別\n${tbl(counts.byTagType, ['tag/type', 'n'])}\n\n## ui-allow\n${tbl(counts.byUiAllow, ['ui-allow', 'n'])}\n\n## 金型ファイル内 / ページ側\n${tbl(counts.byScope, ['scope:tag', 'n'])}\n\n## 上位20ファイル\n|file|n|\n|---|---:|\n${top.map(([f, n]) => `|${f}|${n}|`).join('\n')}\n\n## spread属性あり\n${rows.filter(r => r.spread).map(r => `- ${r.file}:${r.line} <${r.tag}> type=${r.type} spread=${r.spreads.join(',')}`).join('\n') || 'なし'}\n\n## type動的\n${rows.filter(r => r.type && r.type.startsWith('dynamic')).map(r => `- ${r.file}:${r.line} ${r.type}`).join('\n') || 'なし'}\n\n## ui-allow付き\n${rows.filter(r => r.uiAllow).map(r => `- ${r.file}:${r.line} <${r.tag}>`).join('\n') || 'なし'}\n`;
fs.writeFileSync(path.join(outDir, 'av0-input-audit.md'), md);
console.log(JSON.stringify({ basis: out.basis, counts: { ...counts, byFile: undefined } }, null, 2));
