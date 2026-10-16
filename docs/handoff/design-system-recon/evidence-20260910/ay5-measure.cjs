// AY-5 実測。使い方: node ay5-measure.cjs <beforeCss> <afterCss> <outJson> <shotDir>
// 前: origin/main(b6435490b) の vite build CSS ＋ 変更前マークアップ。後: 作業ツリーの vite build CSS ＋ 本物の Radio / RadioControl の DOM。
const path = require("path"), fs = require("fs"), cp = require("child_process"), os = require("os");
const FRONT = path.resolve(__dirname, "../../../../frontend");
const { chromium } = require(path.join(FRONT, "node_modules/playwright"));
const esbuild = require(path.join(FRONT, "node_modules/esbuild"));
const [, , BCSS, ACSS, OUT, SHOTS] = process.argv;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ay5-"));
const outfile = path.join(tmp, "render.cjs");
esbuild.buildSync({ entryPoints: [path.join(__dirname, "ay5-render.tsx")], bundle: true, platform: "node", format: "cjs", outfile, jsx: "automatic", loader: { ".css": "empty" }, alias: { "@src": path.join(FRONT, "src") }, nodePaths: [path.join(FRONT, "node_modules")], absWorkingDir: FRONT });
const HTML = JSON.parse(cp.execFileSync("node", [outfile], { encoding: "utf8", maxBuffer: 1 << 26 }));
const CSS = { before: fs.readFileSync(BCSS, "utf8").replace(/@import[^;]+;/g, ""), after: fs.readFileSync(ACSS, "utf8").replace(/@import[^;]+;/g, "") };

const measure = (scene) => {
  const px = (n) => Math.round(n * 100) / 100;
  const S = document.querySelector("[data-sample]"), sr = S.getBoundingClientRect();
  const rel = (r) => ({ l: px(r.left - sr.left), t: px(r.top - sr.top), w: px(r.width), h: px(r.height) });
  const inputs = [...S.querySelectorAll("input[type=radio]")];
  const e = document.createElement("span"); e.style.color = "var(--accent)"; document.body.appendChild(e); const accentToken = getComputedStyle(e).color; e.remove();
  const o = { accentToken, nInputs: inputs.length, sampleW: px(sr.width), sampleH: px(sr.height) };
  inputs.forEach((inp, i) => {
    const n = i + 1, p = `i${n}_`, cs = getComputedStyle(inp), r = rel(inp.getBoundingClientRect());
    Object.assign(o, { [p + "left"]: r.l, [p + "top"]: r.t, [p + "w"]: r.w, [p + "h"]: r.h });
    Object.assign(o, { [p + "cssWidth"]: cs.width, [p + "cssHeight"]: cs.height, [p + "marginTop"]: cs.marginTop, [p + "marginRight"]: cs.marginRight, [p + "marginBottom"]: cs.marginBottom, [p + "marginLeft"]: cs.marginLeft,
      [p + "accentColor"]: cs.accentColor, [p + "cursor"]: cs.cursor, [p + "opacity"]: cs.opacity, [p + "position"]: cs.position,
      [p + "outlineStyle"]: cs.outlineStyle, [p + "outlineWidth"]: cs.outlineWidth, [p + "outlineColor"]: cs.outlineColor,
      [p + "focusVisible"]: inp.matches(":focus-visible"), [p + "checked"]: inp.checked });
    const par = inp.parentElement, pcs = getComputedStyle(par), pr = rel(par.getBoundingClientRect());
    Object.assign(o, { [p + "parentTag"]: par.tagName.toLowerCase(), [p + "parentLeft"]: pr.l, [p + "parentTop"]: pr.t, [p + "parentW"]: pr.w, [p + "parentH"]: pr.h,
      [p + "parentDisplay"]: pcs.display, [p + "parentBg"]: pcs.backgroundColor, [p + "parentCursor"]: pcs.cursor });
    if (scene === "r1") {
      Object.assign(o, { [p + "labelColumnGap"]: pcs.columnGap, [p + "labelRowGap"]: pcs.rowGap, [p + "labelMarginTop"]: pcs.marginTop, [p + "labelFontSize"]: pcs.fontSize, [p + "labelFontWeight"]: pcs.fontWeight,
        [p + "labelAlignItems"]: pcs.alignItems, [p + "labelLineHeight"]: pcs.lineHeight, [p + "labelFlexDirection"]: pcs.flexDirection });
      const lab = inp.closest("label");
      const lcs = getComputedStyle(lab), lr = rel(lab.getBoundingClientRect());
      Object.assign(o, { [p + "rootDisplay"]: lcs.display, [p + "rootW"]: lr.w, [p + "rootH"]: lr.h, [p + "rootTop"]: lr.t, [p + "rootLeft"]: lr.l,
        [p + "rootColumnGap"]: lcs.columnGap, [p + "rootRowGap"]: lcs.rowGap, [p + "rootMarginTop"]: lcs.marginTop, [p + "rootFontSize"]: lcs.fontSize, [p + "rootFontWeight"]: lcs.fontWeight,
        [p + "rootAlignItems"]: lcs.alignItems, [p + "rootLineHeight"]: lcs.lineHeight, [p + "rootCursor"]: lcs.cursor,
        [p + "containerW"]: px(lab.parentElement.getBoundingClientRect().width) });
      const tn = document.createTreeWalker(lab, NodeFilter.SHOW_TEXT, { acceptNode: (t) => (t.textContent.trim() ? 1 : 3) }).nextNode();
      const rg = document.createRange(); rg.selectNodeContents(tn); const tr = rel(rg.getBoundingClientRect());
      const tcs = getComputedStyle(tn.parentElement);
      Object.assign(o, { [p + "textLeft"]: tr.l, [p + "textTop"]: tr.t, [p + "textW"]: tr.w, [p + "textH"]: tr.h, [p + "textFontSize"]: tcs.fontSize, [p + "textFontWeight"]: tcs.fontWeight, [p + "textColor"]: tcs.color,
        [p + "gapInputToText"]: px(tr.l - (r.l + r.w)), [p + "inputCenterY"]: px(r.t + r.h / 2), [p + "textCenterY"]: px(tr.t + tr.h / 2) });
    }
    if (scene === "r5") {
      const tr = inp.closest("tr"), td = inp.closest("td"), trr = rel(tr.getBoundingClientRect()), tdr = rel(td.getBoundingClientRect());
      Object.assign(o, { [p + "trH"]: trr.h, [p + "trTop"]: trr.t, [p + "trW"]: trr.w, [p + "tdW"]: tdr.w, [p + "tdH"]: tdr.h, [p + "tdLeft"]: tdr.l });
    }
    if (scene === "r34") {
      const lab = inp.closest("label"), lr = rel(lab.getBoundingClientRect()), lcs = getComputedStyle(lab);
      Object.assign(o, { [p + "swatchW"]: lr.w, [p + "swatchH"]: lr.h, [p + "swatchLeft"]: lr.l, [p + "swatchTop"]: lr.t, [p + "swatchBg"]: lcs.backgroundColor, [p + "swatchBoxShadow"]: lcs.boxShadow, [p + "swatchBorder"]: lcs.borderTopColor,
        [p + "inputInSwatchLeft"]: px(r.l - lr.l), [p + "inputInSwatchTop"]: px(r.t - lr.t) });
    }
  });
  if (scene === "r1" && inputs.length >= 2) {
    const a = inputs[0].closest("label").getBoundingClientRect(), b = inputs[1].closest("label").getBoundingClientRect();
    o.rowTopDiff = px(b.top - a.top); o.rowGapBetween = px(b.top - a.bottom);
    const ta = inputs[0].getBoundingClientRect(), tb = inputs[1].getBoundingClientRect();
    o.inputTopDiff = px(tb.top - ta.top);
  }
  if (scene === "r5" && inputs.length >= 2) {
    o.rowTopDiff = px(inputs[1].closest("tr").getBoundingClientRect().top - inputs[0].closest("tr").getBoundingClientRect().top);
  }
  return o;
};
(async () => {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch(fs.existsSync(exe) ? { executablePath: exe } : {});
  const res = { chromium: b.version(), results: [] };
  fs.mkdirSync(SHOTS, { recursive: true });
  const SCENES = { r1: ["unchecked", "checked", "focus"], r34: ["unchecked", "checked"], r5: ["unchecked", "checked", "focus"] };
  for (const vw of [390, 1280]) for (const theme of ["light", "dark"]) {
    const page = await (await b.newContext({ viewport: { width: vw, height: 800 } })).newPage();
    for (const scene of Object.keys(SCENES)) for (const state of SCENES[scene]) for (const side of ["before", "after"]) {
      const src = HTML[side][scene][state === "unchecked" ? "u" : "c"];
      await page.setContent(`<!doctype html><html class="${theme === "dark" ? "force-dark" : ""}"><head><meta name="viewport" content="width=device-width"><style>${CSS[side]}</style></head><body style="margin:0;background:var(--bg-primary,transparent)">${src}</body></html>`, { waitUntil: "load" });
      await page.waitForTimeout(60);
      let focused = null;
      if (state === "focus") {
        focused = false;
        for (let k = 0; k < 6; k++) { await page.keyboard.press("Tab"); if (await page.evaluate(() => document.activeElement && document.activeElement.type === "radio")) { focused = true; break; } }
        await page.waitForTimeout(60);
      }
      const m = await page.evaluate(measure, scene);
      res.results.push({ vw, theme, scene, state, side, focused, ...m });
      const el = await page.$("[data-sample]");
      await el.screenshot({ path: path.join(SHOTS, `ay5-${side}-${scene}-${theme}-${state}-${vw}.png`) });
    }
    await page.context().close();
  }
  fs.writeFileSync(OUT, JSON.stringify(res, null, 1));
  await b.close();
  console.log("results", res.results.length);
})();
