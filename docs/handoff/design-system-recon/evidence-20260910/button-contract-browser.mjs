import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { writeFile, realpath } from 'node:fs/promises';
const output = await realpath('/tmp/frontend-button-contract-20260911');
const fixtureRoot = join(output, 'fixture');
const frontend = '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-calendar-source/frontend';
const require = createRequire(join(frontend, 'package.json'));
const { createServer } = await import(require.resolve('vite'));
const react = (await import(require.resolve('@vitejs/plugin-react'))).default;
const { chromium } = require('playwright');
const server = await createServer({ configFile: false, root: fixtureRoot, cacheDir: join(output, 'vite-cache'),
  plugins: [react()], resolve: { alias: { react: join(frontend, 'node_modules/react'), 'react-dom': join(frontend, 'node_modules/react-dom') } },
  server: { host: '127.0.0.1', port: 0, fs: { allow: [frontend, output] } },
});
const variants = ['primary', 'secondary', 'ghost', 'danger', 'outline', 'tab'];
const expected = {
  light: { inherit: 'rgb(26, 32, 44)', normalHead: 'rgb(30, 58, 138)', normalTrack: 'rgb(226, 232, 240)' },
  dark: { inherit: 'rgb(241, 245, 249)', normalHead: 'rgb(91, 141, 217)', normalTrack: 'rgb(51, 65, 85)' },
};
const results = { operations: [], spinners: [], reducedMotion: [], diagnostics: [] };
server.watcher.on('all', (event, path) => results.diagnostics.push({ source: 'watcher', event, path }));
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('console', (message) => results.diagnostics.push({ source: 'console', type: message.type(), text: message.text(), location: message.location() }));
  page.on('websocket', (socket) => socket.on('framereceived', (frame) => results.diagnostics.push({ source: 'websocket', payload: String(frame.payload) })));
  page.on('request', (request) => { if (request.url().includes('entry.tsx')) results.diagnostics.push({ source: 'entry-request', url: request.url() }); });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0]);
  await page.locator('#primary').waitFor();
  await page.evaluate(() => { const p = window.buttonProbe; p.original = Object.fromEntries(Object.entries(p.refs).map(([v, r]) => [v, r.current])); });
  for (const variant of variants) {
    const button = page.locator(`#${variant}`);
    await button.click();
    const clickCount = await page.evaluate((v) => window.buttonProbe.counts[v], variant);
    assert.equal(clickCount, 1, `${variant} click`);
    await button.press('Enter');
    const enterCount = await page.evaluate((v) => window.buttonProbe.counts[v], variant);
    assert.equal(enterCount, 2, `${variant} Enter`);
    await button.press('Space');
    const spaceCount = await page.evaluate((v) => window.buttonProbe.counts[v], variant);
    assert.equal(spaceCount, 3, `${variant} Space`);
    results.operations.push({ variant, mode: 'normal', clickCount, enterCount, spaceCount });
  }
  for (const mode of ['disabled', 'loading']) {
    await page.evaluate((m) => window.buttonProbe.setMode(m), mode);
    await page.waitForFunction(() => document.querySelector('#primary').disabled);
    if (mode === 'loading') await page.locator('#primary .sa-spinner--inherit').waitFor();
    for (const variant of variants) {
      const button = page.locator(`#${variant}`);
      const box = await button.boundingBox();
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await button.evaluate((el) => el.focus());
      await page.keyboard.press('Enter');
      await page.keyboard.press('Space');
      const status = await page.evaluate((v) => {
        const p = window.buttonProbe;
        return { count: p.counts[v], sameRef: p.refs[v].current === p.original[v], disabled: p.refs[v].current.disabled };
      }, variant);
      assert.equal(status.count, 3);
      assert.equal(status.sameRef, true);
      assert.equal(status.disabled, true);
      results.operations.push({ variant, mode, additionalCount: status.count - 3, sameRef: status.sameRef });
    }
  }
  for (const theme of ['light', 'dark']) {
    await page.evaluate((t) => document.documentElement.classList.toggle('force-dark', t === 'dark'), theme);
    for (const id of ['inherited', 'normal', 'on-accent']) {
      const value = await page.locator(`#${id} .sa-spinner`).evaluate((el) => {
        const s = getComputedStyle(el);
        return { top: s.borderTopColor, right: s.borderRightColor, bottom: s.borderBottomColor, left: s.borderLeftColor, animation: s.animationName };
      });
      const head = id === 'inherited' ? 'rgba(0, 0, 0, 0)' : id === 'normal' ? expected[theme].normalHead : 'rgb(255, 255, 255)';
      const track = id === 'inherited' ? expected[theme].inherit : id === 'normal' ? expected[theme].normalTrack : 'rgba(255, 255, 255, 0.4)';
      assert.equal(value.top, head, `${theme}/${id}/top`);
      for (const edge of ['right', 'bottom', 'left']) assert.equal(value[edge], track, `${theme}/${id}/${edge}`);
      assert.equal(value.animation, 'sa-spin');
      results.spinners.push({ theme, id, ...value });
    }
    for (const variant of variants) {
      const value = await page.locator(`#${variant} .sa-spinner`).evaluate((el) => {
        const s = getComputedStyle(el);
        return { parent: getComputedStyle(el.parentElement).color, top: s.borderTopColor, right: s.borderRightColor,
          bottom: s.borderBottomColor, left: s.borderLeftColor, hidden: el.getAttribute('aria-hidden'), role: el.getAttribute('role') };
      });
      assert.notEqual(value.parent, '');
      assert.equal(value.top, 'rgba(0, 0, 0, 0)');
      for (const edge of ['right', 'bottom', 'left']) assert.equal(value[edge], value.parent);
      assert.equal(value.hidden, 'true'); assert.equal(value.role, null);
      results.spinners.push({ theme, variant, ...value });
    }
  }
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const id of [...variants, 'inherited', 'normal', 'on-accent']) {
    const motion = await page.locator(`#${id} .sa-spinner`).evaluate((el) => ({ name: getComputedStyle(el).animationName, animations: el.getAnimations().length }));
    assert.equal(motion.name, 'none'); assert.equal(motion.animations, 0);
    results.reducedMotion.push({ id, ...motion });
  }
  assert.deepEqual(errors, []);
  await page.screenshot({ path: join(output, 'dark-loading-reduced-motion.png'), fullPage: true });
  assert.deepEqual(results.diagnostics.filter((d) => d.source === 'console' && d.type === 'error'), []);
  await page.close();
  results.status = 'PASS';
  await writeFile(join(output, 'browser-result.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
} finally {
  await browser?.close();
  await server.close();
}
