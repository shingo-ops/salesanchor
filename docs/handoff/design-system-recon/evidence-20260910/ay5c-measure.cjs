// AY-5c 実測。使い方: node ay5c-measure.cjs <beforeCss> <afterCss> <outJson> <outTxt> <shotDir>
// 前: origin/main の vite build CSS ＋ 属性なしのマークアップ。後: 作業ツリーの vite build CSS ＋ data-current-label 付き。
const path = require("path"), fs = require("fs"), cp = require("child_process"), os = require("os");
const FRONT = path.resolve(__dirname, "../../../../frontend");
const { chromium } = require(path.join(FRONT, "node_modules/playwright"));
const esbuild = require(path.join(FRONT, "node_modules/esbuild"));
const [, , BCSS, ACSS, OUT, OUTTXT, SHOTS] = process.argv;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ay5c-"));
const outfile = path.join(tmp, "render.cjs");
esbuild.buildSync({ entryPoints: [path.join(__dirname, "ay5c-render.tsx")], bundle: true, platform: "node", format: "cjs", outfile, jsx: "automatic", loader: { ".css": "empty" }, alias: { "@src": path.join(FRONT, "src") }, nodePaths: [path.join(FRONT, "node_modules")], absWorkingDir: FRONT });
const HTML = JSON.parse(cp.execFileSync("node", [outfile], { encoding: "utf8", maxBuffer: 1 << 26 }));
const CSS = { before: fs.readFileSync(BCSS, "utf8").replace(/@import[^;]+;/g, ""), after: fs.readFileSync(ACSS, "utf8").replace(/@import[^;]+;/g, "") };
const measure = () => {
  const el = document.querySelector("label.color-swatch.selected.color-swatch-legacy");
  const a = getComputedStyle(el, "::after");
  return { content: a.content, fontSize: a.fontSize, color: a.color, bottom: a.bottom, left: a.left, transform: a.transform, whiteSpace: a.whiteSpace, dataAttr: el.getAttribute("data-current-label") };
};
(async () => {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch(fs.existsSync(exe) ? { executablePath: exe } : {});
  const res = { chromium: b.version(), results: [] };
  fs.mkdirSync(SHOTS, { recursive: true });
  for (const theme of ["light", "dark"]) {
    const page = await (await b.newContext({ viewport: { width: 1280, height: 400 } })).newPage();
    for (const [side, lang] of [["before", "ja"], ["after", "ja"], ["after", "en"]]) {
      await page.setContent(`<!doctype html><html lang="${lang}" class="${theme === "dark" ? "force-dark" : ""}"><head><meta name="viewport" content="width=device-width"><style>${CSS[side]}</style></head><body style="margin:0;background:var(--bg-primary,transparent)">${HTML[side][lang]}</body></html>`, { waitUntil: "load" });
      await page.waitForTimeout(60);
      const m = await page.evaluate(measure);
      res.results.push({ vw: 1280, theme, side, lang, ...m });
      const el = await page.$("[data-sample]");
      await el.screenshot({ path: path.join(SHOTS, `ay5c-${side}-${lang}-${theme}-1280.png`) });
    }
    await page.context().close();
  }
  await b.close();
  const keys = ["fontSize", "color", "bottom", "left", "transform", "whiteSpace"];
  const lines = [`chromium ${res.chromium}`];
  for (const r of res.results) lines.push(`${r.theme} ${r.side}-${r.lang}: content=${r.content} dataAttr=${r.dataAttr} ` + keys.map((k) => `${k}=${r[k]}`).join(" "));
  let diff = 0;
  for (const theme of ["light", "dark"]) {
    const bj = res.results.find((r) => r.theme === theme && r.side === "before" && r.lang === "ja");
    const aj = res.results.find((r) => r.theme === theme && r.side === "after" && r.lang === "ja");
    const ae = res.results.find((r) => r.theme === theme && r.side === "after" && r.lang === "en");
    const d = ["content", ...keys].filter((k) => bj[k] !== aj[k]);
    diff += d.length;
    lines.push(`判定 ${theme}: 前ja と 後ja の差=${d.length}${d.length ? " (" + d.join(",") + ")" : ""} / 後ja content=${aj.content} / 後en content=${ae.content} (期待 "Current": ${ae.content === '"Current"' ? "OK" : "NG"}) / 後en の位置系 前ja との差: ${["fontSize", "color", "bottom", "left", "transform", "whiteSpace"].filter((k) => ae[k] !== bj[k]).join(",") || "0"}`);
  }
  lines.push(`前ja と 後ja の差の合計=${diff}`);
  res.diffTotal = diff;
  fs.writeFileSync(OUT, JSON.stringify(res, null, 1));
  fs.writeFileSync(OUTTXT, lines.join("\n") + "\n");
  console.log(lines.join("\n"));
})();
