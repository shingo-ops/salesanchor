// AY-2a 外観同等性: 対象33件の一行入力を、変更前（旧 class・旧 DOM）と変更後（金型の種類 class + 残す class）で
// Chromium の computed style と DPR2 画素で比較する（幅1280・375、light）。
// 使い方（作業台のルートから）: node docs/handoff/design-system-recon/evidence-20260910/ay2a-equivalence.cjs before|after
// before: 現在のソース（旧 class）を計測して保存。after: 種類 class の DOM を現在のソースで計測し before と比較。
// after は FormField.css を最後に読む順（先例 ax2a と同じ）と最初に読む順の2通りを計測する。
const fs = require("fs"), path = require("path"), os = require("os");
const ROOT = path.resolve(__dirname, "..", "..", "..", "..");
const { chromium } = require(path.join(ROOT, "frontend", "node_modules", "playwright"));
const rd = (f) => fs.readFileSync(path.join(ROOT, f), "utf8");
const applied = JSON.parse(fs.readFileSync(path.join(__dirname, "ay2-applied-css.json"), "utf8"));
const OUT = path.join(__dirname, "ay2a-equivalence.json");
const FORM_FIELD = "frontend/src/components/FormField.css";
const K = "frontend/src/pages/inbox/InboxKartePanel.tsx", P = "frontend/src/pages/inbox/InboxProfileModal.tsx";
// [file, line, variant, 残す className（変更後）, 変更前 className の補助指定]
const TARGETS = [
  ...[372, 379, 386, 404, 437, 443, 461, 569, 575, 581].map((l) => [K, l, "karte", ""]),
  ...[117, 122, 129, 148, 153, 158, 172, 178, 197, 238, 243, 248].map((l) => [P, l, "karte", ""]),
  [K, 509, "karte", "karte-field-empty"],
  ["frontend/src/pages/inbox/SalesFormMultiSelect.tsx", 148, "karte", "sales-form-other-input"],
  ["frontend/src/pages/inbox/InboxConversationList.tsx", 62, "search", "inbox-search-input"],
  ...[280, 324, 334, 347, 357, 369].map((l) => ["frontend/src/pages/schedule/SchedulePageImpl.tsx", l, "schedule", ""]),
  ["frontend/src/pages/dashboard/PriorityProspectsSection.tsx", 424, "composer", ""],
  ["frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx", 395, "composer", ""],
];
const idxCss = rd("frontend/src/index.css")
  .replace(/@import\s+"\.\/tokens\.css";/, () => rd("frontend/src/tokens.css"))
  .replace(/@import\s+"\.\/components\/field-size\.css";/, () => rd("frontend/src/components/field-size.css"));
const cssFor = (row, formFieldFirst) => {
  const base = ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)),
    ...row.cssImports.forwardClosure, ...row.cssImports.reverseImportersCss].filter((v, i, a) => a.indexOf(v) === i && v !== FORM_FIELD);
  const order = formFieldFirst ? [base[0], FORM_FIELD, ...base.slice(1)] : [...base, FORM_FIELD];
  return order.map((f) => `<style data-f="${f}">${f.endsWith("/index.css") ? idxCss : rd(f)}</style>`).join("\n");
};
const PROPS = [
  "padding-top", "padding-right", "padding-bottom", "padding-left",
  "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
  "border-top-style", "border-right-style", "border-bottom-style", "border-left-style",
  "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
  "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius", "border-bottom-left-radius",
  "font-size", "font-family", "font-weight", "font-style", "letter-spacing", "line-height", "color", "background-color", "background-image",
  "height", "min-height", "max-height", "width", "min-width", "max-width", "display", "flex-grow", "flex-shrink", "flex-basis", "align-self",
  "margin-top", "margin-right", "margin-bottom", "margin-left", "resize", "text-align", "text-indent", "text-overflow", "appearance",
  "outline-style", "outline-width", "outline-color", "outline-offset", "box-shadow", "box-sizing", "cursor", "opacity",
  "transition-property", "transition-duration", "transition-timing-function", "transition-delay",
];
const EXTRA = ["::placeholder color", "::placeholder opacity", "offsetHeight", "offsetWidth", "::datetime-edit color", "::datetime-edit visibility", "::datetime-edit opacity"];
const classSets = (t, mode) => {
  const empty = t[1] === 509 && t[0] === K; // G38: 空値で karte-field-empty が付く / 付かない の両方
  const oldCls = (extra) => ["right-panel-field", "schedule-input", "db-weekly-composer-input", "search-input-field"].filter(() => false).concat(extra);
  void oldCls;
  const beforeBase = { karte: "right-panel-field", search: "search-input-field", schedule: "schedule-input", composer: "db-weekly-composer-input" }[t[2]];
  const keep = t[3];
  const mk = (withKeep) => mode === "before"
    ? [beforeBase, t[0].endsWith("SalesFormMultiSelect.tsx") || t[0].endsWith("InboxConversationList.tsx") || (t[0] === K && t[1] === 509) ? (withKeep ? keep : "") : ""].filter(Boolean).join(" ")
    : ["comp-field__input", `comp-input--${t[2]}`, withKeep ? keep : ""].filter(Boolean).join(" ");
  return empty ? [["empty", mk(true)], ["filled", mk(false)]] : [["default", mk(true)]];
};
async function build(page, cssHtml, ancestors, type, cls, extraStyle) {
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${cssHtml}</head><body></body></html>`);
  await page.evaluate(({ ancestors, type, cls, extraStyle }) => {
    let parent = document.body;
    for (const a of [...ancestors].reverse()) { const e = document.createElement(a.tag); if (a.classes.length) e.className = a.classes.join(" "); parent.appendChild(e); parent = e; }
    const t = document.createElement("input"); t.id = "t"; if (type) t.setAttribute("type", type); if (cls) t.className = cls;
    t.setAttribute("placeholder", "ph"); if (extraStyle) t.setAttribute("style", extraStyle); parent.appendChild(t);
  }, { ancestors, type, cls, extraStyle });
}
const grab = (page) => page.locator("#t").evaluate((e, props) => {
  const c = getComputedStyle(e), o = {};
  for (const k of props) o[k] = c.getPropertyValue(k);
  const ph = getComputedStyle(e, "::placeholder"); o["::placeholder color"] = ph.color; o["::placeholder opacity"] = ph.opacity;
  if (e.getAttribute("type") === "date") { const d = getComputedStyle(e, "::-webkit-datetime-edit"); o["::datetime-edit color"] = d.color; o["::datetime-edit visibility"] = d.visibility; o["::datetime-edit opacity"] = d.opacity; }
  o.offsetHeight = e.offsetHeight; o.offsetWidth = e.offsetWidth;
  return o;
}, PROPS);
async function measure(page, cssHtml, ancestors, type, cls) {
  await build(page, cssHtml, ancestors, type, cls);
  const out = {}; const h = page.locator("#t");
  await page.mouse.move(1, 1);
  out.normal = await grab(page);
  await h.focus(); await page.waitForTimeout(350); out.focus = await grab(page);
  await h.evaluate((e) => e.blur());
  await h.evaluate((e) => { e.disabled = true; }); await page.waitForTimeout(350); out.disabled = await grab(page); // 33件とも disabled 属性なし: 参考値
  return out;
}
async function run(b, mode, formFieldFirst) {
  const res = { chromium: b.version(), targets: {}, warnings: [] };
  for (const width of [1280, 375]) {
    const ctx = await b.newContext({ viewport: { width, height: 800 }, colorScheme: "light" });
    const page = await ctx.newPage(); page.on("console", (m) => res.warnings.push(`${m.type()}: ${m.text()}`)); page.on("pageerror", (e) => res.warnings.push(`pageerror ${e}`));
    for (const t of TARGETS) {
      const row = applied.rows.find((r) => r.file === t[0] && r.line === t[1]);
      if (!row) throw new Error(`target not found in ay2-applied-css.json: ${t[0]}:${t[1]}`);
      const html = cssFor(row, formFieldFirst); const type = row.type === "omitted" ? null : row.type;
      for (const [cname, cls] of classSets(t, mode)) {
        const sigs = row.chains.distinctSignatures.slice(0, 20);
        for (const [i, sig] of sigs.entries()) {
          const anc = sig.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
          const key = `${t[0]}:${t[1]}|w${width}|${cname}|sig${i}`;
          res.targets[key] = { variant: t[2], cls, ancestors: anc.map((e) => e.tag + e.classes.map((c) => "." + c).join("")), states: await measure(page, html, anc, type, cls) };
        }
      }
    }
    await ctx.close();
  }
  // DPR2 画素: karte 1件（InboxKartePanel:372）と search 1件（InboxConversationList:62）。幅1280・375、通常と focus
  res.pixel = {};
  for (const t of TARGETS.filter((x) => (x[0] === K && x[1] === 372) || x[1] === 62)) {
    const row = applied.rows.find((r) => r.file === t[0] && r.line === t[1]); const html = cssFor(row, formFieldFirst);
    const [, cls] = classSets(t, mode)[0]; const sig = row.chains.distinctSignatures[0];
    const anc = sig.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes })); const type = row.type === "omitted" ? null : row.type;
    for (const width of [1280, 375]) {
      const ctx2 = await b.newContext({ viewport: { width, height: 2400 }, deviceScaleFactor: 2, colorScheme: "light" }); const p2 = await ctx2.newPage();
      for (const st of ["normal", "focus"]) {
        await build(p2, html, [{ tag: "div", classes: [] }], type, cls, "width:240px"); // 画素比較は祖先を外した素の div 直下（モバイルのボトムシート等で画面外になるため。祖先付きの値は computed 比較で担保）
        const h = p2.locator("#t"); await p2.mouse.move(1, 1); if (st === "focus") await h.focus();
        await p2.waitForTimeout(400);
                const box = await h.evaluate((e) => { const r = e.getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; });
        if (!(box.width > 0 && box.height > 0)) throw new Error(`zero-size box for pixel target ${t[0]}:${t[1]} w${width}`);
        let shot; try { shot = await p2.screenshot({ clip: { x: Math.max(0, box.x - 6), y: Math.max(0, box.y - 6), width: box.width + 12, height: box.height + 12 } }); } catch (e) { const dim = await p2.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.scrollHeight]); throw new Error(`pixel clip failed ${t[0]}:${t[1]} w${width} box=${JSON.stringify(box)} doc=${dim}: ${e.message.split("\n")[0]}`); }
        res.pixel[`${t[0]}:${t[1]}|w${width}|${st}`] = shot.toString("base64");
      }
      await ctx2.close();
    }
  }
  return res;
}
(async () => {
  const mode = process.argv[2];
  if (mode !== "before" && mode !== "after") { console.error("usage: node ay2a-equivalence.cjs before|after"); process.exit(2); }
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch({ executablePath: exe });
  if (mode === "before") {
    const before = await run(b, "before", false);
    fs.writeFileSync(OUT, JSON.stringify({ before, after: null }) + "\n");
    console.log(`before: chromium ${b.version()}, conditions ${Object.keys(before.targets).length}, warnings ${before.warnings.length}`);
    await b.close(); return;
  }
  const saved = JSON.parse(fs.readFileSync(OUT, "utf8")); const before = saved.before;
  const afters = { last: await run(b, "after", false), first: await run(b, "after", true) };
  const keys = [...PROPS, ...EXTRA];
  const result = {}; let allZero = true; const mdParts = [];
  const pg = await (await b.newContext()).newPage();
  for (const [order, after] of Object.entries(afters)) {
    const diffs = [], refDisabled = []; let conditions = 0;
    for (const [key, bt] of Object.entries(before.targets)) {
      const at = after.targets[key];
      for (const st of ["normal", "focus", "disabled"]) {
        const x = bt.states[st], y = at.states[st];
        const d = keys.filter((k) => x[k] !== y[k]).map((k) => ({ prop: k, before: x[k], after: y[k] }));
        conditions++;
        if (!d.length) continue;
        const rec = { key, variant: bt.variant, state: st, diffs: d };
        (st === "disabled" ? refDisabled : diffs).push(rec); // 33件とも disabled 属性なし → disabled は参考
      }
    }
    const pixel = [];
    for (const [pk, a] of Object.entries(before.pixel)) {
      const r = await pg.evaluate(async (s) => {
        const load = (b64) => new Promise((ok, ng) => { const i = new Image(); i.onload = () => ok(i); i.onerror = ng; i.src = "data:image/png;base64," + b64; });
        const [x, y] = await Promise.all([load(s.a), load(s.b)]);
        if (x.width !== y.width || x.height !== y.height) return { sizeMismatch: [x.width, x.height, y.width, y.height] };
        const px = (i) => { const cv = document.createElement("canvas"); cv.width = i.width; cv.height = i.height; const g = cv.getContext("2d"); g.drawImage(i, 0, 0); return g.getImageData(0, 0, i.width, i.height).data; };
        const da = px(x), dc = px(y); let n = 0;
        for (let k = 0; k < da.length; k += 4) if (da[k] !== dc[k] || da[k + 1] !== dc[k + 1] || da[k + 2] !== dc[k + 2] || da[k + 3] !== dc[k + 3]) n++;
        return { width: x.width, height: x.height, diffPixels: n };
      }, { a, b: after.pixel[pk] });
      pixel.push({ key: pk, ...r });
    }
    const pixelBad = pixel.filter((r) => r.sizeMismatch || r.diffPixels !== 0);
    result[order] = { conditions, judgedDiffConditions: diffs.length, diffs, referenceDisabledDiffConditions: refDisabled.length, referenceDisabled: refDisabled, pixel, pixelBad: pixelBad.length, warnings: [...before.warnings, ...after.warnings] };
    if (diffs.length || pixelBad.length) allZero = false;
    let md = `## FormField.css を${order === "last" ? "最後" : "最初（index.css の次）"}に読む順\n\n条件 ${conditions}（対象33件 × 幅2 × 祖先シグネチャ × 通常・focus・disabled、G38 は空値あり/なしの2通り。各 ${keys.length} 項目）。console 警告: ${result[order].warnings.length ? result[order].warnings.join("; ") : "なし"}\n\n### 判定対象（通常・focus）の computed 差分: ${diffs.length} 条件\n\n`;
    const bySum = {}; for (const d of diffs) { const k = `${d.variant}/${d.key.split("|")[1]}/${d.state}`; bySum[k] = (bySum[k] || 0) + 1; }
    md += `種類×幅×状態の差分条件数: ${JSON.stringify(bySum)}\n\n`;
    for (const d of diffs.slice(0, 60)) md += `- ${d.key} [${d.variant}] ${d.state}: ` + d.diffs.map((x) => `${x.prop}: ${String(x.before).slice(0, 50)} -> ${String(x.after).slice(0, 50)}`).join("; ") + "\n";
    md += `\n### 参考（33件とも disabled 属性なし。disabled を付けた状態）: 差分 ${refDisabled.length} 条件\n\n`;
    for (const d of refDisabled.slice(0, 6)) md += `- ${d.key}: ` + d.diffs.map((x) => `${x.prop}: ${String(x.before).slice(0, 40)} -> ${String(x.after).slice(0, 40)}`).join("; ") + "\n";
    md += `\n### DPR2 画素比較（karte 1件・search 1件、幅240px固定の clip、幅1280・375、通常・focus）\n\n| 対象 | サイズ(px) | 差分ピクセル |\n|---|---|---|\n`;
    for (const r of pixel) md += `| ${r.key} | ${r.sizeMismatch ? "不一致 " + r.sizeMismatch : r.width + "x" + r.height} | ${r.sizeMismatch ? "-" : r.diffPixels} |\n`;
    mdParts.push(md);
  }
  const strip = (r) => { delete r.pixel; return r; };
  fs.writeFileSync(OUT, JSON.stringify({ before, after: { last: strip(afters.last), first: strip(afters.first) }, result }, null, 1) + "\n");
  fs.writeFileSync(path.join(__dirname, "ay2a-equivalence.md"), `# AY-2a 外観同等性（Chromium ${b.version()}、light、幅1280・375）\n\n` + mdParts.join("\n"));
  console.log(mdParts.join("\n").slice(0, 9000));
  console.log(`order=last judged diffs: ${result.last.judgedDiffConditions}, pixel bad: ${result.last.pixelBad}; order=first judged diffs: ${result.first.judgedDiffConditions}, pixel bad: ${result.first.pixelBad}`);
  await b.close();
  process.exit(allZero ? 0 : 1);
})();
