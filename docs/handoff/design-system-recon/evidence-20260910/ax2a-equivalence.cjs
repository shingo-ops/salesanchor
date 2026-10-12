// AX-2a 外観同等性: 対象12件の textarea を、変更前（旧 class・旧 DOM）と変更後（金型の種類 class）で
// Chromium の computed style と DPR2 画素で比較する。
// 使い方（作業台のルートから）: node docs/handoff/design-system-recon/evidence-20260910/ax2a-equivalence.cjs before|after
// before: 現在のソース（旧 class）を計測して保存。after: 種類 class の DOM を現在のソースで計測し before と比較。
const fs = require("fs"), path = require("path"), os = require("os");
const ROOT = path.resolve(__dirname, "..", "..", "..", "..");
const { chromium } = require(path.join(ROOT, "frontend", "node_modules", "playwright"));
const rd = (f) => fs.readFileSync(path.join(ROOT, f), "utf8");
const applied = JSON.parse(fs.readFileSync(path.join(__dirname, "ax2-applied-css.json"), "utf8"));
const OUT = path.join(__dirname, "ax2a-equivalence.json");
const FORM_FIELD = "frontend/src/components/FormField.css";
// 対象12件（ax2-applied-css.json の file:line → 種類と残す className）
const TARGETS = [
  ["frontend/src/pages/inbox/InboxKartePanel.tsx", 484, "karte", ""], ["frontend/src/pages/inbox/InboxKartePanel.tsx", 503, "karte", ""],
  ["frontend/src/pages/inbox/InboxKartePanel.tsx", 537, "karte", ""], ["frontend/src/pages/inbox/InboxKartePanel.tsx", 588, "karte", ""],
  ["frontend/src/pages/inbox/InboxProfileModal.tsx", 181, "karte", ""], ["frontend/src/pages/inbox/InboxProfileModal.tsx", 191, "karte", ""],
  ["frontend/src/pages/inbox/InboxProfileModal.tsx", 210, "karte", ""], ["frontend/src/pages/inbox/InboxProfileModal.tsx", 265, "karte", ""],
  ["frontend/src/pages/inbox/InboxMessageThread.tsx", 736, "embedded", "inbox-textarea"],
  ["frontend/src/pages/dashboard/PriorityProspectsSection.tsx", 410, "composer", ""], ["frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx", 381, "composer", ""],
  ["frontend/src/pages/schedule/SchedulePageImpl.tsx", 378, "schedule", ""],
];
const JUDGED_DISABLED = new Set(["frontend/src/pages/inbox/InboxMessageThread.tsx:736"]); // disabled 属性を持つもの
const idxCss = rd("frontend/src/index.css")
  .replace(/@import\s+"\.\/tokens\.css";/, () => rd("frontend/src/tokens.css"))
  .replace(/@import\s+"\.\/components\/field-size\.css";/, () => rd("frontend/src/components/field-size.css"));
const cssFor = (row) => {
  const order = ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)),
    ...row.cssImports.forwardClosure, ...row.cssImports.reverseImportersCss].filter((v, i, a) => a.indexOf(v) === i && v !== FORM_FIELD);
  order.push(FORM_FIELD);
  return { order, html: order.map((f) => `<style data-f="${f}">${f.endsWith("/index.css") ? idxCss : rd(f)}</style>`).join("\n") };
};
const PROPS = [
  "padding-top", "padding-right", "padding-bottom", "padding-left",
  "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
  "border-top-style", "border-right-style", "border-bottom-style", "border-left-style",
  "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
  "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius", "border-bottom-left-radius",
  "font-size", "font-family", "font-weight", "line-height", "color", "background-color", "background-image",
  "height", "min-height", "max-height", "width", "min-width", "max-width", "flex-grow", "flex-shrink", "flex-basis", "resize",
  "outline-style", "outline-width", "outline-color", "outline-offset", "box-shadow", "box-sizing", "cursor", "opacity",
  "transition-property", "transition-duration", "transition-timing-function", "text-align", "overflow-y",
];
const SPEC = (row, mode, target) => {
  const rowsAttr = row.attrs.rows ? (/(\d+)/.exec(row.attrs.rows) || [])[1] : null;
  const cls = mode === "before" ? row.className.staticTokens.join(" ")
    : ["comp-field__textarea", `comp-textarea--${target[2]}`, target[3]].filter(Boolean).join(" ");
  return { rows: rowsAttr, cls };
};
async function build(page, cssHtml, ancestors, spec, extraStyle) {
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${cssHtml}</head><body></body></html>`);
  await page.evaluate(({ ancestors, spec, extraStyle }) => {
    let parent = document.body;
    for (const a of [...ancestors].reverse()) { const e = document.createElement(a.tag); if (a.classes.length) e.className = a.classes.join(" "); parent.appendChild(e); parent = e; }
    const t = document.createElement("textarea"); t.id = "t"; if (spec.cls) t.className = spec.cls; if (spec.rows) t.setAttribute("rows", spec.rows);
    t.setAttribute("placeholder", "ph"); if (extraStyle) t.setAttribute("style", extraStyle); parent.appendChild(t);
  }, { ancestors, spec, extraStyle });
}
const grab = (page) => page.locator("#t").evaluate((e, props) => {
  const c = getComputedStyle(e), o = {};
  for (const k of props) o[k] = c.getPropertyValue(k);
  o["::placeholder color"] = getComputedStyle(e, "::placeholder").color;
  o.offsetHeight = e.offsetHeight; o.offsetWidth = e.offsetWidth; o._focused = document.activeElement === e;
  return o;
}, PROPS);
async function measure(page, cssHtml, ancestors, spec) {
  await build(page, cssHtml, ancestors, spec);
  const out = {}; const h = page.locator("#t");
  await page.mouse.move(1, 1);
  out.normal = await grab(page);
  await h.focus(); await page.waitForTimeout(350); out.focus = await grab(page);
  await h.evaluate((e) => e.blur());
  await h.evaluate((e) => { e.disabled = true; }); await page.waitForTimeout(350); out.disabled = await grab(page);
  return out;
}
(async () => {
  const mode = process.argv[2];
  if (mode !== "before" && mode !== "after") { console.error("usage: node ax2a-equivalence.cjs before|after"); process.exit(2); }
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch({ executablePath: exe });
  const page = await (await b.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const warns = []; page.on("console", (m) => warns.push(`${m.type()}: ${m.text()}`)); page.on("pageerror", (e) => warns.push(`pageerror ${e}`));
  const res = { chromium: b.version(), viewport: "1280x800 light", targets: {} };
  for (const t of TARGETS) {
    const row = applied.rows.find((r) => r.file === t[0] && r.line === t[1]);
    if (!row) throw new Error(`target not found in ax2-applied-css.json: ${t[0]}:${t[1]}`);
    const { order, html } = cssFor(row);
    const spec = SPEC(row, mode, t);
    const sigs = row.chains.distinctSignatures.slice(0, 20);
    const key = `${t[0]}:${t[1]}`;
    res.targets[key] = { variant: t[2], cssOrder: order, spec, signatures: [] };
    for (const [i, sig] of sigs.entries()) {
      const anc = sig.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
      res.targets[key].signatures.push({ sig: i, ancestors: anc.map((e) => e.tag + e.classes.map((c) => "." + c).join("")), states: await measure(page, html, anc, spec) });
    }
    // DPR2 画素比較用: karte の1件と embedded の1件
    if (t[1] === 484 || t[1] === 736) {
      const anc = sigs[0].ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
      const ctx2 = await b.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 });
      const p2 = await ctx2.newPage(); res.targets[key].pixel = {};
      for (const st of ["normal", "focus"]) {
        await build(p2, html, anc, spec, "width:240px");
        const h = p2.locator("#t"); await p2.mouse.move(1, 1);
        if (st === "focus") await h.focus();
        await p2.waitForTimeout(400);
        const box = await h.boundingBox();
        res.targets[key].pixel[st] = (await p2.screenshot({ clip: { x: box.x - 6, y: box.y - 6, width: box.width + 12, height: box.height + 12 } })).toString("base64");
      }
      await ctx2.close();
    }
  }
  res.warnings = warns; const ver = b.version();
  if (mode === "before") {
    fs.writeFileSync(OUT, JSON.stringify({ before: res, after: null }) + "\n");
    console.log(`before: chromium ${ver}, targets ${Object.keys(res.targets).length}, warnings ${warns.length}`);
    await b.close(); return;
  }
  const saved = JSON.parse(fs.readFileSync(OUT, "utf8"));
  const before = saved.before;
  const diffs = [], refDisabled = [];
  let conditions = 0;
  for (const [key, bt] of Object.entries(before.targets)) {
    const at = res.targets[key];
    for (let i = 0; i < bt.signatures.length; i++) {
      for (const st of ["normal", "focus", "disabled"]) {
        const x = bt.signatures[i].states[st], y = at.signatures[i].states[st];
        const d = [...PROPS, "::placeholder color", "offsetHeight", "offsetWidth"].filter((k) => x[k] !== y[k]).map((k) => ({ prop: k, before: x[k], after: y[k] }));
        conditions++;
        if (!d.length) continue;
        const rec = { key, variant: bt.variant, sig: i, state: st, diffs: d };
        if (st === "disabled" && !JUDGED_DISABLED.has(key)) refDisabled.push(rec); else diffs.push(rec);
      }
    }
  }
  // 画素比較
  const pixel = [];
  const pg = await (await b.newContext()).newPage();
  for (const [key, bt] of Object.entries(before.targets)) {
    if (!bt.pixel) continue;
    for (const st of ["normal", "focus"]) {
      const r = await pg.evaluate(async (s) => {
        const load = (b64) => new Promise((ok, ng) => { const i = new Image(); i.onload = () => ok(i); i.onerror = ng; i.src = "data:image/png;base64," + b64; });
        const [a, c] = await Promise.all([load(s.a), load(s.b)]);
        if (a.width !== c.width || a.height !== c.height) return { sizeMismatch: [a.width, a.height, c.width, c.height] };
        const px = (i) => { const cv = document.createElement("canvas"); cv.width = i.width; cv.height = i.height; const g = cv.getContext("2d"); g.drawImage(i, 0, 0); return g.getImageData(0, 0, i.width, i.height).data; };
        const da = px(a), dc = px(c); let n = 0;
        for (let k = 0; k < da.length; k += 4) if (da[k] !== dc[k] || da[k + 1] !== dc[k + 1] || da[k + 2] !== dc[k + 2] || da[k + 3] !== dc[k + 3]) n++;
        return { width: a.width, height: a.height, diffPixels: n };
      }, { a: bt.pixel[st], b: res.targets[key].pixel[st] });
      pixel.push({ key, variant: bt.variant, state: st, ...r });
    }
  }
  const pixelBad = pixel.filter((r) => r.sizeMismatch || r.diffPixels !== 0);
  const summary = {}; for (const d of diffs) { const k = `${d.variant}/${d.state}`; summary[k] = (summary[k] || 0) + 1; }
  const out = { chromium: ver, conditions, judgedDiffConditions: diffs.length, judgedDiffBy: summary, diffs, referenceDisabledDiffConditions: refDisabled.length, referenceDisabled: refDisabled, pixel, warnings: [...before.warnings, ...warns] };
  const strip = (r) => { for (const t of Object.values(r.targets)) delete t.pixel; return r; };
  fs.writeFileSync(OUT, JSON.stringify({ before, after: strip(res), result: out }, null, 1) + "\n");
  let md = `# AX-2a 外観同等性（Chromium ${ver}、幅1280・light）\n\n対象12件、祖先シグネチャ別に 通常・focus・disabled を実測（${conditions} 条件、各 ${PROPS.length + 3} 項目＋::placeholder の color）。console 警告: ${out.warnings.length ? out.warnings.join("; ") : "なし"}\n\n`;
  md += `## 判定対象の computed 差分: ${diffs.length} 条件\n\n`;
  for (const d of diffs) md += `- ${d.key} [${d.variant}] sig${d.sig} ${d.state}: ` + d.diffs.map((x) => `${x.prop}: ${String(x.before).slice(0, 50)} -> ${String(x.after).slice(0, 50)}`).join("; ") + "\n";
  md += `\n## 参考（disabled 属性を持たないものに disabled を付けた状態）: 差分 ${refDisabled.length} 条件\n\n`;
  for (const d of refDisabled) md += `- ${d.key} [${d.variant}] sig${d.sig}: ` + d.diffs.map((x) => `${x.prop}: ${String(x.before).slice(0, 40)} -> ${String(x.after).slice(0, 40)}`).join("; ") + "\n";
  md += `\n## DPR2 画素比較（karte 1件・embedded 1件、幅240px固定の clip）\n\n| 対象 | 種類 | 状態 | サイズ(px) | 差分ピクセル |\n|---|---|---|---|---|\n`;
  for (const r of pixel) md += `| ${r.key} | ${r.variant} | ${r.state} | ${r.sizeMismatch ? "不一致 " + r.sizeMismatch : r.width + "x" + r.height} | ${r.sizeMismatch ? "-" : r.diffPixels} |\n`;
  fs.writeFileSync(path.join(__dirname, "ax2a-equivalence.md"), md);
  console.log(md.slice(0, 6000));
  console.log(`judged diffs: ${diffs.length}, pixel bad: ${pixelBad.length}`);
  await b.close();
  process.exit(diffs.length === 0 && pixelBad.length === 0 ? 0 : 1);
})();
