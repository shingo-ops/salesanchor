// AY-2 step 4: Chromium computed-style baseline for text-like raw <input> groups (before) vs TextFieldControl standard md/sm (after), 1280px light.
// usage: node ay2-baseline.cjs  (reads ay2-applied-css.json + ay2-groups.json; writes ay2-baseline.json)
const fs = require('fs'), path = require('path'), os = require('os');
const W = '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-textfield-ay2a';
const { chromium } = require(path.join(W, 'frontend/node_modules/playwright'));
const rdRel = f => fs.readFileSync(path.join(W, f), 'utf8');
const applied = require('./ay2-applied-css.json');
const groups = require('./ay2-groups.json').groups;
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
  // AY-2 additions (layout-affecting)
  'display', 'min-width', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left', 'flex-grow', 'flex-basis', 'text-align',
];
function inlineCss(style) { return (style.props || []).filter(p => p.prop[0] !== '(').map(p => `${p.prop}:${String(p.value).replace(/^['"]|['"]$/g, '')}`).join(';'); }
async function measure(page, cssHtml, spec) {
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${cssHtml}</head><body></body></html>`);
  await page.evaluate(({ spec }) => {
    let parent = document.body;
    for (const a of [...spec.ancestors].reverse()) { const e = document.createElement(a.tag); if (a.classes.length) e.className = a.classes.join(' '); parent.appendChild(e); parent = e; }
    const t = document.createElement('input'); t.id = 't'; if (spec.type) t.setAttribute('type', spec.type); if (spec.cls) t.className = spec.cls; if (spec.style) t.setAttribute('style', spec.style); parent.appendChild(t);
  }, { spec });
  const grab = async () => page.locator('#t').evaluate((e, props) => { const c = getComputedStyle(e); const o = {}; for (const k of props) o[k] = c.getPropertyValue(k); o.offsetHeight = e.offsetHeight; o.offsetWidth = e.offsetWidth; o._focused = document.activeElement === e; return o; }, PROPS);
  const out = {}; const h = page.locator('#t');
  await page.mouse.move(1, 1);
  out.normal = await grab();
  await h.focus(); await page.waitForTimeout(250); out.focus = await grab();
  await h.evaluate(e => e.blur());
  if (spec.hasDisabled) { await h.evaluate(e => { e.disabled = true; }); await page.waitForTimeout(250); out.disabled = await grab(); }
  return out;
}
(async () => {
  const exe = path.join(os.homedir(), 'Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell');
  const b = await chromium.launch({ executablePath: exe });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: 'light' });
  const page = await ctx.newPage(); const warns = [];
  page.on('console', m => warns.push(m.type() + ': ' + m.text())); page.on('pageerror', e => warns.push('pageerror ' + e));
  const result = { chromium: b.version(), viewport: '1280x800 light', props: PROPS, cssOrderNote: 'FormField.css appended last after all other CSS (same assumption as ax2-baseline)', bareMold: {}, groups: [] };
  const bareCss = `<style>${idxCss}</style><style>${rdRel(FORM_FIELD)}</style>`;
  for (const t of ['text', 'number', 'date', 'time', 'datetime-local', 'email', 'password', 'tel', 'url', 'search', null]) {
    const k = t || 'omitted';
    for (const [sz, cls] of [['md', 'comp-field__input'], ['sm', 'comp-field__input comp-field__input--sm'], ['lg', 'comp-field__input comp-field__input--lg']])
      result.bareMold[k + '/' + sz] = await measure(page, bareCss, { ancestors: [], type: t, cls, hasDisabled: true });
  }
  const byKey = new Map(applied.rows.map(r => [r.file + ':' + r.line, r]));
  for (const g of groups) {
    const members = g.count <= 5 ? g.members : [g.members[0]];
    const gOut = { id: g.id, count: g.count, measuredAll: g.count <= 5, measured: [] };
    for (const m of members) {
      const row = byKey.get(m.file + ':' + m.line);
      const { order, html } = cssFor(row);
      const type = row.type === 'omitted' ? null : row.type === 'dynamic' ? 'text' : row.type;
      const hasDisabled = !!row.attrs.disabled;
      const style = inlineCss(row.inlineStyle); const cls = row.className.staticTokens.join(' ');
      const sigs = row.chains.distinctSignatures.slice(0, 20); if (!sigs.length) sigs.push({ ancestorsInnermostFirst: [], unknown: ['no chain'], count: 0 });
      const variants = [];
      for (const [i, sig] of sigs.entries()) {
        const anc = sig.ancestorsInnermostFirst.map(e => ({ tag: e.tag, classes: e.classes }));
        const base = { ancestors: anc, type, hasDisabled };
        variants.push({ sig: i, ancestors: sig.ancestorsInnermostFirst.map(e => e.tag + e.classes.map(c => '.' + c).join('')), unknown: sig.unknown,
          before: await measure(page, html, { ...base, cls, style }),
          afterMd: await measure(page, html, { ...base, cls: 'comp-field__input' }),
          afterSm: await measure(page, html, { ...base, cls: 'comp-field__input comp-field__input--sm' }) });
      }
      gOut.measured.push({ file: m.file, line: m.line, type: row.type, hasDisabled, inlineStyleApplied: style, ownClass: cls, inlineUnresolved: !!row.inlineStyle.unresolved, cssOrder: order, variants });
      process.stderr.write('.');
    }
    result.groups.push(gOut);
  }
  result.warnings = warns;
  await b.close();
  fs.writeFileSync(path.join(__dirname, 'ay2-baseline.json'), JSON.stringify(result, null, 1));
  console.log('\ngroups', result.groups.length, 'measured', result.groups.reduce((a, g) => a + g.measured.length, 0), 'variants', result.groups.reduce((a, g) => a + g.measured.reduce((x, m) => x + m.variants.length, 0), 0), 'warnings', warns.length, result.chromium);
})();
