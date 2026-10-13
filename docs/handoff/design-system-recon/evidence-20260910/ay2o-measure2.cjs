// 使い方: node ay2o-measure.cjs <LABEL> <WORKTREE> [BASE=http://localhost:4179]
//   LABEL: before / after など。出力は /tmp/CC報告ファイル/ssot-ay2o/<LABEL>/ に JSON と PNG。
//   WORKTREE: playwright を解決する worktree（frontend/node_modules がある所）。preview はあらかじめ起動しておく。
const { createRequire } = require("module");
const LABEL = process.argv[2]; const WT = process.argv[3]; const BASE = process.argv[4] || "http://localhost:4179";
if (!LABEL || !WT) { console.error("usage: node ay2o-measure.cjs <LABEL> <WORKTREE> [BASE]"); process.exit(2); }
const req = createRequire(WT + "/frontend/package.json");
const { chromium } = req("@playwright/test");
const fs = require("fs");
const OUT = "/tmp/CC報告ファイル/ssot-ay2o/" + LABEL + "/";
fs.mkdirSync(OUT, { recursive: true });
const PROPS = ["padding","font-size","font-family","line-height","border","border-radius","background-color","height","width","margin-left","box-sizing","min-height","color","display","align-items"];
const PERMS = ["invoices.view","invoices.create","invoices.update","invoices.void","orders.view","orders.update","quotes.view"];
const INVOICE = {
  id: 3, invoice_number: "INV-0003", quote_id: null, company_id: 1, currency: "USD", subtotal: 100, shipping_fee: 10, tax_amount: 0,
  total_amount: 110, exchange_rate_jpy: 150, exchange_rate_usd: 1, amount_jpy: 16500, amount_usd: 110, payment_method: "PayPal",
  status: "issued", branch_number: null, erp_key: "ERP-1", issued_at: "2026-10-01T00:00:00Z", due_date: "2026-10-31", paid_at: null,
  voided_at: null, void_reason: null, notes: null, created_at: "2026-10-01T00:00:00Z",
  items: [{ id: 1, product_name: "テスト商品", name_en: "Test item", condition: "NM", unit: "box", quantity: 2, unit_price: 50, weight: 0.5, subtotal: 100 }],
  ship_to_snapshot: null, bill_to_snapshot: null, duty_amount: null, fx_rate_snapshot: null,
  paypal_order_id: null, paypal_approval_url: "https://www.sandbox.paypal.com/checkoutnow?token=DUMMY-TOKEN-0000000000000000", payment_fee: null,
  paypal_invoicer_view_url: null, paypal_copy_pdf_at: null,
};
const MONTHLY = { year: 2026, month: 10, total: 12345, by_staff: [{ staff_id: 1, staff_name: "担当A", total: 10000 }, { staff_id: null, staff_name: null, total: 2345 }], by_role: [{ role: "sales", total: 12345 }] };
const SETTINGS = { id: 1, tenant_id: 1, created_at: "2026-10-01T00:00:00Z", updated_at: "2026-10-01T00:00:00Z",
  commission_rates: { sales: { type: "rate", value: 0.1 }, order: { type: "rate", value: 0.1 }, ship: { type: "fixed", value: 200 }, purchase: { type: "fixed", value: 100 }, trouble: { type: "fixed", value: 500 } } };
const ORDERS = { items: [{ order_id: 1, order_number: "ORD-0001", company_name: "テスト社", contact_display_name: "山田" }] };

const SCREENS = [
  { key: "invoice-detail", path: "/invoices/3", ready: "input[readonly]",
    targets: { "A1-paypal-url(:241)": "input[readonly]" },
    refs: { "ref-金型date-toolbar(InvoiceDetailPage:210)": 'input[type="date"]' },
    after: async (page) => { await page.getByRole("button", { name: "無効化", exact: true }).click(); await page.waitForSelector('input[placeholder="無効化の理由を入力..."]'); },
    targets2: { "A2-void-reason(:290)": 'input[placeholder="無効化の理由を入力..."]' } },
  { key: "commissions", path: "/commissions", ready: '[data-testid="commissions-year"]',
    targets: { "B1-year(CommissionsPage:141)": '[data-testid="commissions-year"]', "B2-month(CommissionsPage:153)": '[data-testid="commissions-month"]' } },
  { key: "commission-settings", path: "/commission-settings", ready: '[data-testid="monthly-year"]',
    targets: { "B3-year(CommissionSettingsPage:277)": '[data-testid="monthly-year"]', "B4-month(CommissionSettingsPage:289)": '[data-testid="monthly-month"]' },
    refs: { "ref-金型number(settings-value-sales:221)": '[data-testid="settings-value-sales"]', "ref-SelectControl(settings-type-sales:208)": '[data-testid="settings-type-sales"]' } },
];

(async () => {
  const browser = await chromium.launch({ executablePath: "/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const result = {};
  for (const sc of SCREENS) for (const w of [1280, 1440]) {
    const key = sc.key + "-w" + w; const res = { path: sc.path, stoppedAt: null, targets: {}, consoleErrors: [], requestFailures: [], calls: [] };
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
      if (k === "GET /invoices/3") return json(INVOICE);
      if (k === "GET /invoices/3/paypal-disputes") return json([]);
      if (k === "GET /commissions/monthly") return json(MONTHLY);
      if (k === "GET /financials/orders") return json(ORDERS);
      if (k === "GET /tenant-commission-settings") return json(SETTINGS);
      return json(k.startsWith("GET") ? [] : {});
    });
    try {
      await page.goto(BASE + sc.path, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForSelector(sc.ready, { timeout: 15000 });
    } catch (e) {
      res.stoppedAt = "goto/ready(" + sc.ready + "): " + String(e).slice(0, 400);
      res.url = page.url(); res.bodyText = (await page.evaluate(() => document.body.innerText).catch(() => "")).slice(0, 500);
      await page.screenshot({ path: OUT + `${key}-STOPPED.png` }).catch(() => {});
      await ctx.close(); continue;
    }
    const SIX = { "A1": 'input[readonly]', "A2": 'input[placeholder="無効化の理由を入力..."]', "B-year": 'input[data-testid$="year"]', "B-month": 'input[data-testid$="month"]' };
    res.extra = {};
    const info = async (sel) => page.evaluate((sel) => { const el = document.querySelector(sel); if (!el) return { found: false }; const r = el.getBoundingClientRect(); const p = el.closest("label") || el.parentElement; const pr = p.getBoundingClientRect(); return { found: true, className: el.className, left: r.left, top: r.top, width: r.width, height: r.height, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, value: el.value, valueLength: [...el.value].length, centerDiffToParent: (r.top + r.height / 2) - (pr.top + pr.height / 2) }; }, sel);
    if (sc.key !== "invoice-detail") {
      const ys = sc.key === "commissions" ? "commissions-year" : "monthly-year"; const ms = sc.key === "commissions" ? "commissions-month" : "monthly-month";
      await page.fill('[data-testid="' + ys + '"]', "2026"); await page.fill('[data-testid="' + ms + '"]', "12");
      await page.waitForTimeout(500);
      res.extra.apiCallsAfterFill = res.calls.filter(c => c.includes("/commissions/monthly") || c.includes("/monthly"));
      res.extra.year = await info('[data-testid="' + ys + '"]'); res.extra.month = await info('[data-testid="' + ms + '"]');
      const clip = async (name, sel) => { const b = await page.locator(sel).boundingBox(); await page.screenshot({ path: OUT + key + "-month-" + name + ".png", clip: { x: Math.max(0, b.x - 8), y: Math.max(0, b.y - 8), width: b.width + 16, height: b.height + 16 } }); };
      await page.locator('[data-testid="' + ms + '"]').focus(); await clip("focus", '[data-testid="' + ms + '"]');
      await page.locator('[data-testid="' + ms + '"]').blur();
      await page.locator('[data-testid="' + ms + '"]').hover(); await clip("hover", '[data-testid="' + ms + '"]');
      await page.mouse.move(0, 0);
    }
    const measure = async (map) => page.evaluate(([map, PROPS]) => {
      const R = e => { const r = e.getBoundingClientRect(); return { top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom, right: r.right }; };
      const S = e => { const cs = getComputedStyle(e); const o = {}; for (const p of PROPS) o[p] = cs.getPropertyValue(p); return o; };
      const desc = e => ({ tag: e.tagName.toLowerCase(), type: e.getAttribute("type"), testid: e.getAttribute("data-testid"), className: e.className && e.className.toString ? e.className.toString() : "", text: (e.textContent || "").trim().slice(0, 40), rect: R(e), style: S(e) });
      const out = {};
      for (const [name, sel] of Object.entries(map)) {
        const el = document.querySelector(sel);
        if (!el) { out[name] = { found: false }; continue; }
        const r = R(el); const parent = el.parentElement; const grand = parent && parent.parentElement;
        const row = (grand && getComputedStyle(parent).display.includes("flex") ? parent : (grand || parent));
        const neighbors = [...document.querySelectorAll("input,select,button,a,label,textarea")].filter(n => n !== el && !n.contains(el) && !el.contains(n)).filter(n => { const nr = n.getBoundingClientRect(); return nr.width > 0 && nr.top < r.bottom && nr.bottom > r.top; }).map(n => { const d = desc(n); d.centerDiffToTarget = (d.rect.top + d.rect.height / 2) - (r.top + r.height / 2); return d; });
        out[name] = { found: true, self: Object.assign(desc(el), { value: el.value, readOnly: el.readOnly, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, fits: el.scrollWidth <= el.clientWidth, placeholder: el.getAttribute("placeholder"), ariaLabel: el.getAttribute("aria-label") }),
          parent: Object.assign(desc(parent), { parentDisplay: getComputedStyle(parent).display, flexGap: getComputedStyle(parent).gap, alignItems: getComputedStyle(parent).alignItems }),
          grandparent: grand ? Object.assign(desc(grand), { display: getComputedStyle(grand).display, gap: getComputedStyle(grand).gap, alignItems: getComputedStyle(grand).alignItems }) : null,
          verticalOverlapNeighbors: neighbors };
      }
      return out;
    }, [map, PROPS]);
    Object.assign(res.targets, await measure(sc.targets));
    if (sc.refs) res.refs = await measure(sc.refs);
    if (sc.after) {
      try { await sc.after(page); Object.assign(res.targets, await measure(sc.targets2));
        const reason = "テスト用の無効化理由です。三十文字ちょうどになるように調整す";
        await page.fill(SIX.A2, reason); res.extra.A2 = await info(SIX.A2); res.extra.A2.expectedLength = [...reason].length;
        await page.screenshot({ path: OUT + key + "-A2-filled.png" });
        res.extra.A1 = await info(SIX.A1);
        res.extra.A1ButtonLink = await page.evaluate(() => { const a = document.querySelector("input[readonly]"); const sib = [...a.parentElement.children].filter(c => c !== a)[0]; const r = sib.getBoundingClientRect(); const ar = a.getBoundingClientRect(); return { tag: sib.tagName, className: String(sib.className), left: r.left, top: r.top, width: r.width, height: r.height, centerDiffToA1: (ar.top + ar.height / 2) - (r.top + r.height / 2) }; });
        await page.getByRole("button", { name: "キャンセル", exact: true }).click(); await page.waitForTimeout(300);
        res.extra.A2AfterCancelExists = (await page.locator(SIX.A2).count()) > 0;
      }
      catch (e) { res.stoppedAt = "after-step: " + String(e).slice(0, 400); }
    }
    res.doc = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
    await page.screenshot({ path: OUT + `${key}.png`, fullPage: true });
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + `measure-${LABEL}.json`, JSON.stringify(result, null, 1));
  console.log("written", OUT + `measure-${LABEL}.json`);
})().catch(e => { console.error(e); process.exit(1); });
