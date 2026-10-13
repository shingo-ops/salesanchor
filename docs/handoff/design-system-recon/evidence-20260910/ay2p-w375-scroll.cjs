const { createRequire } = require("module");
const WT = "/Users/tanizawashingo/worktrees/salesanchor/release-list-search-inputs";
const { chromium } = createRequire(WT + "/frontend/package.json")("@playwright/test");
const BASE = process.argv[3], LABEL = process.argv[2];
(async () => {
  const browser = await chromium.launch({ executablePath: "/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const ctx = await browser.newContext({ viewport: { width: 375, height: 1000 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.addInitScript(() => { const u = { uid: "e2e-test-user-uid", email: "review@salesanchor.jp", displayName: "E2E", emailVerified: true }; window.__salesanchorE2eAuthUser = u; try { localStorage.setItem("salesanchor:e2e-firebase-auth-user", JSON.stringify(u)); } catch {} });
  await page.route("**/api/v1/**", route => { const u = new URL(route.request().url()); const k = route.request().method() + " " + u.pathname.replace("/api/v1", ""); const json = b => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(b) });
    if (k === "GET /me/permissions") return json({ permissions: ["inventory.view","products.view"], is_super_admin: false });
    if (k === "GET /staff/me") return json({ id: 1, primary_email: "r@s.jp", locale: "ja", theme: "light", ui_preferences: { show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true } });
    if (k === "GET /inventory") return json({ items: [], total: 0, suppliers: [], categories: [], conditions: [], units: [] });
    return json(k.startsWith("GET") ? [] : {}); });
  for (let a = 0; a < 8; a++) { try { await page.goto(BASE + "/inventory", { waitUntil: "networkidle", timeout: 30000 }); await page.waitForSelector('[data-testid=inventory-filter-toggle]', { timeout: 20000 }); break; } catch (e) { await new Promise(r => setTimeout(r, 3000)); } }
  const r = await page.evaluate(() => {
    const btn = document.querySelector('[data-testid=inventory-filter-toggle]');
    const scrollers = []; for (let n = btn.parentElement; n; n = n.parentElement) { const c = getComputedStyle(n); if (n.scrollWidth > n.clientWidth && /auto|scroll/.test(c.overflowX)) scrollers.push(n); }
    const s = scrollers[0]; const out = { scroller: s && (s.tagName + "." + String(s.className).slice(0, 40)), scrollW: s && s.scrollWidth, clientW: s && s.clientWidth };
    if (s) { s.scrollLeft = 9999; out.scrollLeftAfter = s.scrollLeft; const b = btn.getBoundingClientRect(); out.btnAfterScroll = { left: b.left, right: b.right, fullyVisible: b.left >= 0 && b.right <= 375 }; s.scrollLeft = 0; }
    return out; });
  console.log(LABEL, JSON.stringify(r));
  await browser.close();
})();
