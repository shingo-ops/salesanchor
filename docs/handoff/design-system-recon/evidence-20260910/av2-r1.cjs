// AV-2 recon2 R1: bare-select page rules vs existing Select/SelectControl mold usages. Read-only.
const fs = require('fs'), path = require('path');
const P = require('./av2-project.cjs'); const { ts, files, ROOT, rel, classTokens, full, isJsx, tagText, jsxAttr, opening, hasSpread, emptyTok, resolveExport } = P;
const C = require('./av2-css.cjs');
const SELECT_FILE = path.join(ROOT, 'frontend/src/components/Select.tsx');
const lineOf = (fi, n) => fi.sf.getLineAndCharacterOfPosition(n.getStart(fi.sf)).line + 1;
const key = r => r.file + ':' + r.line;

// bare select rules inventory
const bare = C.cssRules.filter(r => { const l = r.parsed.compounds[r.parsed.compounds.length - 1]; return l.tag === 'select' && !l.classes.length && !l.ids.length && !l.attrs.length; });
const bareRules = bare.map(r => { const l = r.parsed.compounds[r.parsed.compounds.length - 1]; return { id: key(r) + ' ' + r.selector, file: r.file, line: r.line, selector: r.selector, spec: r.parsed.spec, media: r.media || null, lastPseudo: [...l.pseudos, ...l.pseudoEls, ...l.funcPseudos].join('') || null, decls: r.decls.map(d => d.prop + ': ' + C.normV(d.value) + (d.important ? ' !important' : '') + ' (L' + d.line + ')') }; });

// mold declared props
const moldDecl = {};
for (const r of C.cssRules) if (r.file === 'frontend/src/components/FormField.css') for (const l of [r.parsed.compounds[r.parsed.compounds.length - 1]]) if (l.classes.some(c => c === 'comp-select__control' || c === 'comp-field__select' || /^comp-select__control--/.test(c))) {
  const k = l.classes[0] + (l.pseudos.join('') || ''); (moldDecl[k] = moldDecl[k] || []).push({ line: r.line, selector: r.selector, spec: r.parsed.spec, props: r.decls.map(d => d.prop) });
}

// usages
const usages = [];
for (const fi of files.values()) {
  if (fi.abs === SELECT_FILE) continue;
  const v = n => {
    if (isJsx(n)) {
      const T = tagText(n);
      if (T === 'Select' || T === 'SelectControl') {
        const im = fi.imports.get(T);
        const r = im && resolveExport(im.file, im.name);
        if (r && r.file === SELECT_FILE) usages.push({ fi, el: n, T });
      }
    }
    ts.forEachChild(n, v);
  };
  v(fi.sf);
}
usages.sort((a, b) => a.fi.rel.localeCompare(b.fi.rel) || a.el.getStart(a.fi.sf) - b.el.getStart(b.fi.sf));

const litAttr = (el, n) => { const a = jsxAttr(el, n); if (!a) return null; const i = a.initializer; if (!i) return 'true'; if (ts.isStringLiteral(i)) return i.text; if (ts.isJsxExpression(i) && i.expression && (ts.isStringLiteral(i.expression) || ts.isNoSubstitutionTemplateLiteral(i.expression))) return i.expression.text; return '(dynamic:' + i.getText().slice(0, 40) + ')'; };
const mkTok = (st, base) => ({ prefixes: base.prefixes || new Set(), st: new Set([...st, ...base.st]), cond: base.cond, unresolved: base.unresolved });

const rows = [];
for (const { fi, el, T } of usages) {
  const cn = jsxAttr(el, 'className');
  const ct = cn && cn.initializer ? classTokens(fi, cn.initializer) : emptyTok();
  const chains = full(fi, el, 0);
  let tokens, ch, selectClass, appearance = null;
  const idAttr = jsxAttr(el, 'id');
  const attrNames = new Set(opening(el).attributes.properties.filter(a => ts.isJsxAttribute(a)).map(a => a.name.getText()));
  const spread = hasSpread(el);
  if (T === 'SelectControl') {
    appearance = litAttr(el, 'appearance') || 'bare(default)';
    selectClass = appearance === 'field' ? 'comp-field__select' : 'comp-select__control';
    if (/dynamic/.test(appearance)) selectClass = 'comp-select__control|comp-field__select(dynamic appearance)';
    tokens = mkTok(selectClass.includes('|') ? ['comp-select__control', 'comp-field__select'] : [selectClass], ct);
    ch = chains;
  } else {
    selectClass = 'comp-field__select';
    tokens = mkTok(['comp-field__select'], emptyTok()); // className goes to the wrapper div, not the select
    const div = { k: 'dom', tag: 'div', st: new Set(['comp-field', ...ct.st]), cond: ct.cond, maybe: new Set(), unresolved: ct.unresolved && ct.other, propFwd: false, prefixes: ct.prefixes, spread: false, loc: 'Select.tsx wrapper div' };
    ch = chains.map(c => ({ entries: [div].concat(c.entries), closed: c.closed }));
  }
  const sel = { tokens, chains: ch, attrNames, idLit: undefined, spread: false };
  const m = C.matchRules(sel, r => bare.includes(r));
  rows.push({ file: fi.rel, line: lineOf(fi, el), tag: T, appearance, selectClass, wrapperClassName: T === 'Select' ? (cn && cn.initializer ? cn.initializer.getText().slice(0, 120) : null) : null, chainCount: chains.length, matched: m.map(x => ({ id: key(x.rule) + ' ' + x.rule.selector, status: x.status, whys: x.whys })) });
}

// per rule aggregation
const rawRows = require('./av2-select-mapping.json').rows;
const out = { baseSha: '3210edeea250e269102bedd3546ebc48ddb89b77', usageCounts: { total: rows.length, Select: rows.filter(r => r.tag === 'Select').length, SelectControl: rows.filter(r => r.tag === 'SelectControl').length }, moldDeclared: moldDecl, bareRuleInventory: bareRules, perRule: [] };
for (const br of bareRules) {
  const spec = br.spec; const specStr = '(' + spec.join(',') + ')';
  const cmp = (a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2];
  const vs = cmp(spec, [0, 1, 0]);
  const usageMatches = rows.filter(r => r.matched.some(x => x.id === br.id));
  const def = usageMatches.filter(r => r.matched.find(x => x.id === br.id).status === 'definite');
  const rawM = rawRows.filter(r => [...r.appliedRules, ...r.unconfirmedRules].some(x => x.file + ':' + x.line + ' ' + x.selector === br.id)).map(r => ({ at: r.file + ':' + r.line, status: [...r.appliedRules, ...r.unconfirmedRules].find(x => x.file + ':' + x.line + ' ' + x.selector === br.id).status, cls: r.classification }));
  out.perRule.push({ rule: br.id, spec: specStr, media: br.media, lastPseudo: br.lastPseudo, vsMoldControl_0_1_0: vs > 0 ? 'rule wins (higher specificity)' : vs < 0 ? 'mold wins (lower rule specificity)' : 'tie: later source order wins (cross-file, import-order dependent)', decls: br.decls, moldUsagesMatching: { definite: def.length, any: usageMatches.length, list: usageMatches.map(r => ({ at: r.file + ':' + r.line, tag: r.tag, class: r.selectClass, status: r.matched.find(x => x.id === br.id).status, whys: r.matched.find(x => x.id === br.id).whys })) }, rawSelectsMatching: { count: rawM.length, list: rawM } });
}
out.usageRows = rows;
fs.writeFileSync(path.join(ROOT, 'out/av2-r1.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out.usageCounts), 'bare rules', bareRules.length);
for (const p of out.perRule) console.log(p.spec, p.rule, '| mold usages definite/any', p.moldUsagesMatching.definite + '/' + p.moldUsagesMatching.any, '| raw', p.rawSelectsMatching.count, '|', p.vsMoldControl_0_1_0);
