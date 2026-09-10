import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { resolve, join } from 'node:path';
import { runInNewContext } from 'node:vm';

// Usage: node verify-color-source.mjs REPOSITORY PROPOSAL_ROOT AUDIT_JSON [DEPENDENCY_FRONTEND]
// The optional dependency root is for explicitly labelled supplemental draft verification.
const [repositoryArg, proposalArg, auditArg, dependencyArg, ...extra] = process.argv.slice(2);
assert.ok(repositoryArg && proposalArg && auditArg && extra.length === 0,
  'Usage: node verify-color-source.mjs REPOSITORY PROPOSAL_ROOT AUDIT_JSON [DEPENDENCY_FRONTEND]');
const repository = resolve(repositoryArg);
const proposal = resolve(proposalArg);
const dependencies = resolve(dependencyArg ?? join(repository, 'frontend'));
const require = createRequire(join(dependencies, 'package.json'));
const postcss = require('postcss');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { chromium } = require('playwright');
const audit = JSON.parse(await readFile(resolve(auditArg), 'utf8'));
const baseline = audit.baseline;
const gitRead = (file) => execFileSync('git', ['show', `${baseline}:${file}`], {
  cwd: repository, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024,
});
const files = [...new Set(['frontend/src/index.css', ...audit.usages.map((r) => r.file)])];
assert.equal(files.length, 7);
const texts = { before: {}, after: {} };
for (const file of files) {
  texts.before[file] = gitRead(file);
  texts.after[file] = await readFile(join(proposal, file), 'utf8');
}
const tokens = gitRead('frontend/src/tokens.css');
const stylesheetFiles = files.filter((f) => f.endsWith('.css'));
const indexFile = 'frontend/src/index.css';
const iconFile = 'frontend/src/constants/icons.tsx';
const report = { baseline, repository, proposal, dependencies,
  supplemental: dependencyArg !== undefined, tokens: [], cases: [], staticResolutions: [],
  limits: ['Local CSS fixtures and actual PlatformIcon server rendering, not full-page PO visual approval.'] };

function definitions(css, theme) {
  const map = new Map();
  const ast = postcss.parse(css);
  const allowed = theme === 'dark' ? [':root', ':root.force-dark'] : [':root'];
  for (const selector of allowed) {
    const inScope = new Set();
    ast.walkDecls((decl) => {
      if (decl.parent.type !== 'rule' || decl.parent.parent !== ast || decl.parent.selector !== selector) return;
      if (!decl.prop.startsWith('--')) return;
      assert.ok(!inScope.has(decl.prop), `Duplicate ${selector} ${decl.prop}`);
      inScope.add(decl.prop);
      map.set(decl.prop, decl.value);
    });
  }
  return map;
}
function resolveColor(map, name, stack = []) {
  assert.ok(!stack.includes(name), `Cycle: ${[...stack, name].join(' -> ')}`);
  assert.ok(map.has(name), `Missing token ${name}`);
  const value = map.get(name).trim();
  const ref = /^var\((--[\w-]+)\)$/.exec(value);
  if (ref) return resolveColor(map, ref[1], [...stack, name]);
  assert.match(value, /^#[\da-f]{6}$/i, `Unexpected color grammar: ${name}=${value}`);
  return value.toLowerCase();
}
function rgb(hex) {
  assert.match(hex, /^#[\da-f]{6}$/i);
  return `rgb(${[1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16)).join(', ')})`;
}
const maps = {};
for (const theme of ['light', 'dark']) {
  maps[theme] = Object.fromEntries(['before', 'after'].map((side) => [side, definitions(texts[side][indexFile], theme)]));
  for (const row of audit.existing_declarations.filter((r) => r.theme === theme)) {
    const oldValue = resolveColor(maps[theme].before, row.name);
    const newValue = resolveColor(maps[theme].after, row.name);
    assert.equal(oldValue, row.before.toLowerCase());
    assert.equal(newValue, oldValue);
    report.staticResolutions.push({ theme, token: row.name, oldValue, newValue });
  }
  for (const row of audit.aliases) {
    const source = /^var\((--[\w-]+)\)$/.exec(row.after)?.[1];
    assert.ok(source);
    assert.ok(!maps[theme].before.has(row.name), `Unexpected baseline alias ${row.name}`);
    const oldValue = resolveColor(maps[theme].before, source);
    const newValue = resolveColor(maps[theme].after, row.name);
    assert.equal(oldValue, row[theme].toLowerCase());
    assert.equal(newValue, oldValue);
    report.staticResolutions.push({ theme, token: row.name, source, oldValue, newValue });
  }
}

function actualPlatformComponent(source) {
  // Evaluate the whole real icons.tsx twice; only CSS loading is handled separately by the fixture.
  const transformed = ts.transpileModule(source, { fileName: 'icons.tsx', reportDiagnostics: true,
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } });
  assert.equal((transformed.diagnostics ?? []).filter((d) => d.category === ts.DiagnosticCategory.Error).length, 0);
  const module = { exports: {} };
  const localRequire = (name) => {
    if (name === './platform-icon.css') return {};
    return require(name);
  };
  runInNewContext(transformed.outputText, { exports: module.exports, module, require: localRequire },
    { filename: 'actual-icons.cjs', timeout: 10000 });
  assert.equal(typeof module.exports.PlatformIcon, 'function');
  return module.exports.PlatformIcon;
}
const component = Object.fromEntries(['before', 'after'].map((s) => [s, actualPlatformComponent(texts[s][iconFile])]));
const fixtureCases = [
  { id: 'action', tag: 'button', className: 'icon-btn', token: '--icon-action' },
  { id: 'hover', tag: 'button', className: 'icon-btn', token: '--icon-action-hover', hover: true },
  { id: 'danger', tag: 'button', className: 'icon-btn danger', token: '--icon-action-danger', hover: true },
  { id: 'empty', tag: 'span', className: 'comp-empty__icon', token: '--icon-empty' },
  { id: 'decorative', tag: 'span', className: 'db-section-icon', token: '--icon-decorative' },
  { id: 'search', tag: 'span', className: 'inbox-search-icon', token: '--icon-search' },
  { id: 'lock', tag: 'span', className: 'karte-lock-icon', token: '--icon-status-success' },
];
const mailCases = ['mail', 'email'].flatMap((platform) => [undefined, 16, 20, 24].map((size) => ({
  id: `${platform}-${size ?? 'default'}`, platform, size,
})));
function fixture(side, theme) {
  const styles = [tokens, ...stylesheetFiles.map((f) => texts[side][f])].map((css) => {
    const ast = postcss.parse(css);
    // All real relevant sheets are already supplied. Disable network imports only in this local fixture.
    ast.walkAtRules('import', (rule) => rule.remove());
    return ast.toString();
  }).join('\n');
  const controls = fixtureCases.map((c) => `<${c.tag} id="${c.id}" class="${c.className}">X</${c.tag}>`).join('');
  const mail = mailCases.map((c) => `<div id="${c.id}">${renderToStaticMarkup(React.createElement(component[side], {
    platform: c.platform, ...(c.size === undefined ? {} : { size: c.size }),
  }))}</div>`).join('');
  return `<!doctype html><html class="${theme === 'dark' ? 'force-dark' : ''}"><head><style>${styles}</style></head>`
    + `<body><main>${controls}${mail}</main><div id="token-probe"></div></body></html>`;
}
const browser = await chromium.launch({ headless: true });
try {
  for (const theme of ['light', 'dark']) {
    for (const width of [390, 1280]) {
      const sideResults = {};
      for (const side of ['before', 'after']) {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        try {
          await page.route('**/*', (route) => route.abort());
          await page.setContent(fixture(side, theme));
          const result = { tokens: {}, cases: {} };
          for (const row of report.staticResolutions.filter((r) => r.theme === theme)) {
            const name = side === 'before' ? (row.source ?? row.token) : row.token;
            const value = await page.locator('#token-probe').evaluate((el, token) => {
              el.style.color = `var(${token})`;
              return getComputedStyle(el).color;
            }, name);
            assert.equal(value, rgb(row.oldValue), `${theme}/${width}/${side}/${name}`);
            result.tokens[row.token] = value;
          }
          for (const c of fixtureCases) {
            await page.mouse.move(width - 1, 899);
            if (c.hover) await page.locator(`#${c.id}`).hover();
            // Existing CSS transitions must settle before the computed target color is inspected.
            await page.locator(`#${c.id}`).evaluate(async (el) => {
              await Promise.all(el.getAnimations().map((animation) => animation.finished));
            });
            const value = await page.locator(`#${c.id}`).evaluate((el) => getComputedStyle(el).color);
            const expected = audit.aliases.find((r) => r.name === c.token)[theme];
            assert.equal(value, rgb(expected), `${theme}/${width}/${side}/${c.id}`);
            result.cases[c.id] = { color: value };
          }
          for (const c of mailCases) {
            const value = await page.locator(`#${c.id}`).evaluate((host) => {
              const wrap = host.firstElementChild;
              const svg = wrap.querySelector('svg');
              const style = getComputedStyle(svg);
              return { color: style.color, fill: style.fill, width: style.width, height: style.height,
                svgWidth: svg.getAttribute('width'), svgHeight: svg.getAttribute('height'),
                ariaHidden: svg.getAttribute('aria-hidden'), wrapWidth: getComputedStyle(wrap).width,
                wrapHeight: getComputedStyle(wrap).height, pathCount: svg.querySelectorAll('path').length,
                viewBox: svg.getAttribute('viewBox'), tag: svg.tagName };
            });
            const size = c.size ?? 16;
            assert.equal(value.color, rgb('#ffffff'));
            assert.equal(value.fill, rgb('#ffffff'));
            for (const property of ['width', 'height']) assert.equal(value[property], `${Math.round(size * 0.7)}px`);
            for (const property of ['svgWidth', 'svgHeight']) assert.equal(value[property], String(Math.round(size * 0.7)));
            assert.equal(value.wrapWidth, `${size}px`);
            assert.equal(value.wrapHeight, `${size}px`);
            assert.equal(value.ariaHidden, 'true');
            assert.ok(value.pathCount > 0);
            result.cases[c.id] = value;
          }
          sideResults[side] = result;
        } finally { await page.close(); }
      }
      assert.deepEqual(sideResults.after, sideResults.before, `${theme}/${width} before/after`);
      report.tokens.push({ theme, width, ...sideResults.after.tokens });
      report.cases.push({ theme, width, ...sideResults.after.cases });
    }
  }
  report.counts = { staticTokenPairs: report.staticResolutions.length, themeViewportPairs: report.cases.length,
    browserTokenPairs: report.staticResolutions.length * 2,
    browserControlPairs: report.cases.length * (fixtureCases.length + mailCases.length) };
  report.status = 'PASS';
  console.log(JSON.stringify(report, null, 2));
} finally { await browser.close(); }
