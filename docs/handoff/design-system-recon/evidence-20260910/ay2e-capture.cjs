// AY-2e: 規則なし一行入力6件（5画面）の実画面採取。使い方: node ay2e-capture.cjs <before|after> <port> <outDir>
// API は page.route でモック（応答 JSON は ay2e-mocks.json、before/after 同一）。偽ログインは DEV build のみ有効。
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const { chromium } = require(path.join(ROOT, "frontend/node_modules/playwright"));
const [label, port, outDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const MOCKS = JSON.parse(fs.readFileSync(path.join(__dirname, "ay2e-mocks.json"), "utf8"));
const NON_TEXT = ["radio", "checkbox", "hidden", "button", "submit"];
const PROPS = ["padding-top","padding-right","padding-bottom","padding-left","border-top-width","border-top-style","border-top-color","border-top-left-radius","font-size","font-family","font-weight","line-height","color","background-color","height","width","margin-left","margin-top","flex-grow","outline-style","box-sizing","display","vertical-align"];

const SCREENS = [
  { key: "discord-announce", url: "/admin/discord-announce", ready: 'input[placeholder]', n: 1 },
  { key: "manual-record", url: "/lead-chat", ready: "#manual-occurred-at", n: 1,
    prep: async (page) => { await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click(); } },
  { key: "channel-masters", url: "/admin/channel-masters", ready: 'input[placeholder*="whatsapp"]', n: 2 },
  { key: "commission", url: "/management-center/commission", ready: '[data-testid^="settings-value-"]', n: 5 },
  { key: "own-inventory", url: "/own-inventory", ready: ".actions-cell button", n: 1,
    prep: async (page) => { await page.locator(".actions-cell button").first().click(); await page.waitForSelector('input[aria-label]:not([type=hidden])[type=number]', { timeout: 8000 }); } },
];

(async () => {
  const b = await chromium.launch({ executablePath: process.env.HOME + "/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell" });
  const res = { label, screens: [] };
  for (const w of [1280, 375]) {
    for (const s of SCREENS) {
      const ctx = await b.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 2, colorScheme: "light" });
      const page = await ctx.newPage();
      const logs = [], seen = [];
      page.on("pageerror", (e) => logs.push("pageerror: " + String(e).slice(0, 200)));
      await page.addInitScript(() => { window.__salesanchorE2eAuthUser = { uid: "e2e-test-user-uid", email: "review@salesanchor.jp", displayName: "E2E", emailVerified: true }; try { localStorage.setItem("salesanchor:e2e-firebase-auth-user", JSON.stringify(window.__salesanchorE2eAuthUser)); } catch {} });
      await page.route("**/api/v1/**", async (route) => {
        const u = new URL(route.request().url()); const key = route.request().method() + " " + u.pathname.replace(/^\/api\/v1/, "");
        seen.push(key);
        const body = key in MOCKS ? MOCKS[key] : (route.request().method() === "GET" ? [] : {});
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
      });
      const rec = { screen: s.key, w, url: s.url, ok: false };
      try {
        await page.goto(`http://127.0.0.1:${port}${s.url}`, { waitUntil: "networkidle" });
        if (s.prep) await page.waitForTimeout(300), await s.prep(page);
        await page.waitForSelector(s.ready, { timeout: 10000 });
        await page.waitForTimeout(500);
        rec.ok = true;
      } catch (e) { rec.error = String(e).slice(0, 300); }
      rec.logs = logs.slice(0, 5); rec.requests = [...new Set(seen)];
      rec.shot = path.join(outDir, `${label}-${s.key}-${w}.png`);
      await page.screenshot({ path: rec.shot, fullPage: true });
      if (rec.ok) {
        const data = await page.evaluate(({ props, nonText }) => {
          const rect = (r) => ({ x: +(r.x + scrollX).toFixed(2), y: +(r.y + scrollY).toFixed(2), w: +r.width.toFixed(2), h: +r.height.toFixed(2) });
          const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
          // 対象: 画面内の text/number/datetime-local 入力（検索ボックス等を除くため body 内 main 領域のみでなくページ全体を採取し、後で絞る）
          const ins = [...document.querySelectorAll("input")].filter((e) => !nonText.includes(e.type) && vis(e));
          const textRects = (el) => { const out = []; const wk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n; while ((n = wk.nextNode())) { if (!n.textContent.trim()) continue; const rg = document.createRange(); rg.selectNodeContents(n); const r = rg.getBoundingClientRect(); if (r.width > 0) out.push({ t: n.textContent.trim().slice(0, 24), ...rect(r) }); } return out; };
          const items = ins.map((e) => {
            const c = getComputedStyle(e), o = {}; for (const k of props) o[k] = c.getPropertyValue(k);
            const p = e.parentElement;
            const sib = [...p.children].filter((x) => x !== e && vis(x)).map((x) => ({ tag: x.tagName.toLowerCase(), cls: x.className && x.className.toString ? x.className.toString().slice(0, 40) : "", text: (x.textContent || "").trim().slice(0, 24), ...rect(x.getBoundingClientRect()) }));
            const tr = e.closest("tr");
            const row = tr ? [...tr.children].map((x) => ({ tag: x.tagName.toLowerCase(), ...rect(x.getBoundingClientRect()) })) : null;
            return { type: e.type, id: e.id, ph: e.placeholder, aria: e.getAttribute("aria-label"), testid: e.getAttribute("data-testid"), cls: e.className, style: e.getAttribute("style"), rect: rect(e.getBoundingClientRect()), cs: o,
              parentTag: p.tagName.toLowerCase(), parentCls: p.className && p.className.toString ? p.className.toString() : "", parentRect: rect(p.getBoundingClientRect()), siblings: sib, parentText: textRects(p).filter((t) => true), row };
          });
          const table = document.querySelector("table"); const ths = table ? [...table.querySelectorAll("thead th")].map((x) => ({ t: x.textContent.trim().slice(0, 16), ...rect(x.getBoundingClientRect()) })) : null;
          // ページ全体: 操作要素＋入力の重なり・はみ出し
          const els = [...document.querySelectorAll("input,button,select,textarea")].filter((e) => !["radio", "checkbox", "hidden"].includes(e.type) && vis(e));
          const rs = els.map((e) => ({ e, r: e.getBoundingClientRect() }));
          const ov = (a, b) => a.x < b.x + b.width - 0.5 && b.x < a.x + a.width - 0.5 && a.y < b.y + b.height - 0.5 && b.y < a.y + a.height - 0.5;
          const overlaps = [];
          for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) { if (rs[i].e.contains(rs[j].e) || rs[j].e.contains(rs[i].e)) continue; if (ov(rs[i].r, rs[j].r)) overlaps.push([rs[i].e.tagName + ":" + (rs[i].e.getAttribute("aria-label") || rs[i].e.placeholder || rs[i].e.textContent.trim().slice(0, 12)), rs[j].e.tagName + ":" + (rs[j].e.getAttribute("aria-label") || rs[j].e.placeholder || rs[j].e.textContent.trim().slice(0, 12))]); }
          // 入力と他要素の文字の重なり（同じ親内）
          const textOverlaps = [];
          ins.forEach((e) => { const er = e.getBoundingClientRect(); const scope = e.closest("tr") || e.closest("label") || e.parentElement; const wk = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT); let n; while ((n = wk.nextNode())) { if (!n.textContent.trim() || e.contains(n)) continue; if (n.parentElement && n.parentElement.closest("select,option,button")) continue; const rg = document.createRange(); rg.selectNodeContents(n); const r = rg.getBoundingClientRect(); if (r.width > 0 && ov(er, r)) textOverlaps.push((e.getAttribute("aria-label") || e.placeholder || e.id) + " x " + n.textContent.trim().slice(0, 20)); } });
          const outRight = els.filter((e) => e.getBoundingClientRect().right > document.documentElement.clientWidth + 0.5).map((e) => e.tagName + ":" + (e.getAttribute("aria-label") || e.placeholder || ""));
          return { scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth, count: items.length, items, ths, tableRect: table ? rect(table.getBoundingClientRect()) : null, overlaps, textOverlaps, outRight };
        }, { props: PROPS, nonText: NON_TEXT });
        Object.assign(rec, data);
      }
      res.screens.push(rec);
      await ctx.close();
    }
  }
  await b.close();
  fs.writeFileSync(path.join(outDir, `${label}.json`), JSON.stringify(res, null, 1));
  for (const r of res.screens) console.log(label, r.screen, r.w, r.ok ? "ok" : "FAIL " + r.error, "inputs", r.count, "scrollW/clientW", r.scrollWidth + "/" + r.clientWidth, "overlaps", (r.overlaps || []).length, "textOverlaps", (r.textOverlaps || []).length, "outRight", (r.outRight || []).length, "logs", (r.logs || []).length);
})();
