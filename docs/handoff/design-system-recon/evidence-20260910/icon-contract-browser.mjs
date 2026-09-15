import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { readFile, writeFile, mkdir, realpath } from 'node:fs/promises';
import { createServer } from 'node:http';
import { runInNewContext } from 'node:vm';
import { join } from 'node:path';
const output = await realpath('/tmp/frontend-icon-contract-20260911');
const fixture = join(output, 'fixture');
await mkdir(fixture, { recursive: true });
const repository = '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-icon-contract';
const baseline = '76c6dff98e3fa68f47c381d044e86fd0564d9509';
const require = createRequire(join(repository, 'frontend/package.json'));
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { chromium } = require('playwright');
const postcss = require('postcss');
const before = (file) => execFileSync('git', ['show', `${baseline}:frontend/src/${file}`], { cwd: repository, encoding: 'utf8' });
const after = (file) => readFile(join(repository, 'frontend/src', file), 'utf8');
const actual = {};
for (const side of ['before', 'after']) {
  const text = side === 'before' ? before('constants/icons.tsx') : await after('constants/icons.tsx');
  const compiled = ts.transpileModule(text, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022, esModuleInterop: true } });
  const module = { exports: {} };
  runInNewContext(compiled.outputText, { module, exports: module.exports,
    require: (name) => name === './platform-icon.css' ? {} : require(name) }, { timeout: 10000 });
  actual[side] = module.exports;
}
const sourceBefore = before('components/GoogleCalendarStatusBar.tsx');
const sourceAfter = await after('components/GoogleCalendarStatusBar.tsx');
assert.ok(sourceBefore.includes('style={{ marginRight: "var(--space-2)", flexShrink: 0 }}'));
assert.ok(sourceAfter.includes('className="google-calendar-status-icon-layout"'));
assert.ok(sourceAfter.includes('import "./GoogleCalendarStatusBar.css";'));
const layout = await after('components/GoogleCalendarStatusBar.css');
const declarations = [];
postcss.parse(layout).walkDecls((d) => declarations.push([d.prop, d.value]));
assert.deepEqual(declarations, [['margin-right', 'var(--space-2)'], ['flex-shrink', '0']]);
const commonCSS = ['tokens.css', 'index.css'].map((file) => before(file)).map((text) => {
  const ast = postcss.parse(text); ast.walkAtRules('import', (rule) => rule.remove()); return ast.toString();
}).join('\n');
assert.match(before('tokens.css'), /--space-2:\s*8px;/);
const statuses = { connected: { icon: 'Check', token: '--calendar-status-ok-text', light: '#1e7e34', dark: '#4ade80' },
  disconnected: { icon: 'X', token: '--calendar-status-error-text', light: '#c5221f', dark: '#f87171' } };
for (const value of Object.values(statuses)) {
  assert.ok(sourceBefore.includes(`color: "var(${value.token})"`));
  assert.ok(sourceAfter.includes(`color: "var(${value.token})"`));
}
const rgb = (hex) => `rgb(${[1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`;
const seed = '<!doctype html><html><body></body></html>';
await writeFile(join(fixture, 'index.html'), seed);
let documentRequests = 0;
const server = createServer((req, res) => {
  if (req.url === '/') { documentRequests += 1; res.setHeader('Content-Type', 'text/html'); res.end(seed); }
  else { res.statusCode = 204; res.end(); }
});
await new Promise((done) => server.listen(0, '127.0.0.1', done));
let browser;
const result = { baseline, method: 'Actual before/after Icon TSX compiled in memory with real Heroicons; server-rendered SVG inspected in Chromium. No client React entry or hydration.', comparisons: [], aria: [], diagnostics: {} };
try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [], consoleErrors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  for (const theme of ['light', 'dark']) for (const width of [390, 1280]) for (const [status, spec] of Object.entries(statuses)) {
    await page.setViewportSize({ width, height: 400 });
    const measured = {};
    for (const side of ['before', 'after']) {
      const props = { size: 14, weight: 'bold', 'aria-hidden': 'true',
        ...(side === 'before' ? { style: { marginRight: 'var(--space-2)', flexShrink: 0 } } : { className: 'google-calendar-status-icon-layout' }) };
      const svg = renderToStaticMarkup(React.createElement(actual[side][spec.icon], props));
      await page.setContent(`<!doctype html><html class="${theme === 'dark' ? 'force-dark' : ''}"><head><style>${commonCSS}\n${side === 'after' ? layout : ''}</style></head><body><div id="parent" style="display:flex;color:var(${spec.token})">${svg}<span>status</span></div></body></html>`);
      measured[side] = await page.locator('#parent svg').evaluate((el) => {
        const s = getComputedStyle(el);
        return { width: s.width, height: s.height, marginRight: s.marginRight, flexShrink: s.flexShrink,
          color: s.color, fill: s.fill, parentColor: getComputedStyle(el.parentElement).color,
          hidden: el.getAttribute('aria-hidden'), tag: el.tagName, paths: el.querySelectorAll('path').length };
      });
      const m = measured[side];
      assert.equal(m.width, '14px'); assert.equal(m.height, '14px'); assert.equal(m.marginRight, '8px');
      assert.equal(m.flexShrink, '0'); assert.equal(m.hidden, 'true');
      for (const key of ['color', 'fill', 'parentColor']) assert.equal(m[key], rgb(spec[theme]));
      assert.ok(m.paths > 0);
    }
    assert.deepEqual(measured.after, measured.before);
    result.comparisons.push({ theme, width, status, ...measured });
  }
  const attrs = { 'aria-hidden': false, 'aria-label': 'Done', 'aria-labelledby': 'caption', 'aria-describedby': 'description', role: 'img', focusable: 'false' };
  for (const side of ['before', 'after']) {
    await page.setContent(renderToStaticMarkup(React.createElement(actual[side].Check, attrs)));
    const value = await page.locator('svg').evaluate((el) => Object.fromEntries(['aria-hidden', 'aria-label', 'aria-labelledby', 'aria-describedby', 'role', 'focusable'].map((a) => [a, el.getAttribute(a)])));
    assert.deepEqual(value, side === 'before' ? { 'aria-hidden': 'true', 'aria-label': null, 'aria-labelledby': null, 'aria-describedby': null, role: null, focusable: null } : { ...attrs, 'aria-hidden': 'false' });
    result.aria.push({ side, value });
  }
  assert.equal(documentRequests, 1); assert.deepEqual(errors, []); assert.deepEqual(consoleErrors, []);
  result.diagnostics = { documentEntryRequests: documentRequests, clientModuleEntries: 0, pageerror: errors, consoleErrors };
  result.status = 'PASS';
  await page.close();
  await writeFile(join(output, 'browser-result.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser?.close();
  await new Promise((done) => server.close(done));
}
