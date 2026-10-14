const L = require("./lib.cjs"); const fs = require("fs");
const BASE = "http://localhost:4182"; const OUT = "/tmp/CC報告ファイル/ssot-ay2r/impl/";
const LABEL = process.argv[2]; // before | after
fs.mkdirSync(OUT + LABEL, { recursive: true });
const SCREENS = [
  { key: "conditions", path: "/management-center/conditions", sel: '[data-testid="conditions-search"]', form: true },
  { key: "product-categories", path: "/management-center/product-categories", sel: '[data-testid="product-categories-search"]', form: true },
  { key: "status-master", path: "/management-center/status-master", sel: '[data-testid="status-master-search"]', form: true },
  { key: "suppliers", path: "/management-center/suppliers", sel: '[data-testid="suppliers-search"]', form: true },
  { key: "units", path: "/management-center/units", sel: '[data-testid="units-search"]', form: true },
  { key: "contacts", path: "/crm/contacts", sel: '.content-toolbar input[type="text"]', form: false },
  { key: "companies", path: "/crm/companies", sel: '.content-toolbar input[type="text"]', form: false },
];
(async () => {
  const browser = await L.chromium.launch({ executablePath: L.EXE }); const result = {};
  for (const sc of SCREENS) for (const w of [1280, 1440, 375]) {
    const key = sc.key + "-w" + w; const res = { path: sc.path, stoppedAt: null, consoleErrors: [], calls: [] }; result[key] = res;
    const ctx = await browser.newContext({ viewport: { width: w, height: 1000 }, deviceScaleFactor: 2 });
    const page = await L.setup(ctx, res);
    const err = await L.goto(page, BASE + sc.path, sc.sel, res);
    if (err) { res.stoppedAt = err; res.url = page.url(); await page.screenshot({ path: OUT + LABEL + `/${key}-STOPPED.png` }).catch(()=>{}); await ctx.close(); continue; }
    const arg = [sc.sel, L.PROPS, sc.form ? "form" : ".content-toolbar"];
    res.formClass = await page.locator(sc.sel).first().evaluate(e => (e.closest("form") || e.closest(".content-toolbar")).className);
    res.measure = await page.evaluate(L.measureFn, arg);
    res.doc = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
    const b = await page.locator(sc.sel).first().evaluate(e => { const r = (e.closest("form") || e.closest(".content-toolbar")).getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; });
    await page.screenshot({ path: OUT + LABEL + "/" + key + "-form.png", clip: { x: Math.max(0, b.x - 8), y: Math.max(0, b.y - 8), width: Math.min(b.width + 16, w), height: b.height + 16 } });
    await page.screenshot({ path: OUT + LABEL + "/" + key + "-full.png" });
    // 検索動作
    const n0 = res.calls.length;
    await page.locator(sc.sel).first().fill("テスト検索");
    if (sc.form) await page.locator(sc.sel).first().press("Enter"); 
    await page.waitForTimeout(1500);
    res.searchCalls = res.calls.slice(n0).filter(c => /search=/.test(c));
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + LABEL + ".json", JSON.stringify(result, null, 1)); console.log("written");
})().catch(e => { console.error(e); process.exit(1); });
