const { createRequire } = require("module");
const WT = process.env.AY2Q_WT || "/tmp/ay2p-wt";
const req = createRequire(WT + "/frontend/package.json");
const { chromium } = req("@playwright/test");
const fs = require("fs");
const LABEL = process.argv[2]; const BASE = process.argv[3];
const OUT = "/tmp/CC報告ファイル/ssot-ay2q/" + LABEL + "/";
fs.mkdirSync(OUT, { recursive: true });
const PROPS = ["height","padding","font-size","font-weight","color","background-color","border","border-radius","box-shadow","cursor","outline","opacity"];
const PAGES = [
  { key: "quote", path: "/quotes/new", prefix: "quote-add-search", pre: null },
  { key: "invoice", path: "/invoices/new", prefix: "invoice-add-search", pre: "invoice-mode-inventory" },
];
const CANDS = ["ポケモンカード テスト箱A", "ポケモンカード テスト箱B", "ポケモンカード 在庫ゼロ箱"].map((name, i) => ({
  product_id: 900 + i, name, name_en: "Test " + i, product_code: "PM-0090" + i, expansion_code: null, card_number: null, jan_code: null,
  unit_price: 1000 * (i + 1), stock_quantity: i === 2 ? 0 : 10, supplier_default_id: null, supplier_name: null, image_url: null,
  matched_via: "name", score: 1 - i * 0.1, inventory_offers: [],
}));
(async () => {
  const browser = await chromium.launch({ executablePath: "/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const result = {};
  for (const pg of PAGES) for (const w of [1280, 1440, 375]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.addInitScript(() => {
      const u = { uid: "e2e-test-user-uid", email: "review@salesanchor.jp", displayName: "E2E", emailVerified: true };
      window.__salesanchorE2eAuthUser = u;
      try { localStorage.setItem("salesanchor:e2e-firebase-auth-user", JSON.stringify(u)); } catch {}
    });
    const searchUrls = [];
    await page.route("**/api/v1/**", route => {
      const u = new URL(route.request().url()); const k = route.request().method() + " " + u.pathname.replace("/api/v1", "");
      const json = b => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(b) });
      if (k === "GET /inventory/search") { searchUrls.push(u.pathname + u.search); return json({ candidates: CANDS, masked: false }); }
      if (k === "GET /me/permissions") return json({ permissions: [], is_super_admin: true });
      if (k === "GET /staff/me") return json({ id: 1, primary_email: "review@salesanchor.jp", locale: "ja", theme: "light", ui_preferences: { show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true } });
      return json(k.startsWith("GET") ? [] : {});
    });
    await page.goto(BASE + pg.path, { waitUntil: "networkidle" });
    if (pg.pre) await page.click(`[data-testid="${pg.prefix.replace("add-search","mode-inventory")}"]`).catch(()=>{});
    if (pg.pre) { await page.click(`[data-testid="${pg.pre}"]`).catch(()=>{}); }
    const T = s => `[data-testid="${pg.prefix}-${s}"]`;
    page.on("pageerror", e => console.log("PAGEERR", e.message.slice(0,200)));
    try { await page.waitForSelector(T("input"), { timeout: 15000 }); } catch (e) { console.log("URL", page.url()); await page.screenshot({ path: OUT + "fail.png" }); throw e; }
    const m = {};
    const snap = async () => page.evaluate(([inS, aS, oS, gS, PROPS]) => {
      const R = e => { const r = e.getBoundingClientRect(); return { top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom, right: r.right }; };
      const info = e => { const cs = getComputedStyle(e); const st = {}; for (const p of PROPS) st[p] = cs.getPropertyValue(p);
        return { class: e.className, ariaPressed: e.getAttribute("aria-pressed"), disabled: e.disabled, rect: R(e), computed: st, text: e.textContent }; };
      const inp = document.querySelector(inS), a = document.querySelector(aS), o = document.querySelector(oS), g = document.querySelector(gS);
      const ri = R(inp), ra = R(a), ro = R(o);
      return { input: ri, row: R(g.parentElement), groupInRow: R(g).right <= R(g.parentElement).right + 0.01, group: { rect: R(g), computed: (() => { const cs = getComputedStyle(g); return { border: cs.border, borderRadius: cs.borderRadius, opacity: cs.opacity, display: cs.display, gap: cs.gap }; })() },
        and: info(a), or: info(o),
        centerDiffAnd: (ra.top + ra.height/2) - (ri.top + ri.height/2), centerDiffOr: (ro.top + ro.height/2) - (ri.top + ri.height/2),
        gapInputToGroup: R(g).left - ri.right, gapAndOr: ro.left - ra.right,
        docScrollW: document.documentElement.scrollWidth, docClientW: document.documentElement.clientWidth };
    }, [T("input"), T("op-and"), T("op-or"), T("op-toggle"), PROPS]);
    const clip = async (name) => { const g = await page.locator(T("root")).first().boundingBox(); await page.screenshot({ path: OUT + `${LABEL}-${pg.key}-${w}-${name}.png`, clip: { x: Math.max(0,g.x-8), y: Math.max(0,g.y-8), width: Math.min(g.width+16, w), height: Math.max(90, Math.min(260, Math.round((await page.locator(T("op-toggle")).boundingBox()).y + (await page.locator(T("op-toggle")).boundingBox()).height - g.y + 24))) } }); };
    m.initialSingleToken = await snap(); // 空欄: disabled
    await clip("0-empty-disabled");
    await page.fill(T("input"), "ポケモン カード");
    await page.waitForSelector(T("result-0"), { timeout: 10000 });
    await page.waitForTimeout(300);
    m.enabledInitial = await snap();
    await clip("1-initial-or");
    // hover on AND (unselected)
    await page.hover(T("op-and")); await page.waitForTimeout(150);
    m.hoverAnd = (await snap()).and; await clip("2-hover-and");
    // click AND (mousedown outside? results close handled by component)
    searchUrls.length = 0;
    await page.click(T("op-and")); await page.waitForTimeout(700);
    m.afterAnd = await snap(); m.afterAndSearchUrls = [...searchUrls];
    await page.mouse.move(5, 5); await page.waitForTimeout(150);
    await clip("3-and-selected");
    searchUrls.length = 0;
    await page.click(T("op-or")); await page.waitForTimeout(700);
    m.afterOr = await snap(); m.afterOrSearchUrls = [...searchUrls];
    // OR を押した後に検索語を変更
    searchUrls.length = 0;
    await page.fill(T("input"), "ポケモン カード 箱"); await page.waitForTimeout(700);
    m.typedAfterOrUrls = [...searchUrls];
    // AND を選び検索語変更
    await page.click(T("op-and")); await page.waitForTimeout(300);
    searchUrls.length = 0;
    await page.fill(T("input"), "ポケモン カード 箱A"); await page.waitForTimeout(700);
    m.typedAfterAndUrls = [...searchUrls];
    await page.click(T("op-or")); await page.waitForTimeout(300);
    await page.mouse.move(5, 5);
    // keyboard focus: focus input then Tab
    await page.focus(T("input")); await page.keyboard.press("Tab"); await page.waitForTimeout(150);
    m.focusAfterTab = await page.evaluate(() => { const e = document.activeElement; const cs = getComputedStyle(e); return { testid: e.getAttribute("data-testid"), tag: e.tagName, outline: cs.outline, outlineOffset: cs.outlineOffset, boxShadow: cs.boxShadow, matchesFocusVisible: e.matches(":focus-visible"), bg: cs.backgroundColor }; });
    await clip("4-focus-visible");
    await page.keyboard.press("Tab"); await page.waitForTimeout(150);
    m.focusAfterTab2 = await page.evaluate(() => { const e = document.activeElement; const cs = getComputedStyle(e); return { testid: e.getAttribute("data-testid"), outline: cs.outline, matchesFocusVisible: e.matches(":focus-visible") }; });
    m.searchUrlsAll = searchUrls;
    result[pg.key + "-w" + w] = m;
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + `ay2q-measure-${LABEL}.json`, JSON.stringify(result, null, 1));
  console.log("written", OUT + `ay2q-measure-${LABEL}.json`);
})().catch(e => { console.error(e); process.exit(1); });
