// AY-4a 実測スクリプト。使い方: node ay4a-measure.cjs <beforeCss> <afterCss> <beforeDataTable.tsx> <afterDataTable.tsx> <outJson> <shotDir>
// 前: origin/main の DataTable.tsx + vite build CSS。後: 作業ツリーの DataTable.tsx + vite build CSS。
// どちらも DataTable を renderToStaticMarkup した HTML。indeterminate は DOM プロパティなので、"some" 状態では
// ページ側で「見出しの input.indeterminate = true」を前後とも同じ手順で設定する（実アプリでは prop/ref が設定）。
const path = require("path"), fs = require("fs"), cp = require("child_process"), os = require("os");
const FRONT = path.resolve(__dirname, "../../../../frontend");
const { chromium } = require(path.join(FRONT, "node_modules/playwright"));
const [, , BCSS, ACSS, BDT, ADT, OUT, SHOTS] = process.argv;
const esbuild = require(path.join(FRONT, "node_modules/esbuild"));
const render = (dt) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ay4a-"));
  const outfile = path.join(tmp, "render.cjs");
  esbuild.buildSync({ entryPoints: [path.join(__dirname, "ay4a-render.tsx")], bundle: true, platform: "node", format: "cjs", outfile, jsx: "automatic", loader: { ".css": "empty" }, alias: { "@dt": path.resolve(dt) }, nodePaths: [path.join(FRONT, "node_modules")], absWorkingDir: FRONT });
  return JSON.parse(cp.execFileSync("node", [outfile], { encoding: "utf8" }));
};
const HTML = { before: render(BDT), after: render(ADT) };
const CSS = { before: fs.readFileSync(BCSS, "utf8").replace(/@import[^;]+;/g, ""), after: fs.readFileSync(ACSS, "utf8").replace(/@import[^;]+;/g, "") };
const PROPS = ["width", "height", "marginTop", "marginRight", "marginBottom", "marginLeft", "cursor", "accentColor", "outlineStyle", "outlineWidth", "outlineColor", "display", "verticalAlign"];
const measure = ({ state, PROPS }) => {
  const boxes = [...document.querySelectorAll("input[type=checkbox]")];
  if (state === "some") boxes[0].indeterminate = true;
  return boxes.map((el, i) => {
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    const o = { which: i === 0 ? "header" : "row" + i, checked: el.checked, indeterminate: el.indeterminate, rectW: r.width, rectH: r.height };
    for (const p of PROPS) o[p] = cs[p];
    return o;
  });
};
(async () => {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch(fs.existsSync(exe) ? { executablePath: exe } : {});
  const res = { chromium: b.version(), results: {} };
  fs.mkdirSync(SHOTS, { recursive: true });
  for (const vw of [390, 1280]) for (const theme of ["light", "dark"]) {
    const page = await (await b.newContext({ viewport: { width: vw, height: 400 } })).newPage();
    for (const state of ["none", "all", "some"]) for (const side of ["before", "after"]) {
      await page.setContent(`<!doctype html><html class="${theme === "dark" ? "force-dark" : ""}"><head><meta name="viewport" content="width=device-width"><style>${CSS[side]}</style></head><body style="padding:16px">${HTML[side][state]}</body></html>`, { waitUntil: "load" });
      await page.waitForTimeout(100);
      const m = await page.evaluate(measure, { state, PROPS });
      (res.results[`${vw}/${theme}/${state}`] ??= {})[side] = m;
      if (vw === 1280) await page.screenshot({ path: path.join(SHOTS, `ay4a-${side}-${theme}-${state}.png`), clip: { x: 0, y: 0, width: 400, height: 160 } });
    }
    await page.context().close();
  }
  fs.writeFileSync(OUT, JSON.stringify(res, null, 1));
  await b.close();
  // 比較
  let total = 0; const diffs = {};
  for (const [cond, v] of Object.entries(res.results)) v.before.forEach((bo, i) => { const ao = v.after[i]; for (const k of Object.keys(bo)) { if (k === "which") continue; total++; if (bo[k] !== ao[k]) ((diffs[k] ??= {})[`${bo[k]} -> ${ao[k]}`] ??= []).push(`${cond}/${bo.which}`); } });
  const lines = [`比較した値の数: ${total}`, `条件数: ${Object.keys(res.results).length}（幅2×テーマ2×状態3）× 欄3（header, row1, row2）`];
  for (const [k, m] of Object.entries(diffs)) for (const [c, conds] of Object.entries(m)) lines.push(`DIFF ${k}: ${c}  [${conds.length}件]`);
  lines.push(`差のあった項目: ${Object.keys(diffs).join(",") || "なし"}`);
  fs.writeFileSync(OUT.replace(/\.json$/, "-compare.txt"), lines.join("\n") + "\n");
  console.log(lines.join("\n"));
})();
