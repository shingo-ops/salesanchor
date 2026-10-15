// AY-4c-2b 実測。使い方: node ay4c2b-measure.cjs <beforeCss> <afterCss> <outJson> <shotDir>
// 前: 8f6d089d6 の vite build CSS ＋ 変更前マークアップ。後: 作業ツリーの vite build CSS ＋ 本物の CheckboxControl の DOM。
const path = require("path"), fs = require("fs"), cp = require("child_process"), os = require("os");
const FRONT = path.resolve(__dirname, "../../../../frontend");
const { chromium } = require(path.join(FRONT, "node_modules/playwright"));
const esbuild = require(path.join(FRONT, "node_modules/esbuild"));
const [, , BCSS, ACSS, OUT, SHOTS] = process.argv;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ay4c2b-"));
const outfile = path.join(tmp, "render.cjs");
esbuild.buildSync({ entryPoints: [path.join(__dirname, "ay4c2b-render.tsx")], bundle: true, platform: "node", format: "cjs", outfile, jsx: "automatic", loader: { ".css": "empty" }, alias: { "@src": path.join(FRONT, "src") }, nodePaths: [path.join(FRONT, "node_modules")], absWorkingDir: FRONT });
const HTML = JSON.parse(cp.execFileSync("node", [outfile], { encoding: "utf8", maxBuffer: 1 << 26 }));
const CSS = { before: fs.readFileSync(BCSS, "utf8").replace(/@import[^;]+;/g, ""), after: fs.readFileSync(ACSS, "utf8").replace(/@import[^;]+;/g, "") };

const measure = () => {
  const px = (n) => Math.round(n * 100) / 100;
  const toRgb = (c) => { const e = document.createElement("span"); e.style.color = c; document.body.appendChild(e); const v = getComputedStyle(e).color; e.remove(); return v; };
  const rows = [...document.querySelectorAll("[data-row]")];
  const sample = document.querySelector("[data-sample]").getBoundingClientRect();
  const o = { nRows: rows.length, sampleH: px(sample.height), sampleW: px(sample.width) };
  rows.forEach((row, i) => {
    const n = i + 1, inp = row.querySelector("input[type=checkbox]"), sw = row.querySelector(".schedule-calendar-item__swatch");
    const rr = row.getBoundingClientRect(), ir = inp.getBoundingClientRect(), cs = getComputedStyle(inp), rcs = getComputedStyle(row);
    o[`r${n}_rowH`] = px(rr.height); o[`r${n}_rowW`] = px(rr.width); o[`r${n}_rowTop`] = px(rr.top - sample.top);
    o[`r${n}_inputW`] = px(ir.width); o[`r${n}_inputH`] = px(ir.height);
    o[`r${n}_marginL`] = cs.marginLeft; o[`r${n}_marginT`] = cs.marginTop; o[`r${n}_marginR`] = cs.marginRight; o[`r${n}_marginB`] = cs.marginBottom;
    o[`r${n}_accentColor`] = cs.accentColor;
    o[`r${n}_rightGap`] = px(rr.right - ir.right);
    o[`r${n}_swatchBg`] = getComputedStyle(sw).backgroundColor;
    o[`r${n}_swatchEqAccent`] = getComputedStyle(sw).backgroundColor === cs.accentColor ? "一致" : "不一致";
    o[`r${n}_cursor`] = cs.cursor; o[`r${n}_rowCursor`] = rcs.cursor; o[`r${n}_rowOpacity`] = rcs.opacity;
    o[`r${n}_checked`] = inp.checked; o[`r${n}_disabled`] = inp.disabled; o[`r${n}_flexShrink`] = cs.flexShrink;
  });
  return o;
};
(async () => {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch(fs.existsSync(exe) ? { executablePath: exe } : {});
  const res = { chromium: b.version(), results: [] };
  fs.mkdirSync(SHOTS, { recursive: true });
  for (const vw of [390, 1280]) for (const theme of ["light", "dark"]) {
    const page = await (await b.newContext({ viewport: { width: vw, height: 700 } })).newPage();
    for (const state of ["u", "c"]) for (const side of ["before", "after"]) {
      await page.setContent(`<!doctype html><html class="${theme === "dark" ? "force-dark" : ""}"><head><meta name="viewport" content="width=device-width"><style>${CSS[side]}</style></head><body style="margin:0;background:var(--bg-primary,transparent)">${HTML[side][state]}</body></html>`, { waitUntil: "load" });
      await page.waitForTimeout(60);
      const m = await page.evaluate(measure);
      res.results.push({ vw, theme, state: state === "c" ? "checked" : "unchecked", side, ...m });
      const el = await page.$("[data-sample]");
      await el.screenshot({ path: path.join(SHOTS, `ay4c2b-${side}-${theme}-${state === "c" ? "checked" : "unchecked"}-${vw}.png`) });
    }
    await page.context().close();
  }
  fs.writeFileSync(OUT, JSON.stringify(res, null, 1));
  await b.close();
  console.log("results", res.results.length);
})();
