const L = require("./ay2s-lib.cjs"); const fs = require("fs");
const PORT = process.env.PORT || "4182"; const BASE = "http://localhost:" + PORT;
const TAG = process.env.TAG || "before"; const OUT = "/tmp/CC報告ファイル/ssot-ay2s/impl/";
const SCREENS = [
  { key: "inventory-filter", path: "/inventory", ready: '[data-testid="inventory-filter-toggle"]',
    pre: async (page) => { await page.getByTestId("inventory-filter-toggle").click(); await page.waitForSelector('[data-testid="inventory-qty-min"]', { timeout: 10000 }); },
    items: ["inventory-qty-min", "inventory-qty-max", "inventory-price-min", "inventory-price-max"].map(t => ({ name: t, sel: `[data-testid="${t}"]`, sib: "div" })),
    interact: async (page, res) => {
      const mark = res.calls.length;
      for (const [t, v] of [["inventory-qty-min","3"],["inventory-qty-max","50"],["inventory-price-min","100"],["inventory-price-max","9000"]]) { await page.getByTestId(t).fill(v); await page.waitForTimeout(700); }
      await page.waitForTimeout(1200);
      res.interactCalls = res.calls.slice(mark).filter(c => c.startsWith("GET /inventory"));
    } },
  { key: "knowledge-aliases", path: "/super-admin/analysis-rules?section=knowledge-aliases", ready: '[data-testid="rules-search"]',
    items: ["rules-search", "aliases-search"].map(t => ({ name: t, sel: `[data-testid="${t}"]`, sib: "div" })),
    interact: async (page, res) => {
      const mark = res.calls.length;
      await page.getByTestId("rules-search").fill("abc"); await page.getByTestId("rules-search").press("Enter"); await page.waitForTimeout(1000);
      await page.getByTestId("aliases-search").fill("xyz"); await page.getByTestId("aliases-search").press("Enter"); await page.waitForTimeout(1000);
      res.interactCalls = res.calls.slice(mark);
    } },
];
(async () => {
  const browser = await L.chromium.launch({ executablePath: L.EXE }); const result = {};
  for (const sc of SCREENS) for (const w of [1280, 1440, 375]) {
    const key = sc.key + "-w" + w; const res = { path: sc.path, stoppedAt: null, consoleErrors: [], calls: [], items: {} }; result[key] = res;
    const ctx = await browser.newContext({ viewport: { width: w, height: 1000 }, deviceScaleFactor: 2 });
    const page = await L.setup(ctx, res, sc.extra);
    const err = await L.goto(page, BASE + sc.path, sc.ready, res);
    if (err) { res.stoppedAt = err; await ctx.close(); continue; }
    try { if (sc.pre) await sc.pre(page); } catch (e) { res.preError = String(e).slice(0, 300); }
    for (const it of sc.items) {
      const n = await page.locator(it.sel).count();
      const m = n ? await page.evaluate(L.measureFn, [it.sel, L.PROPS, it.sib]) : { found: false };
      res.items[it.name] = { count: n, ...m, doc: await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth })) };
    }
    await page.screenshot({ path: OUT + `${TAG}/${key}-full.png` });
    for (const it of sc.items) { const loc = page.locator(it.sel).first(); if (await loc.count()) { const box = await loc.boundingBox(); if (box) await page.screenshot({ path: OUT + `${TAG}/${key}-${it.name}.png`, clip: { x: Math.max(0, box.x - 16), y: Math.max(0, box.y - 16), width: Math.min(box.width + 32, w), height: box.height + 32 } }).catch(()=>{}); } }
    try { await sc.interact(page, res); } catch (e) { res.interactError = String(e).slice(0, 300); }
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + TAG + ".json", JSON.stringify(result, null, 1)); console.log("written");
})().catch(e => { console.error(e); process.exit(1); });
