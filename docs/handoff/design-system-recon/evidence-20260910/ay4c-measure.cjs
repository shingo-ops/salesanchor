// AY-4c-1 実測スクリプト。使い方: node ay4c-measure.cjs <beforeCss> <afterCss> <outJson> <shotDir>
// 前: origin/main の vite build CSS（アプリ全体 1 枚）＋ 実ファイルから写した変更前マークアップ。
// 後: 作業ツリーの vite build CSS ＋ 本物の Checkbox / CheckboxControl が描く DOM（renderToStaticMarkup）。
// 親は型ごとに実ファイルの親要素の class・インライン style を写してある（ay4c-render.tsx の ref を参照）。
const path = require("path"), fs = require("fs"), cp = require("child_process"), os = require("os");
const FRONT = path.resolve(__dirname, "../../../../frontend");
const { chromium } = require(path.join(FRONT, "node_modules/playwright"));
const esbuild = require(path.join(FRONT, "node_modules/esbuild"));
const [, , BCSS, ACSS, OUT, SHOTS] = process.argv;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ay4c-"));
const outfile = path.join(tmp, "render.cjs");
esbuild.buildSync({ entryPoints: [path.join(__dirname, "ay4c-render.tsx")], bundle: true, platform: "node", format: "cjs", outfile, jsx: "automatic", loader: { ".css": "empty" }, alias: { "@src": path.join(FRONT, "src") }, nodePaths: [path.join(FRONT, "node_modules")], absWorkingDir: FRONT });
const SAMPLES = JSON.parse(cp.execFileSync("node", [outfile], { encoding: "utf8", maxBuffer: 1 << 26 }));
const CSS = { before: fs.readFileSync(BCSS, "utf8").replace(/@import[^;]+;/g, ""), after: fs.readFileSync(ACSS, "utf8").replace(/@import[^;]+;/g, "") };

const measure = () => {
  const px = (n) => Math.round(n * 100) / 100;
  const probe = (css) => { const e = document.createElement("span"); e.style.cssText = css; document.body.appendChild(e); const cs = getComputedStyle(e); const o = { color: cs.color, fontSize: cs.fontSize, fontWeight: cs.fontWeight, lineHeight: cs.lineHeight, gap: cs.paddingLeft }; e.remove(); return o; };
  const tokAccent = probe("color:var(--accent)").color, tokText = probe("color:var(--text-primary)").color;
  const tokFont = probe("font-size:var(--font-sm)").fontSize, tokWeight = probe("font-weight:var(--font-weight-medium)").fontWeight, tokLH = probe("line-height:var(--line-height-base)").lineHeight, tokGap = probe("padding-left:var(--space-2)").gap;
  const sample = document.querySelector("[data-sample]");
  const inp = sample.querySelector("input[type=checkbox]");
  const label = inp.closest("label");
  const root = label || inp;
  const ir = inp.getBoundingClientRect(), rr = root.getBoundingClientRect(), ics = getComputedStyle(inp);
  const o = { sampleW: px(sample.getBoundingClientRect().width), sampleH: px(sample.getBoundingClientRect().height), rootW: px(rr.width), rootH: px(rr.height), inputW: px(ir.width), inputH: px(ir.height), accentColor: ics.accentColor, inputFontSize: ics.fontSize, inputMarginLeft: ics.marginLeft, inputMarginTop: ics.marginTop };
  const tokSecondary = probe("color:var(--text-secondary)").color, tokSizeCb = probe("padding-left:var(--size-checkbox)").gap, tokSizeCbSm = probe("padding-left:var(--size-checkbox-sm)").gap;
  const tok = { tokAccent, tokText, tokFont, tokWeight, tokLH, tokGap, tokSecondary, tokSizeCb, tokSizeCbSm };
  if (label) {
    const textEl = label.querySelector(".comp-checkbox__label") || label.querySelector("span") || label;
    const w = document.createTreeWalker(textEl, NodeFilter.SHOW_TEXT, { acceptNode: (n) => (n.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT) });
    const tn = w.nextNode(); const rg = document.createRange(); rg.selectNodeContents(tn); const tr = rg.getBoundingClientRect();
    // 文字そのものの computed は text node の親要素（A 型は label、A' は span、金型は span.comp-checkbox__label）
    const cs = getComputedStyle(tn.parentElement);
    o.textFontSize = cs.fontSize; o.textFontWeight = cs.fontWeight; o.textColor = cs.color; o.textLineHeight = cs.lineHeight;
    o.inputToTextGap = px(tr.left - ir.right);
    o.vCenterOffsetInputMinusText = px((ir.top + ir.height / 2) - (tr.top + tr.height / 2));
    o.rootDisplay = getComputedStyle(label).display; o.rootAlignItems = getComputedStyle(label).alignItems;
  }
  // 左の TextField の入力枠との縦の中心のずれ（A-same-row のみ）
  const fields = [...sample.querySelectorAll(".comp-field input, .form-group input:not([type=checkbox])")];
  const same = fields.filter((f) => { const fr = f.getBoundingClientRect(); return fr.left < rr.left - 4 && Math.abs((fr.top + fr.height / 2) - (rr.top + rr.height / 2)) < 60; });
  if (same.length && root.parentElement && getComputedStyle(root.parentElement).display === "grid") {
    const f = same[same.length - 1].getBoundingClientRect();
    o.vCenterOffsetInputMinusLeftField = px((ir.top + ir.height / 2) - (f.top + f.height / 2));
  }
  // 上下の要素との間隔（縦に並ぶ場合のみ）
  // 金型が div で包まれる場合（E）は、包みごと（root の外側で兄弟が無い限り上へたどった要素）の外側との間隔を測る
  let ge = root; while (ge.parentElement && ge.parentElement !== sample && ge.parentElement.children.length === 1) ge = ge.parentElement;
  const gr = ge.getBoundingClientRect(), pe = ge.previousElementSibling ?? null, ne = ge.nextElementSibling ?? null;
  if (pe) { const pr = pe.getBoundingClientRect(); if (pr.bottom <= gr.top + 0.5) o.gapAbove = px(gr.top - pr.bottom); }
  if (ne) { const nr = ne.getBoundingClientRect(); if (nr.top >= gr.bottom - 0.5) o.gapBelow = px(nr.top - gr.bottom); }
  o.wrapW = px(gr.width); o.wrapIsRoot = ge === root ? "root" : ge.tagName.toLowerCase();
  { let e = inp, t = null; while (e && e !== sample.parentElement) { if (e.hasAttribute && e.hasAttribute("title")) { t = e.tagName.toLowerCase() + (e.className && typeof e.className === "string" ? "." + e.className.split(" ")[0] : ""); break; } e = e.parentElement; } o.titleOn = t || "なし"; }
  o.rootFlexShrink = getComputedStyle(root).flexShrink; o.inputFlexShrink = ics.flexShrink; o.userSelect = getComputedStyle(root).userSelect;
  // F: セル（td）の高さ
  const td = inp.closest("td"); if (td) { o.cellW = px(td.getBoundingClientRect().width); o.cellH = px(td.getBoundingClientRect().height); o.inputCenterXInCell = px((ir.left + ir.width / 2) - (td.getBoundingClientRect().left + td.getBoundingClientRect().width / 2)); }
  return { o, tok };
};
(async () => {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch(fs.existsSync(exe) ? { executablePath: exe } : {});
  const res = { chromium: b.version(), samples: SAMPLES.map((s) => ({ id: s.id, type: s.type, ref: s.ref })), results: [] };
  fs.mkdirSync(SHOTS, { recursive: true });
  const shotDone = new Set();
  for (const vw of [390, 1280]) for (const theme of ["light", "dark"]) {
    const page = await (await b.newContext({ viewport: { width: vw, height: 900 } })).newPage();
    for (const s of SAMPLES) for (const state of ["u", "c"]) for (const side of ["before", "after"]) {
      await page.setContent(`<!doctype html><html class="${theme === "dark" ? "force-dark" : ""}"><head><meta name="viewport" content="width=device-width"><style>${CSS[side]}</style></head><body style="margin:0">${s.html[side][state]}</body></html>`, { waitUntil: "load" });
      await page.waitForTimeout(60);
      const m = await page.evaluate(measure);
      res.results.push({ vw, theme, id: s.id, type: s.type, state: state === "c" ? "checked" : "unchecked", side, ...m });
      // 画像: 型ごと 1 件（最初の試料）、1280、チェック時、ライト/ダーク × 前/後
      const key = `${s.type}`;
      const first = SAMPLES.find((x) => x.type === s.type).id === s.id;
      if (state === "c" && first && (vw === 1280 || (vw === 390 && (s.type === "G2-same-row" || s.type === "G3")))) {
        const el = await page.$("[data-sample]");
        await el.screenshot({ path: path.join(SHOTS, `ay4c-${side}-${s.type}-${theme}-checked${vw === 390 ? "-390" : ""}.png`) });
      }
    }
    await page.context().close();
  }
  fs.writeFileSync(OUT, JSON.stringify(res, null, 1));
  await b.close();
  console.log("results", res.results.length);
})();
