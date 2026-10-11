// AY-2d: 登録画面3種の実画面採取。使い方: node ay2d-capture.cjs <before|after> <port> <outDir>
// API(/api/v1/public/register)は page.route でモック（before/after 同一応答）。
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const { chromium } = require(path.join(ROOT, "frontend/node_modules/playwright"));
const [label, port, outDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const MOCK = { valid: true, company_name: "Sample Trading Co.", lead_id: 1, token_type: "register" };
const PAGES = [
  { key: "register", url: "/register?token=mock", proceed: true },
  { key: "address", url: "/register/address?token=mock" },
  { key: "change-billing", url: "/register/change-billing?token=mock" },
];
const PROPS = ["padding-top","padding-right","padding-bottom","padding-left","border-top-width","border-top-style","border-top-color","border-top-left-radius","font-size","font-family","font-weight","line-height","color","background-color","height","width","margin-left","margin-top","flex-grow","outline-style","box-shadow","box-sizing"];
(async () => {
  const b = await chromium.launch({ executablePath: process.env.HOME + "/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const res = { label, mock: MOCK, pages: [] };
  for (const w of [1280, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 2, colorScheme: "light" });
    for (const p of PAGES) {
      const page = await ctx.newPage();
      await page.route(/\/api\/v1\/public\/register/, (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK) }));
      await page.goto(`http://127.0.0.1:${port}${p.url}`, { waitUntil: "networkidle" });
      await page.waitForSelector("form");
      if (p.proceed) { await page.locator('input[type=radio][value=proceed]').check(); await page.waitForTimeout(200); }
      await page.waitForTimeout(300);
      const data = await page.evaluate((props) => {
        const ins = [...document.querySelectorAll("input")].filter((e) => !["radio","checkbox","hidden"].includes(e.type));
        const rect = (e) => { const r = e.getBoundingClientRect(); return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height }; };
        const items = ins.map((e) => { const c = getComputedStyle(e), o = {}; for (const k of props) o[k] = c.getPropertyValue(k); return { type: e.type, id: e.id, cls: e.className, style: e.getAttribute("style"), rect: rect(e), cs: o }; });
        const ov = (a, b) => a.x < b.x + b.w - 0.5 && b.x < a.x + a.w - 0.5 && a.y < b.y + b.h - 0.5 && b.y < a.y + a.h - 0.5;
        const overlapsInputs = []; for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) if (ov(items[i].rect, items[j].rect)) overlapsInputs.push([i, j]);
        // ラベル文字との重なり: 入力を含む/参照する label のテキスト範囲 vs 入力矩形
        const overlapsLabelText = [];
        ins.forEach((e, i) => { const lab = e.closest("label") || (e.id && document.querySelector(`label[for="${e.id}"]`)); if (!lab) return; const walker = document.createTreeWalker(lab, NodeFilter.SHOW_TEXT); let n; while ((n = walker.nextNode())) { if (!n.textContent.trim()) continue; const rg = document.createRange(); rg.selectNodeContents(n); for (const r of rg.getClientRects()) { const a = { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height }; if (ov(a, items[i].rect)) overlapsLabelText.push([i, n.textContent.trim().slice(0, 30)]); } } });
        const outOfViewport = items.map((it, i) => (it.rect.x < -0.5 || it.rect.x + it.rect.w > document.documentElement.clientWidth + 0.5) ? i : -1).filter((i) => i >= 0);
        // tel 行: 国番号 select と電話入力の top 差
        const tels = ins.filter((e) => e.type === "tel").map((e) => { const sel = e.parentElement.querySelector("input[id$=-dial]"); if (!sel) return { note: "no-dial-input" }; const a = sel.getBoundingClientRect(), t = e.getBoundingClientRect(); return { selTop: a.top + scrollY, telTop: t.top + scrollY, selH: a.height, telH: t.height, sameRow: Math.abs((a.top + a.height / 2) - (t.top + t.height / 2)) < Math.max(a.height, t.height) / 2 }; });
        return { scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth, count: items.length, items, overlapsInputs, overlapsLabelText, outOfViewport, tels };
      }, PROPS);
      const shot = path.join(outDir, `${label}-${p.key}-${w}.png`);
      await page.screenshot({ path: shot, fullPage: true });
      res.pages.push({ page: p.key, w, shot, ...data });
      await page.close();
    }
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(path.join(outDir, `${label}.json`), JSON.stringify(res, null, 1));
  for (const r of res.pages) console.log(label, r.page, r.w, "inputs", r.count, "scrollW/clientW", r.scrollWidth + "/" + r.clientWidth, "overlapIn", r.overlapsInputs.length, "overlapLabel", r.overlapsLabelText.length, "out", r.outOfViewport.length, "tel", JSON.stringify(r.tels.map((t) => t.sameRow)));
})();
