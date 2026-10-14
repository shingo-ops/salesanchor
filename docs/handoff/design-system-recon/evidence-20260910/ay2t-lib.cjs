const { createRequire } = require("module");
const WT = "/Users/tanizawashingo/worktrees/salesanchor/release-ay2t-goal-inputs-mold";
const req = createRequire(WT + "/frontend/package.json");
exports.chromium = req("@playwright/test").chromium;
exports.EXE = "/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell";
const PERMS = ["customers.view","customers.create","customers.update","customers.delete","leads.view","leads.create","leads.update","products.view","products.create","products.update","products.delete","inventory.view","orders.view","orders.create","orders.update","orders.delete","quotes.view","invoices.view"];
exports.PROPS = ["height","padding","border","border-radius","font-size","min-width","width","color","background-color","min-height","box-sizing","display"];
const d = new Date(); 
exports.setup = async function (ctx, res, extra) {
  const page = await ctx.newPage();
  page.on("console", m => { if (m.type() === "error") res.consoleErrors.push(m.text().slice(0, 300)); });
  page.on("pageerror", e => res.consoleErrors.push("pageerror: " + String(e).slice(0, 300)));
  await page.addInitScript(() => {
    const u = { uid: "e2e-test-user-uid", email: "review@salesanchor.jp", displayName: "E2E", emailVerified: true };
    window.__salesanchorE2eAuthUser = u;
    try { localStorage.setItem("salesanchor:e2e-firebase-auth-user", JSON.stringify(u)); } catch {}
  });
  await page.route("**/api/v1/**", route => {
    const u = new URL(route.request().url()); const k = route.request().method() + " " + u.pathname.replace("/api/v1", "");
    res.calls.push(k + u.search);
    const json = b => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(b) });
    if (extra) { const r = extra(k, u, json, route); if (r !== undefined) return r; }
    if (k === "GET /me/permissions") return json({ user_id: 6, is_tenant_admin: true, permissions: PERMS, is_super_admin: true });
    if (k === "GET /staff/me") return json({ id: 6, primary_email: "review@salesanchor.jp", locale: "ja", theme: "light", ui_preferences: { show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true } });
    if (k === "GET /teams") return json([{ id: 1, name: "営業本部", leader_id: 6 }]);
    if (k === "GET /inventory") return json({ items: [], total: 0, suppliers: [], categories: [], conditions: [], units: [] });
    return json(k.startsWith("GET") ? [] : {});
  });
  return page;
};
exports.goto = async function (page, url, sel, res) {
  let lastErr = null;
  for (let a = 0; a < 6; a++) {
    try { await page.goto(url, { waitUntil: "networkidle", timeout: 30000 }); await page.waitForSelector(sel, { timeout: 15000 }); return null; } catch (e) { lastErr = e; res.consoleErrors.push("retry" + a); }
  }
  return String(lastErr).slice(0, 400);
};
// 要素の計測。el は selector 文字列
exports.measureFn = ([SEL, PROPS, SIBSEL]) => {
  const R = e => { const r = e.getBoundingClientRect(); return { left: +r.left.toFixed(2), top: +r.top.toFixed(2), width: +r.width.toFixed(2), height: +r.height.toFixed(2) }; };
  const el = document.querySelector(SEL);
  if (!el) return { found: false };
  const cs = getComputedStyle(el); const s = {}; for (const p of PROPS) s[p] = cs.getPropertyValue(p);
  const r = el.getBoundingClientRect(); const c = r.top + r.height / 2;
  const scope = el.closest(SIBSEL) || el.parentElement;
  const sibs = [...scope.querySelectorAll("input,select,button,a,textarea")].filter(n => n !== el && n.getBoundingClientRect().width > 0 && n.closest("form,.gs-row,.dist-field,.content-toolbar,section,div") ).slice(0, 8).map(n => {
    const nr = n.getBoundingClientRect();
    return { tag: n.tagName.toLowerCase(), type: n.getAttribute("type"), testid: n.getAttribute("data-testid"), text: (n.textContent || "").trim().slice(0, 20), height: +nr.height.toFixed(2), centerDiff: +((nr.top + nr.height / 2) - c).toFixed(2) };
  });
  return { found: true, tag: el.tagName.toLowerCase(), type: el.getAttribute("type"), className: String(el.className), testid: el.getAttribute("data-testid"), id: el.id || null, rect: R(el), computed: s, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, siblings: sibs,
    parent: el.parentElement.tagName.toLowerCase() + "." + String(el.parentElement.className) };
};
// 一致する CSS 規則（selector / 宣言のうち対象プロパティ）
exports.matchRulesFn = ([SEL]) => {
  const el = document.querySelector(SEL); const out = [];
  const want = ["padding","border","border-radius","font-size","min-width","width","color","background","background-color","min-height"];
  const walk = (rules, sheetHref, ctxs) => { for (const r of rules) {
    if (r.cssRules && !r.selectorText) { walk(r.cssRules, sheetHref, ctxs.concat(r.conditionText || r.constructor.name)); continue; }
    if (!r.selectorText) continue;
    let m = false; try { m = el.matches(r.selectorText); } catch {}
    if (!m) continue;
    const decl = {}; for (const p of want) { const v = r.style.getPropertyValue(p); if (v) decl[p] = v; }
    for (let i = 0; i < r.style.length; i++) { const n = r.style.item(i); if (want.some(w => n === w || n.startsWith(w + "-"))) decl[n] = r.style.getPropertyValue(n); }
    if (Object.keys(decl).length) out.push({ selector: r.selectorText.replace(/\s+/g, " "), media: ctxs.join(" | "), decl });
  } };
  for (const sh of document.styleSheets) { try { walk(sh.cssRules, sh.href || "inline", []); } catch {} }
  return out;
};
