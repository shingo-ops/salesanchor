// AX-2 step 3: Chromium computed-style baseline for the 53 raw <textarea> (before) and TextareaControl (after), 1280px light.
// usage: node ax2-baseline.cjs   (reads ax2-applied-css.json; writes ax2-baseline.json)
const fs = require('fs'), path = require('path'), os = require('os');
const W = '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-textarea-ax2a';
const { chromium } = require(path.join(W, 'frontend/node_modules/playwright'));
const SRC = path.join(W, 'frontend/src');
const rdRel = f => fs.readFileSync(path.join(W, f), 'utf8');
const applied = require('./ax2-applied-css.json');
const FORM_FIELD = 'frontend/src/components/FormField.css';
const idxCss = rdRel('frontend/src/index.css')
  .replace(/@import\s+"\.\/tokens\.css";/, () => rdRel('frontend/src/tokens.css'))
  .replace(/@import\s+"\.\/components\/field-size\.css";/, () => rdRel('frontend/src/components/field-size.css'));
const cssFor = (row) => {
  const order = ['frontend/src/index.css', ...applied.globalCss.filter(f => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)),
    ...row.cssImports.forwardClosure, ...row.cssImports.reverseImportersCss].filter((v, i, a) => a.indexOf(v) === i && v !== FORM_FIELD);
  order.push(FORM_FIELD);
  return { order, html: order.map(f => `<style data-f="${f}">${f.endsWith('/index.css') ? idxCss : rdRel(f)}</style>`).join('\n') };
};
const PROPS = [
  'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
  'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
  'border-top-style', 'border-right-style', 'border-bottom-style', 'border-left-style',
  'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
  'border-top-left-radius', 'border-top-right-radius', 'border-bottom-right-radius', 'border-bottom-left-radius',
  'font-size', 'font-family', 'line-height', 'color', 'background-color',
  'height', 'min-height', 'width', 'max-width', 'resize', 'outline-style', 'outline-width', 'outline-color', 'outline-offset',
  'box-shadow', 'box-sizing', 'cursor', 'opacity',
];
const parseRows = s => { const m = /^\{?\s*(\d+)\s*\}?$/.exec(s || ''); return m ? m[1] : null; };
const kebabToCamel = s => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
function inlineCss(style) { // only literal values
  return (style.props || []).filter(p => p.prop[0] !== '(').map(p => `${p.prop}:${String(p.value).replace(/^['"]|['"]$/g, '')}`).join(';');
}
async function measure(page, cssHtml, spec) {
  // spec: {ancestors:[{tag,classes}] innermost-first, cls, rows, disabledAttr, required, style}
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${cssHtml}</head><body></body></html>`);
  const res = await page.evaluate(({ spec, PROPS }) => {
    let parent = document.body;
    for (const a of [...spec.ancestors].reverse()) { const e = document.createElement(a.tag); if (a.classes.length) e.className = a.classes.join(' '); parent.appendChild(e); parent = e; }
    const t = document.createElement('textarea'); t.id = 't'; if (spec.cls) t.className = spec.cls; if (spec.rows) t.setAttribute('rows', spec.rows); if (spec.required) t.required = true; if (spec.style) t.setAttribute('style', spec.style); parent.appendChild(t);
    return true;
  }, { spec, PROPS });
  const grab = async () => page.locator('#t').evaluate((e, props) => { const c = getComputedStyle(e); const o = {}; for (const k of props) o[k] = c.getPropertyValue(k); o.offsetHeight = e.offsetHeight; o.offsetWidth = e.offsetWidth; o._focused = document.activeElement === e; return o; }, PROPS);
  const out = {};
  const h = page.locator('#t');
  await page.mouse.move(1, 1);
  out.normal = await grab();
  await h.focus(); await page.waitForTimeout(300); out.focus = await grab();
  await h.evaluate(e => e.blur());
  if (spec.hasDisabled) { await h.evaluate(e => { e.disabled = true; }); await page.waitForTimeout(300); out.disabled = await grab(); }
  return out;
}
(async () => {
  const exe = path.join(os.homedir(), 'Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell');
  const b = await chromium.launch({ executablePath: exe });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage(); const warns = [];
  page.on('console', m => warns.push(m.type() + ': ' + m.text())); page.on('pageerror', e => warns.push('pageerror ' + e));
  const result = { chromium: b.version(), viewport: '1280x800 light', props: PROPS, bareMold: {}, rows: [] };
  // bare mold (no ancestors), CSS = index + FormField only
  const bareCss = `<style>${idxCss}</style><style>${rdRel(FORM_FIELD)}</style>`;
  for (const [k, cls] of [['md', 'comp-field__textarea'], ['sm', 'comp-field__textarea comp-field__textarea--sm'], ['lg', 'comp-field__textarea comp-field__textarea--lg']]) {
    result.bareMold[k] = await measure(page, bareCss, { ancestors: [], cls, rows: null, hasDisabled: true });
    result.bareMold[k + '+rows3'] = await measure(page, bareCss, { ancestors: [], cls, rows: '3', hasDisabled: true });
  }
  for (const row of applied.rows) {
    const { order, html } = cssFor(row);
    const rowsAttr = row.attrs.rows ? parseRows(row.attrs.rows) : null;
    const hasDisabled = !!row.attrs.disabled;
    const style = inlineCss(row.inlineStyle);
    const cls = row.className.staticTokens.join(' ');
    const variants = [];
    const sigs = row.chains.distinctSignatures.slice(0, 20);
    if (!sigs.length) sigs.push({ ancestorsInnermostFirst: [], unknown: ['no chain'], count: 0 });
    for (const [i, sig] of sigs.entries()) {
      const anc = sig.ancestorsInnermostFirst.map(e => ({ tag: e.tag, classes: e.classes }));
      const base = { ancestors: anc, rows: rowsAttr, required: !!row.attrs.required, hasDisabled };
      const before = await measure(page, html, { ...base, cls, style });
      const afterMd = await measure(page, html, { ...base, cls: 'comp-field__textarea' });
      const afterSm = await measure(page, html, { ...base, cls: 'comp-field__textarea comp-field__textarea--sm' });
      variants.push({ sig: i, ancestors: sig.ancestorsInnermostFirst.map(e => e.tag + e.classes.map(c => '.' + c).join('')), conditionalAncestorClasses: sig.ancestorsInnermostFirst.flatMap(e => e.cond), unknownReasons: sig.unknown, before, afterMd, afterSm });
    }
    const bareBase = { ancestors: [], rows: rowsAttr, required: !!row.attrs.required, hasDisabled };
    const bare = { md: await measure(page, bareCss, { ...bareBase, cls: 'comp-field__textarea' }), sm: await measure(page, bareCss, { ...bareBase, cls: 'comp-field__textarea comp-field__textarea--sm' }) };
    result.rows.push({ file: row.file, line: row.line, cssOrder: order, rowsAttr, hasDisabled, inlineStyleApplied: style, ownClass: cls, variants, bare });
    process.stderr.write('.');
  }
  result.warnings = warns;
  await b.close();
  fs.writeFileSync(path.join(__dirname, 'ax2-baseline.json'), JSON.stringify(result, null, 1));
  console.log('\nrows', result.rows.length, 'variants', result.rows.reduce((a, r) => a + r.variants.length, 0), 'warnings', warns.length, result.chromium);
})();
