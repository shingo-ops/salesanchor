const { createRequire } = require("module");
const WT = "/Users/tanizawashingo/worktrees/salesanchor/release-list-search-inputs";
const { chromium } = createRequire(WT + "/frontend/package.json")("@playwright/test");
const fs = require("fs");
const LABEL = process.argv[2], BASE = process.argv[3];
const OUT = "/tmp/CC報告ファイル/ssot-ay2p/w375/"; fs.mkdirSync(OUT, { recursive: true });
const PERMS = ["customers.view","customers.create","customers.update","customers.delete","leads.view","leads.create","leads.update","products.view","products.create","products.update","products.delete","inventory.view","orders.view","orders.create","orders.update","orders.delete","quotes.view","invoices.view"];
const SEARCH_SEL = ".content-toolbar__left input[type=text], .content-toolbar__left input[type=search]";
const SCREENS = [{ key: "contacts", path: "/crm/contacts" }, { key: "inventory", path: "/inventory" }];
const CP = ["min-width","max-width","flex-shrink","flex-grow","flex-basis","width","box-sizing","display","overflow-x","overflow-y","padding-left","padding-right","border-left-width","border-right-width"];
(async () => {
  const browser = await chromium.launch({ executablePath: "/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const result = {};
  for (const sc of SCREENS) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 1000 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.addInitScript(() => { const u = { uid: "e2e-test-user-uid", email: "review@salesanchor.jp", displayName: "E2E", emailVerified: true }; window.__salesanchorE2eAuthUser = u; try { localStorage.setItem("salesanchor:e2e-firebase-auth-user", JSON.stringify(u)); } catch {} });
    await page.route("**/api/v1/**", route => {
      const u = new URL(route.request().url()); const k = route.request().method() + " " + u.pathname.replace("/api/v1", "");
      const json = b => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(b) });
      if (k === "GET /me/permissions") return json({ permissions: PERMS, is_super_admin: false });
      if (k === "GET /staff/me") return json({ id: 1, primary_email: "review@salesanchor.jp", locale: "ja", theme: "light", ui_preferences: { show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true } });
      if (k === "GET /inventory") return json({ items: [], total: 0, suppliers: [], categories: [], conditions: [], units: [] });
      return json(k.startsWith("GET") ? [] : {});
    });
    let lastErr = null;
    for (let a = 0; a < 8; a++) { try { await page.goto(BASE + sc.path, { waitUntil: "networkidle", timeout: 30000 }); await page.waitForSelector(SEARCH_SEL, { timeout: 20000 }); lastErr = null; break; } catch (e) { lastErr = e; await new Promise(r => setTimeout(r, 3000)); } }
    if (lastErr) { result[sc.key] = { error: String(lastErr).slice(0, 200) }; await ctx.close(); continue; }
    const r = {};
    r.measure = await page.evaluate(([SEL, CP]) => {
      const cs = (e) => { const c = getComputedStyle(e); const o = {}; for (const p of CP) o[p] = c.getPropertyValue(p); return o; };
      const R = e => { const b = e.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top, width: b.width, height: b.height }; };
      const el = document.querySelector(SEL); const left = el.closest(".content-toolbar__left"); const tb = el.closest(".content-toolbar");
      const sw = e => ({ scrollWidth: e.scrollWidth, clientWidth: e.clientWidth, offsetWidth: e.offsetWidth, scrollLeft: e.scrollLeft });
      const path = []; for (let n = tb; n && n !== document.documentElement; n = n.parentElement) path.push({ tag: n.tagName.toLowerCase(), cls: String(n.className).slice(0, 50), ...sw(n), overflowX: getComputedStyle(n).overflowX, w: n.getBoundingClientRect().width });
      const btns = [...tb.querySelectorAll("button")].map(b => ({ testid: b.getAttribute("data-testid"), text: (b.textContent || "").trim().slice(0, 12), rect: R(b), insideViewport: b.getBoundingClientRect().right <= 375, visibleWidth: Math.max(0, Math.min(b.getBoundingClientRect().right, 375) - Math.max(b.getBoundingClientRect().left, 0)) }));
      return { input: { cls: String(el.className), cs: cs(el), rect: R(el) }, left: { cs: cs(left), rect: R(left), ...sw(left) }, toolbar: { cs: cs(tb), rect: R(tb), ...sw(tb) }, ancestors: path, buttons: btns, viewportW: innerWidth, docScrollW: document.documentElement.scrollWidth };
    }, [SEARCH_SEL, CP]);
    // 横スクロールの可否: toolbar と left を scrollLeft で動かしてみる
    r.scrollTest = await page.evaluate((SEL) => {
      const el = document.querySelector(SEL); const left = el.closest(".content-toolbar__left"); const tb = el.closest(".content-toolbar");
      const out = {};
      for (const [n, e] of [["left", left], ["toolbar", tb]]) { e.scrollLeft = 9999; out[n] = { scrollLeftAfter: e.scrollLeft, canScroll: e.scrollWidth > e.clientWidth, overflowX: getComputedStyle(e).overflowX }; e.scrollLeft = 0; }
      return out;
    }, SEARCH_SEL);
    await page.screenshot({ path: OUT + `${LABEL}-${sc.key}-w375-full.png`, fullPage: false });
    // CDP matched rules
    const cdp = await ctx.newCDPSession(page);
    await cdp.send("DOM.enable"); await cdp.send("CSS.enable");
    const doc = await cdp.send("DOM.getDocument", { depth: 0 });
    const q = await cdp.send("DOM.querySelector", { nodeId: doc.root.nodeId, selector: SEARCH_SEL });
    const m = await cdp.send("CSS.getMatchedStylesForNode", { nodeId: q.nodeId });
    r.matched = (m.matchedCSSRules || []).map(x => ({ selector: x.rule.selectorList.text, origin: x.rule.origin, src: (x.rule.style.cssText || "").slice(0, 400), styleSheetId: x.rule.styleSheetId, range: x.rule.style.range }))
      .filter(x => /width|flex|display|min|box-sizing/.test(x.src));
    // 規則を一つずつ外す実験: 各 matched rule の関連宣言を inline で無効化ではなく、classを外して幅を見る
    r.experiments = await page.evaluate((SEL) => {
      const el = document.querySelector(SEL); const w = () => el.getBoundingClientRect().width; const out = { base: w() };
      const orig = el.className;
      for (const c of orig.split(/\s+/)) { el.className = orig.split(/\s+/).filter(x => x !== c).join(" "); out["without." + c] = w(); }
      el.className = orig;
      el.style.minWidth = "0"; out["inline min-width:0"] = w(); el.style.minWidth = "";
      el.style.flexShrink = "0"; out["inline flex-shrink:0"] = w(); el.style.flexShrink = "";
      el.style.width = "280px"; out["inline width:280px"] = w(); el.style.width = "";
      return out;
    }, SEARCH_SEL);
    result[sc.key] = r;
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + `w375-${LABEL}.json`, JSON.stringify(result, null, 1));
  console.log("written", LABEL);
})().catch(e => { console.error(e); process.exit(1); });
