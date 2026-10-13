const { createRequire } = require("module");
const WT = "/Users/tanizawashingo/worktrees/salesanchor/release-inventory-search-input";
const req = createRequire(WT + "/frontend/package.json");
const { chromium } = req("@playwright/test");
const fs = require("fs");
const LABEL = process.argv[2]; const BASE = process.argv[3];
const OUT = WT + "/docs/handoff/design-system-recon/evidence-20260910/";
const PROPS = ["padding","font-size","font-family","line-height","border","border-radius","background-color","border-top-color"];
const PAGES = [
  { key: "quote", path: "/quotes/new", prefix: "quote-add-search", rowName: "quote-item-row-1-name", pre: null },
  { key: "invoice", path: "/invoices/new", prefix: "invoice-add-search", rowName: "invoice-item-row-1-name", pre: "invoice-mode-inventory" },
];
const CANDS = ["ポケモンカード テスト箱A", "ポケモンカード テスト箱B", "ポケモンカード 在庫ゼロ箱"].map((name, i) => ({
  product_id: 900 + i, name, name_en: "Test " + i, product_code: "PM-0090" + i, expansion_code: null, card_number: null, jan_code: null,
  unit_price: 1000 * (i + 1), stock_quantity: i === 2 ? 0 : 10, supplier_default_id: null, supplier_name: null, image_url: null,
  matched_via: "name", score: 1 - i * 0.1, inventory_offers: [],
}));
const rectOf = r => r && ({ top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom });
(async () => {
  const browser = await chromium.launch({ executablePath: "/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const result = {};
  for (const pg of PAGES) for (const w of [1280, 1440]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 1000 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.addInitScript(() => {
      const u = { uid: "e2e-test-user-uid", email: "review@salesanchor.jp", displayName: "E2E", emailVerified: true };
      window.__salesanchorE2eAuthUser = u;
      try { localStorage.setItem("salesanchor:e2e-firebase-auth-user", JSON.stringify(u)); } catch {}
    });
    const calls = []; const searchUrls = [];
    await page.route("**/api/v1/**", route => {
      const u = new URL(route.request().url()); const k = route.request().method() + " " + u.pathname.replace("/api/v1", "");
      calls.push(k);
      const json = b => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(b) });
      if (k === "GET /inventory/search") { searchUrls.push(u.search); return json({ candidates: CANDS, masked: false }); }
      if (k === "GET /me/permissions") return json({ permissions: [], is_super_admin: true });
      if (k === "GET /staff/me") return json({ id: 1, primary_email: "review@salesanchor.jp", locale: "ja", theme: "light", ui_preferences: { show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true } });
      return json(k.startsWith("GET") ? [] : {});
    });
    await page.goto(BASE + pg.path, { waitUntil: "networkidle" });
    if (pg.pre) await page.click(`[data-testid="${pg.pre}"]`);
    const T = s => `[data-testid="${pg.prefix}-${s}"]`;
    await page.waitForSelector(T("input"), { timeout: 15000 });
    const m = {};
    const snap = async () => page.evaluate(([sel, andSel, orSel, PROPS]) => {
      const el = document.querySelector(sel); const a = document.querySelector(andSel); const o = document.querySelector(orSel);
      const cs = getComputedStyle(el); const st = {}; for (const p of PROPS) st[p] = cs.getPropertyValue(p);
      const R = e => { const r = e.getBoundingClientRect(); return { top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom }; };
      const ri = R(el), ra = R(a), ro = R(o);
      return { className: el.className, style: st, input: ri, and: ra, or: ro,
        centerDiffAnd: (ra.top + ra.height / 2) - (ri.top + ri.height / 2), centerDiffOr: (ro.top + ro.height / 2) - (ri.top + ri.height / 2) };
    }, [T("input"), T("op-and"), T("op-or"), PROPS]);
    m.initial = await snap();
    await page.fill(T("input"), "ポケモン カード");
    await page.waitForSelector(T("result-0"), { timeout: 10000 });
    await page.waitForTimeout(300);
    m.opened = await snap();
    m.dropdown = await page.evaluate(s => { const u = document.querySelector(s); const r = u.getBoundingClientRect(); return { left: r.left, top: r.top, width: r.width, height: r.height }; }, T("results"));
    m.dropdownTopMinusInputBottom = m.dropdown.top - m.opened.input.bottom;
    await page.screenshot({ path: OUT + `ay2n-${LABEL}-${pg.key}-${w}.png` });
    // 検索欄内クリックで閉じない
    await page.click(T("input"));
    await page.waitForTimeout(150);
    m.openAfterInsideClick = (await page.locator(T("results")).count()) > 0;
    // 外側クリックで閉じる
    await page.mouse.click(5, 5);
    await page.waitForTimeout(150);
    m.openAfterOutsideClick = (await page.locator(T("results")).count()) > 0;
    // 再度開いて AND
    await page.click(T("input"));
    await page.waitForSelector(T("result-0"), { timeout: 10000 });
    m.preAnd = { and: await page.getAttribute(T("op-and"), "aria-pressed"), or: await page.getAttribute(T("op-or"), "aria-pressed") };
    await page.click(T("op-and"));
    await page.waitForTimeout(500);
    m.afterAnd = { and: await page.getAttribute(T("op-and"), "aria-pressed"), or: await page.getAttribute(T("op-or"), "aria-pressed") };
    m.searchUrls = searchUrls;
    // 候補選択
    m.openAfterAndClick = (await page.locator(T("results")).count()) > 0;
    await page.click(T("input"));
    await page.waitForSelector(T("result-0"), { timeout: 10000 });
    await page.click(T("result-0"));
    await page.waitForTimeout(300);
    m.rowName = await page.evaluate(id => { const e = document.querySelector(`[data-testid="${id}"]`); return e ? { tag: e.tagName, value: e.value ?? null, text: e.textContent } : null; }, pg.rowName);
    m.unmockedCalls = [...new Set(calls)];
    result[pg.key + "-w" + w] = m;
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + `ay2n-measure-${LABEL}.json`, JSON.stringify(result, null, 1));
  console.log("written", OUT + `ay2n-measure-${LABEL}.json`);
})().catch(e => { console.error(e); process.exit(1); });
