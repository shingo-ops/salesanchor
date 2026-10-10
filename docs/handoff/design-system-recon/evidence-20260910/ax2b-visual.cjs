// AX-2b 外観実測（Chromium、幅1280・light）: 標準40件＋商品編集保留1件＋既存 <Textarea> 利用13件を、
// 旧規則のある現状（before）と、旧規則を取り除き TextareaControl 標準に替えた後（after）で比較する。
// 使い方（作業台のルートから）:
//   node docs/handoff/design-system-recon/evidence-20260910/ax2b-visual.cjs            … 事前計測（before と事前予測 after。調査時に実行済みで ax2b-visual.json に保存）
//   node docs/handoff/design-system-recon/evidence-20260910/ax2b-visual.cjs inputs-before … 実装前に同じ祖先の input の値を ax2b-visual.json の inputBefore に保存
//   node docs/handoff/design-system-recon/evidence-20260910/ax2b-visual.cjs after-real    … 実装後の実ファイルの CSS と実 DOM を計測し、ax2b-after-check.md を書く
// 注: 事前計測モードは調査時の入力（ax2-applied-css.json の 41 行版・ax2b-mold-users.json）が必要。after-real は ax2b-visual.json と ax2-applied-css.json（同ディレクトリ）だけを読む。
const fs = require("fs"), path = require("path"), os = require("os");
const W = path.resolve(__dirname, "..", "..", "..", "..");
const { chromium } = require(path.join(W, "frontend/node_modules/playwright"));
const postcss = require(path.join(W, "frontend/node_modules/postcss"));
const rdRaw = (f) => fs.readFileSync(path.join(W, f), "utf8");
const MODE = process.argv[2] || "predict";
const applied = JSON.parse(fs.readFileSync(path.join(__dirname, "ax2-applied-css.json"), "utf8"));
const moldUsers = MODE === "predict" ? JSON.parse(fs.readFileSync(path.join(__dirname, "ax2b-mold-users.json"), "utf8")) : [];
const FORM_FIELD = "frontend/src/components/FormField.css";
const norm = (s) => s.replace(/\s+/g, " ").trim();

// ---------- 旧規則の取り除き（after の CSS を作る。ファイルは書き換えない） ----------
const DROP = [
  /^\.form-group textarea(:focus)?$/,
  /^\.form-grid > \.form-row textarea(:focus)?$/,
  /^\.modal-content(-wide)? \.form-row textarea(:focus)?$/,
  /^\.product-edit-form \.form-group textarea$/,
  /^\.outbound-translation-edit(:focus)?$/,
];
function transformCss(file, text) {
  if (!/components\.css$|company-forms\.css$|supplier-detail-view\.css$|InboxPage\.css$/.test(file)) return text;
  const root = postcss.parse(text);
  // 旧 .form-group の宣言（商品編集の独立規則へ同値で写す）
  let baseDecls = null, focusDecls = null;
  if (/frontend\/src\/components\.css$/.test(file)) {
    baseDecls = []; focusDecls = [];
    root.walkRules((r) => {
      const sels = r.selectors.map(norm);
      if (sels.includes(".form-group textarea") && r.nodes) r.walkDecls((d) => baseDecls.push([d.prop, d.value]));
      if (sels.includes(".form-group textarea:focus")) r.walkDecls((d) => focusDecls.push([d.prop, d.value]));
      if (sels.includes(".form-group input") && !sels.includes(".form-group textarea") ) {}
    });
    // .form-group input, .form-group textarea の共有宣言は :19 側に含まれる（上の walk で textarea を含む規則として拾われる）
  }
  const dropped = [];
  root.walkRules((r) => {
    const sels = r.selectors.map(norm);
    const keep = sels.filter((s) => !DROP.some((re) => re.test(s)));
    if (keep.length === sels.length) {
      // .pmd-field textarea 単独規則: resize を落として min-height だけ残す
      if (sels.length === 1 && sels[0] === ".pmd-field textarea") { r.walkDecls("resize", (d) => d.remove()); dropped.push("pmd resize"); }
      return;
    }
    dropped.push(sels.filter((s) => !keep.includes(s)).join(", "));
    if (!keep.length) r.remove(); else r.selectors = keep;
  });
  // .pmd-field input, .pmd-field textarea の textarea 側だけ外す
  root.walkRules((r) => { const s = r.selectors.map(norm); if (s.includes(".pmd-field textarea") && s.length > 1) { r.selectors = s.filter((x) => x !== ".pmd-field textarea"); dropped.push(".pmd-field textarea (shared)"); } });
  return { css: root.toString(), baseDecls, focusDecls, dropped };
}
const afterCache = {};
function loadCss(file, mode) {
  const raw = file.endsWith("/index.css") ? rdRaw("frontend/src/index.css").replace(/@import\s+"\.\/tokens\.css";/, () => rdRaw("frontend/src/tokens.css")).replace(/@import\s+"\.\/components\/field-size\.css";/, () => rdRaw("frontend/src/components/field-size.css")) : rdRaw(file);
  if (mode === "before") return raw;
  if (!afterCache[file]) afterCache[file] = transformCss(file, raw);
  const t = afterCache[file]; return typeof t === "string" ? t : t.css;
}
// 商品編集保留用の独立規則（旧 .form-group textarea の宣言を同値で写す）
function productEditRule() {
  const t = transformCss("frontend/src/components.css", rdRaw("frontend/src/components.css"));
  const base = t.baseDecls.filter(([p]) => true);
  const decl = (arr) => arr.map(([p, v]) => `${p}: ${v};`).join(" ");
  // 旧 border は company-forms.css:254 で --border-strong に上書きされていたので同値で写す
  const b = base.map(([p, v]) => [p, p === "border" ? "1px solid var(--border-strong)" : v]);
  // focus は現行の計算値に合わせる: company-forms.css:254 の border ショートハンド（後勝ち・同特異度）が focus の border-color を打ち消しているため、現行の focus 枠色は --border-strong
  const f = t.focusDecls.map(([p, v]) => [p, p === "border-color" ? "var(--border-strong)" : v]);
  return `.product-edit-form .form-group textarea { ${decl(b)} }\n.product-edit-form .form-group textarea:focus { ${decl(f)} }\n`;
}
const PRODUCT_RULE = productEditRule();
const cssHtmlFor = (order, mode) => order.map((f) => {
  let c = loadCss(f, mode);
  if (mode === "after" && /company-forms\.css$/.test(f)) c += "\n" + PRODUCT_RULE;
  if (mode === "after") c += "";
  return `<style data-f="${f}">${c}</style>`;
}).join("\n");

const PROPS = [
  "padding-top", "padding-right", "padding-bottom", "padding-left",
  "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
  "border-top-style", "border-right-style", "border-bottom-style", "border-left-style",
  "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
  "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius", "border-bottom-left-radius",
  "font-size", "font-family", "font-weight", "line-height", "color", "background-color",
  "height", "min-height", "max-height", "width", "max-width", "resize",
  "outline-style", "outline-width", "outline-color", "outline-offset", "box-shadow", "box-sizing", "cursor", "opacity",
  "transition-property", "transition-duration",
];
const orderFor = (row) => {
  const o = ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)),
    ...row.cssImports.forwardClosure, ...row.cssImports.reverseImportersCss].filter((v, i, a) => a.indexOf(v) === i && v !== FORM_FIELD);
  o.push(FORM_FIELD); return o;
};
async function build(page, css, spec) {
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${css}</head><body></body></html>`);
  await page.evaluate((spec) => {
    let parent = document.body;
    for (const a of [...spec.ancestors].reverse()) { const e = document.createElement(a.tag); if (a.classes.length) e.className = a.classes.join(" "); parent.appendChild(e); parent = e; }
    if (spec.mold) { const w = document.createElement("div"); w.className = spec.mold.wrapCls; parent.appendChild(w); if (spec.mold.label) { const l = document.createElement("label"); l.className = "comp-field__label"; l.textContent = "L"; w.appendChild(l); } parent = w; }
    const t = document.createElement("textarea"); t.id = "t"; if (spec.cls) t.className = spec.cls; if (spec.rows) t.setAttribute("rows", spec.rows);
    t.setAttribute("placeholder", "ph"); if (spec.style) t.setAttribute("style", spec.style); parent.appendChild(t);
  }, spec);
}
const grab = (page) => page.locator("#t").evaluate((e, props) => {
  const c = getComputedStyle(e), o = {}; for (const k of props) o[k] = c.getPropertyValue(k);
  o["::placeholder color"] = getComputedStyle(e, "::placeholder").color; o.offsetHeight = e.offsetHeight; o.offsetWidth = e.offsetWidth; return o;
}, PROPS);
async function measure(page, css, spec, states) {
  await build(page, css, spec); const out = {}; const h = page.locator("#t"); await page.mouse.move(1, 1);
  out.normal = await grab(page);
  if (states) {
    await h.focus(); await page.waitForTimeout(300); out.focus = await grab(page); await h.evaluate((e) => e.blur());
    await h.evaluate((e) => { e.disabled = true; }); await page.waitForTimeout(300); out.disabled = await grab(page);
  }
  return out;
}
const groupOf = (r) => {
  const f = r.appliedRules.map((a) => a.file + ":" + a.line).join(",");
  if (/ProductEditPage/.test(r.file)) return "H 商品編集（保留）";
  if (/ExtractionPromptConfigTab/.test(r.file)) return "G6 抽出プロンプト（inline のみ）";
  if (/OutboundTranslationPreview/.test(r.file)) return "G3 送信下訳（.outbound-translation-edit）";
  if (/ProductMasterDrawer/.test(r.file)) return "G4 商品マスタドロワー（.pmd-field）";
  if (/company-forms\.css:(100|154)/.test(f)) return "G2 .form-row（company-forms.css）";
  if (/components\.css:19/.test(f)) return "G1 .form-group（components.css）";
  return "G5 CSS規則なし（ブラウザ既定）";
};
const parseInline = (style) => (style.props || []).filter((p) => p.prop[0] !== "(").map((p) => [p.prop, String(p.value).replace(/^['"]|['"]$/g, "")]);
async function predictMode() {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch({ executablePath: exe });
  const page = await (await b.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const warns = []; page.on("console", (m) => warns.push(`${m.type()}: ${m.text()}`)); page.on("pageerror", (e) => warns.push(`pageerror ${e}`));
  const res = { chromium: b.version(), viewport: "1280x800 light", props: PROPS, productEditRule: PRODUCT_RULE, targets: [], moldUsers: [] };
  for (const row of applied.rows) {
    const order = orderFor(row); const g = groupOf(row);
    const rowsAttr = row.attrs.rows ? (/(\d+)/.exec(row.attrs.rows) || [])[1] : null;
    const inline = parseInline(row.inlineStyle); const inlineCss = inline.map(([p, v]) => `${p}:${v}`).join(";");
    const cls = row.className.staticTokens.join(" ");
    const hold = /ProductEditPage/.test(row.file);
    const t = { file: row.file, line: row.line, group: g, beforeClass: cls, beforeInline: inlineCss, rows: rowsAttr, hasDisabledAttr: !!row.attrs.disabled, signatures: [] };
    const sigs = row.chains.distinctSignatures.slice(0, 20);
    for (const [i, sig] of sigs.entries()) {
      const anc = sig.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
      const before = await measure(page, cssHtmlFor(order, "before"), { ancestors: anc, cls, rows: rowsAttr, style: inlineCss }, true);
      const afterSpec = hold ? { ancestors: anc, cls, rows: rowsAttr, style: inlineCss } : { ancestors: anc, cls: "comp-field__textarea", rows: rowsAttr };
      const afterCss = cssHtmlFor(order, "after");
      const after = await measure(page, afterCss, afterSpec, true);
      const s = { sig: i, ancestors: anc.map((e) => e.tag + e.classes.map((c) => "." + c).join("")), before, after };
      if (inline.length && !hold) { // inline の宣言を 1 つずつ標準に足したときの効果（事実の測定。分類はしない）
        s.perDeclaration = {};
        for (const [p, v] of inline) s.perDeclaration[`${p}: ${v}`] = (await measure(page, afterCss, { ancestors: anc, cls: "comp-field__textarea", rows: rowsAttr, style: `${p}:${v}` }, false)).normal;
        s.afterWithAllInline = (await measure(page, afterCss, { ancestors: anc, cls: "comp-field__textarea", rows: rowsAttr, style: inlineCss }, false)).normal;
      }
      t.signatures.push(s);
    }
    res.targets.push(t); process.stderr.write(".");
  }
  // 既存 <Textarea> 利用（旧規則が当たるか。before/after の CSS だけが違う）
  const rowFor = (file) => applied.rows[0]; // CSS 集合は共通の global + 金型 CSS
  const moldOrder = ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)), FORM_FIELD];
  for (const u of moldUsers) {
    const rowsAttr = u.attrs.rows ? (/(\d+)/.exec(u.attrs.rows) || [])[1] : null;
    const wrap = ["comp-field", u.attrs.fullWidth ? "comp-field--full" : "", u.attrs.error ? "comp-field--error" : ""].filter(Boolean).join(" ");
    const rec = { file: u.file, line: u.line, attrs: u.attrs, signatures: [] };
    for (const [i, sig] of u.signatures.slice(0, 20).entries()) {
      const anc = sig.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
      const spec = { ancestors: anc, cls: "comp-field__textarea", rows: rowsAttr, mold: { wrapCls: wrap, label: !!u.attrs.label } };
      const before = await measure(page, cssHtmlFor(moldOrder.concat([]), "before"), spec, true);
      const after = await measure(page, cssHtmlFor(moldOrder, "after"), spec, true);
      rec.signatures.push({ sig: i, ancestors: anc.map((e) => e.tag + e.classes.map((c) => "." + c).join("")), unknown: sig.unknown, before, after });
    }
    res.moldUsers.push(rec);
  }
  res.warnings = warns; await b.close();
  fs.writeFileSync(path.join(__dirname, "ax2b-visual.json"), JSON.stringify(res));
  console.log("\ntargets", res.targets.length, "mold", res.moldUsers.length, "warnings", warns.length);
}

// ---------- 同じ祖先の input（共有規則の無影響確認用。ax2b-shared.md） ----------
const INPUT_CTX = [
  ["form-group", [["div", "form-group"]]],
  ["form-grid > form-row", [["div", "form-grid"], ["div", "form-row"]]],
  ["modal-content-wide form-row", [["div", "modal-content-wide"], ["div", "form-row"]]],
  ["modal-content form-row", [["div", "modal-content"], ["div", "form-row"]]],
  ["pmd-field", [["div", "pmd-fields"], ["label", "pmd-field"]]],
  ["product-edit-form form-group", [["form", "product-edit-form"], ["div", "form-group"]]],
  ["outbound-translation-section", [["div", "outbound-translation-section"]]],
];
const INPUT_TYPES = ["text", "email", "number", "date", "checkbox"];
const INPUT_PROPS = ["padding-top", "padding-right", "padding-bottom", "padding-left", "border-top-width", "border-top-style", "border-top-color", "border-top-left-radius", "font-size", "font-family", "line-height", "color", "background-color", "height", "min-height", "width", "resize", "outline-style", "outline-color", "box-shadow", "box-sizing", "cursor", "opacity"];
const inputOrder = () => ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)), "frontend/src/features/tcg-analysis-review/supplier-detail-view.css", "frontend/src/pages/inbox/InboxPage.css", FORM_FIELD].filter((v, i, a) => a.indexOf(v) === i);
async function measureInputs(page) {
  const out = {};
  for (const [name, anc] of INPUT_CTX) for (const ty of INPUT_TYPES) {
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${cssHtmlFor(inputOrder(), "before")}</head><body></body></html>`);
    await page.evaluate(({ anc, ty }) => { let p = document.body; for (const [tag, cls] of anc) { const e = document.createElement(tag); e.className = cls; p.appendChild(e); p = e; } const i = document.createElement("input"); i.id = "t"; i.type = ty; p.appendChild(i); }, { anc, ty });
    const h = page.locator("#t"); const grab = () => h.evaluate((e, props) => { const c = getComputedStyle(e), o = {}; for (const k of props) o[k] = c.getPropertyValue(k); o.offsetHeight = e.offsetHeight; o.offsetWidth = e.offsetWidth; return o; }, INPUT_PROPS);
    await page.mouse.move(1, 1); out[`${name}|${ty}|normal`] = await grab(); await h.focus(); await page.waitForTimeout(250); out[`${name}|${ty}|focus`] = await grab();
  }
  return out;
}
const launch = async () => { const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"); const b = await chromium.launch({ executablePath: exe }); const page = await (await b.newContext({ viewport: { width: 1280, height: 800 } })).newPage(); return { b, page }; };
async function inputsBefore() {
  const { b, page } = await launch(); const store = JSON.parse(fs.readFileSync(path.join(__dirname, "ax2b-visual.json"), "utf8"));
  store.inputBefore = await measureInputs(page); await b.close();
  fs.writeFileSync(path.join(__dirname, "ax2b-visual.json"), JSON.stringify(store));
  console.log("inputBefore conditions:", Object.keys(store.inputBefore).length);
}

// ---------- 実装後（実ファイルの CSS・実 DOM）の計測と事前予測との照合 ----------
const parseAnc = (arr) => arr.map((s) => { const [tag, ...cls] = s.split("."); return { tag, classes: cls }; });
const EXPECT_PATCH = { // 事前予測の after に設計どおりの変更を反映（調査の追加測定 ax2b-inline-facts.md）
  "frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx": { "font-family": "monospace" }, // textStyle=code
  "frontend/src/pages/staff-reports/StaffReportsPage.tsx:90": { height: "120px", "min-height": "120px", offsetHeight: 120 }, // minHeight の inline を保持
};
const ALLOWED_MOLD = { "frontend/src/components/MergeCompanyModal.tsx:246": { normal: ["border-top-color", "border-right-color", "border-bottom-color", "border-left-color"], disabled: ["border-top-color", "border-right-color", "border-bottom-color", "border-left-color", "background-color"], focus: [] } };
async function afterReal() {
  const { b, page } = await launch(); const store = JSON.parse(fs.readFileSync(path.join(__dirname, "ax2b-visual.json"), "utf8"));
  const KEYS = [...PROPS, "::placeholder color", "offsetHeight", "offsetWidth"];
  const cmp = (x, y) => KEYS.filter((k) => String(x[k]) !== String(y[k])).map((k) => ({ prop: k, a: x[k], b: y[k] }));
  const r1 = [], r2 = [], r2p = [], r3 = [], r4 = []; let n1 = 0, n2 = 0, n2p = 0, n3 = 0;
  for (const t of store.targets) {
    const key = `${t.file}:${t.line}`; const row = applied.rows.find((r) => r.file === t.file && r.line === t.line);
    if (!row) throw new Error("applied row not found " + key);
    const order = orderFor(row); const css = cssHtmlFor(order, "before"); // 実ファイルをそのまま読む
    const hold = /ProductEditPage|ProductMasterDrawer/.test(t.file); const isPmd = /ProductMasterDrawer/.test(t.file); const isExt = /ExtractionPromptConfigTab/.test(t.file); const isStaff = key.endsWith("StaffReportsPage.tsx:90");
    for (const s of t.signatures) {
      const anc = parseAnc(s.ancestors);
      const spec = hold ? { ancestors: anc, cls: t.beforeClass, rows: t.rows, style: t.beforeInline }
        : { ancestors: anc, cls: "comp-field__textarea" + (isExt ? " comp-textarea--code" : ""), rows: t.rows, style: isStaff ? t.beforeInline : "" };
      const real = await measure(page, css, spec, true);
      for (const st of ["normal", "focus", "disabled"]) {
        if (hold) { const d = cmp(s.before[st], real[st]); if (isPmd) { n2p++; if (d.length) r2p.push({ key, sig: s.sig, state: st, d }); } else { n2++; if (d.length) r2.push({ key, sig: s.sig, state: st, d }); } continue; }
        n1++; const pred = { ...s.after[st], ...(EXPECT_PATCH[t.file] || {}), ...(EXPECT_PATCH[key] || {}) };
        const d = cmp(pred, real[st]); if (d.length) r1.push({ key, group: t.group, sig: s.sig, state: st, d });
      }
    }
  }
  for (const u of store.moldUsers) {
    const key = `${u.file}:${u.line}`; const rowsAttr = u.attrs.rows ? (/(\d+)/.exec(u.attrs.rows) || [])[1] : null;
    const wrap = ["comp-field", u.attrs.fullWidth ? "comp-field--full" : "", u.attrs.error ? "comp-field--error" : ""].filter(Boolean).join(" ");
    const moldOrd = ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)), FORM_FIELD];
    for (const s of u.signatures) {
      const real = await measure(page, cssHtmlFor(moldOrd, "before"), { ancestors: parseAnc(s.ancestors), cls: "comp-field__textarea", rows: rowsAttr, mold: { wrapCls: wrap, label: !!u.attrs.label } }, true);
      for (const st of ["normal", "focus", "disabled"]) { n3++; const d = cmp(s.before[st], real[st]); const allowed = new Set((ALLOWED_MOLD[key] || {})[st] || []); const bad = d.filter((x) => !allowed.has(x.prop)); r3.push({ key, sig: s.sig, state: st, diffs: d, unexpected: bad }); }
    }
  }
  const inputsNow = await measureInputs(page); let n4 = 0;
  for (const [k, v] of Object.entries(store.inputBefore || {})) { n4++; const d = INPUT_PROPS.concat(["offsetHeight", "offsetWidth"]).filter((p) => String(v[p]) !== String(inputsNow[k][p])); if (d.length) r4.push({ k, d: d.map((p) => `${p}: ${v[p]} -> ${inputsNow[k][p]}`) }); }
  await b.close();
  const r3Unexpected = r3.filter((x) => x.unexpected.length);
  const r3Allowed = r3.filter((x) => x.diffs.length && !x.unexpected.length);
  let md = `# AX-2b 実装後の実測（after-real。Chromium ${store.chromium}、幅1280・light）\n\n実ファイルの CSS と実 DOM（TextareaControl 標準の出力 class、G6 は \`comp-textarea--code\` 付き、StaffReportsPage.tsx:90 は inline の minHeight を保持）を計測し、事前の before / 事前予測 after（ax2b-visual.json）と照合した。\n\n`;
  md += `事前予測側の調整（設計どおりの変更を反映）: G6 ExtractionPromptConfigTab は font-family を \`monospace\` に、StaffReportsPage.tsx:90 は height/min-height/offsetHeight を 120px に（minHeight を残すため）。\n\n`;
  md += `## (1) 標準38件（ProductMasterDrawer.tsx の2件は保留のため除く）: after-real と事前予測 after の差 — ${r1.length} 条件（比較 ${n1} 条件）\n\n`;
  for (const x of r1) md += `- ${x.key} sig${x.sig} ${x.state}: ${x.d.map((y) => `${y.prop}: 予測 ${String(y.a).slice(0, 40)} / 実測 ${String(y.b).slice(0, 40)}`).join("; ")}\n`;
  md += `\n## (2) 商品編集 ProductEditPage.tsx:309: before との差（normal・focus・disabled） — ${r2.length} 条件（比較 ${n2} 条件）\n\n`;
  for (const x of r2) md += `- ${x.key} sig${x.sig} ${x.state}: ${x.d.map((y) => `${y.prop}: ${y.a} → ${y.b}`).join("; ")}\n`;
  md += `\n## (2') 商品マスタ修正ドロワー ProductMasterDrawer.tsx:217/221（保留。未移管の生 textarea のまま）: before との差 — ${r2p.length} 条件（比較 ${n2p} 条件）\n\n`;
  for (const x of r2p) md += `- ${x.key} sig${x.sig} ${x.state}: ${x.d.map((y) => `${y.prop}: ${y.a} → ${y.b}`).join("; ")}\n`;
  md += `\n## (3) 既存 <Textarea> 金型 13 件: before との差 — 許容外 ${r3Unexpected.length} 条件、許容（MergeCompanyModal.tsx:246 の枠色・disabled 背景）${r3Allowed.length} 条件（比較 ${n3} 条件）\n\n`;
  for (const x of r3Allowed) md += `- 許容 ${x.key} sig${x.sig} ${x.state}: ${x.diffs.map((y) => `${y.prop}: ${y.a} → ${y.b}`).join("; ")}\n`;
  for (const x of r3Unexpected) md += `- 許容外 ${x.key} sig${x.sig} ${x.state}: ${x.unexpected.map((y) => `${y.prop}: ${y.a} → ${y.b}`).join("; ")}\n`;
  md += `\n## (4) 同じ祖先の input: before との差 — ${r4.length} 条件（比較 ${n4} 条件）\n\n`;
  for (const x of r4) md += `- ${x.k}: ${x.d.join("; ")}\n`;
  fs.writeFileSync(path.join(__dirname, "ax2b-after-check.md"), md);
  console.log(md);
  console.log(`counts: (1) ${r1.length} (2) ${r2.length} (2p) ${r2p.length} (3 unexpected) ${r3Unexpected.length} (3 allowed) ${r3Allowed.length} (4) ${r4.length}`);
  process.exit(r1.length === 0 && r2.length === 0 && r2p.length === 0 && r3Unexpected.length === 0 && r4.length === 0 ? 0 : 1);
}
(MODE === "predict" ? predictMode : MODE === "inputs-before" ? inputsBefore : MODE === "after-real" ? afterReal : () => { console.error("usage: ax2b-visual.cjs [predict|inputs-before|after-real]"); process.exit(2); })();
