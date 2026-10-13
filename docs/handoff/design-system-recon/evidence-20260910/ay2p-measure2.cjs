// 使い方: node ay2p-measure2.cjs <LABEL> <WORKTREE> [BASE=http://localhost:4181]
// 出力: /tmp/CC報告ファイル/ssot-ay2p/<LABEL>/ に JSON と PNG
const { createRequire } = require("module");
const LABEL = process.argv[2]; const WT = process.argv[3]; const BASE = process.argv[4] || "http://localhost:4181";
if (!LABEL || !WT) { console.error("usage: node ay2p-measure2.cjs <LABEL> <WORKTREE> [BASE]"); process.exit(2); }
const req = createRequire(WT + "/frontend/package.json");
const { chromium } = req("@playwright/test");
const fs = require("fs");
const OUT = "/tmp/CC報告ファイル/ssot-ay2p/" + LABEL + "/";
fs.mkdirSync(OUT, { recursive: true });
const PROPS = ["padding","border","border-radius","font-size","font-family","line-height","background-color","min-height","box-sizing","height","width","color","margin","display"];
const PERMS = ["customers.view","customers.create","customers.update","customers.delete","leads.view","leads.create","leads.update","products.view","products.create","products.update","products.delete","inventory.view","orders.view","orders.create","orders.update","orders.delete","quotes.view","invoices.view"];
const WORD = "テスト検索ワード";
const SEARCH_SEL = ".content-toolbar__left input[type=text], .content-toolbar__left input[type=search]";
const SCREENS = [
  { key: "companies", path: "/crm/companies", list: "/companies", param: "search" },
  { key: "contacts", path: "/crm/contacts", list: "/contacts", param: "search" },
  { key: "inventory", path: "/inventory", list: "/inventory", param: "q" },
  { key: "orders", path: "/orders", list: "/orders", param: "search" },
  { key: "products", path: "/admin/products", list: "/products", param: "search" },
];

(async () => {
  const browser = await chromium.launch({ executablePath: "/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const result = {};
  for (const sc of SCREENS) for (const w of [1280, 1440, 375]) {
    const key = sc.key + "-w" + w; const res = { path: sc.path, stoppedAt: null, consoleErrors: [], calls: [] };
    result[key] = res;
    const ctx = await browser.newContext({ viewport: { width: w, height: 1000 }, deviceScaleFactor: 2 });
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
      if (k === "GET /me/permissions") return json({ permissions: PERMS, is_super_admin: false });
      if (k === "GET /staff/me") return json({ id: 1, primary_email: "review@salesanchor.jp", locale: "ja", theme: "light", ui_preferences: { show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true } });
      if (k === "GET /inventory") return json({ items: [], total: 0, suppliers: [], categories: [], conditions: [], units: [] });
      if (k === "GET /orders/group-counts") return json({ total: 0, counts: {} });
      if (k === "GET /products/tcg-types" || k === "GET /tcg-types") return json([{ code: "T1", name_ja: "テスト種別A" }, { code: "T2", name_ja: "テスト種別B" }]);
      return json(k.startsWith("GET") ? [] : {});
    });
    try {
      let lastErr = null;
      for (let attempt = 0; attempt < 8; attempt++) {
        try { await page.goto(BASE + sc.path, { waitUntil: "networkidle", timeout: 30000 }); await page.waitForSelector(SEARCH_SEL, { timeout: 20000 }); lastErr = null; break; } catch (e) { lastErr = e; res.consoleErrors.push("retry" + attempt); await new Promise(r => setTimeout(r, 3000)); }
      }
      if (lastErr) throw lastErr;
    } catch (e) {
      res.stoppedAt = "goto/ready: " + String(e).slice(0, 400);
      res.url = page.url(); res.bodyText = (await page.evaluate(() => document.body.innerText).catch(() => "")).slice(0, 500);
      await page.screenshot({ path: OUT + `${key}-STOPPED.png` }).catch(() => {});
      await ctx.close(); continue;
    }
    const measure = () => page.evaluate(([SEL, PROPS]) => {
      const R = e => { const r = e.getBoundingClientRect(); return { left: r.left, top: r.top, width: r.width, height: r.height }; };
      const S = e => { const cs = getComputedStyle(e); const o = {}; for (const p of PROPS) o[p] = cs.getPropertyValue(p); return o; };
      const el = document.querySelector(SEL);
      const tb = el.closest(".content-toolbar");
      const r = el.getBoundingClientRect(); const c = r.top + r.height / 2;
      const sibs = [...tb.querySelectorAll("input,select,button,a")].filter(n => n !== el && n.getBoundingClientRect().width > 0).map(n => {
        const nr = n.getBoundingClientRect();
        return { tag: n.tagName.toLowerCase(), type: n.getAttribute("type"), testid: n.getAttribute("data-testid"), className: String(n.className), text: (n.textContent || "").trim().slice(0, 30), rect: R(n), centerDiffToSearch: (nr.top + nr.height / 2) - c };
      });
      const parent = el.parentElement;
      return { search: { tag: "input", type: el.type, className: el.className, testid: el.getAttribute("data-testid"), placeholder: el.placeholder, rect: R(el), style: S(el), parentTag: parent.tagName.toLowerCase(), parentClass: String(parent.className) },
        toolbarRect: R(tb), siblings: sibs };
    }, [SEARCH_SEL, PROPS]);
    res.initial = await measure();
    const clip = async (name) => {
      const b = await page.locator(SEARCH_SEL).first().evaluate(e => { const r = e.closest(".content-toolbar").getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; });
      await page.screenshot({ path: OUT + key + "-toolbar-" + name + ".png", clip: { x: Math.max(0, b.x - 8), y: Math.max(0, b.y - 8), width: b.width + 16, height: b.height + 16 } });
    };
    await page.screenshot({ path: OUT + `${key}.png`, fullPage: true });
    await clip("initial");
    const input = page.locator(SEARCH_SEL).first();
    await input.focus();
    res.focused = await input.evaluate(e => { const cs = getComputedStyle(e); return { borderColor: cs.borderColor, boxShadow: cs.boxShadow, outline: cs.outline }; });
    await clip("focus");
    // fill: API URL の変化
    const before = res.calls.filter(c => c.startsWith("GET " + sc.list + "?") || c === "GET " + sc.list);
    res.listUrlBeforeFill = before.length ? before[before.length - 1] : null;
    const waiter = page.waitForResponse(r => { const u = new URL(r.url()); return u.pathname === "/api/v1" + sc.list && u.searchParams.has(sc.param); }, { timeout: 10000 }).then(r => { const u = new URL(r.url()); return u.pathname.replace("/api/v1", "") + u.search; }).catch(e => "NOT-OBSERVED: " + String(e).slice(0, 100));
    await input.fill(WORD);
    res.listUrlAfterFill = await waiter;
    res.afterFill = await input.evaluate(e => ({ value: e.value, scrollWidth: e.scrollWidth, clientWidth: e.clientWidth, rectWidth: e.getBoundingClientRect().width, height: e.getBoundingClientRect().height }));
    res.doc = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));

    res.extra = await page.evaluate(([SEL]) => {
      const el = document.querySelector(SEL); const tb = el.closest(".content-toolbar");
      const tbr = tb.getBoundingClientRect();
      // 一覧(表)先頭要素: table / [role=table] / .data-table 等の最初
      // 一覧先頭: ツールバー(またはその親)の次の兄弟要素
      let anc = tb; let tbl = anc.nextElementSibling; while (!tbl && anc.parentElement) { anc = anc.parentElement; tbl = anc.nextElementSibling; }
      const tr = tbl ? tbl.getBoundingClientRect() : null;
      const sel = document.querySelector(".content-toolbar select, .comp-select__control");
      const out = { searchHeight: el.getBoundingClientRect().height, toolbarHeight: tbr.height, toolbarTop: tbr.top, toolbarBottom: tbr.bottom,
        listFirst: tbl ? { tag: tbl.tagName.toLowerCase(), className: String(tbl.className).slice(0, 60), top: tr.top, left: tr.left } : null,
        docScrollWidth: document.documentElement.scrollWidth, docClientWidth: document.documentElement.clientWidth };
      const cs = [...document.querySelectorAll("select.comp-select__control")].map(n => ({ className: String(n.className), width: n.getBoundingClientRect().width }));
      out.selects = cs;
      return out;
    }, [SEARCH_SEL]);
    // 合成検証: 金型クラス + field-* の競合（検索欄の隣に一時挿入して測り、すぐ消す）
    res.synthetic = await page.evaluate(() => {
      const host = document.querySelector(".content-toolbar__left"); const out = {};
      const variants = { "A comp-field__input field-h-md field-w-md": "comp-field__input field-h-md field-w-md", "B comp-field__input field-h-md field-w-sm": "comp-field__input field-h-md field-w-sm", "C comp-field__input (class only)": "comp-field__input", "D comp-field__input field-w-sm": "comp-field__input field-w-sm" };
      for (const [name, cls] of Object.entries(variants)) {
        const i = document.createElement("input"); i.type = "text"; i.className = cls; host.appendChild(i);
        const cs = getComputedStyle(i), r = i.getBoundingClientRect();
        out[name] = { width: r.width, height: r.height, minHeight: cs.minHeight, padding: cs.padding, fontSize: cs.fontSize, borderRadius: cs.borderRadius, borderTop: cs.borderTopWidth + " " + cs.borderTopColor };
        i.remove();
      }
      return out;
    });
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + `measure-${LABEL}.json`, JSON.stringify(result, null, 1));
  console.log("written", OUT + `measure-${LABEL}.json`);
})().catch(e => { console.error(e); process.exit(1); });
