// AY-2b 外観実測（Chromium、幅1280/375・light）。ax2b-visual.cjs と同じ方法を <input> に適用。
// 使い方: node ay2b-visual.cjs   （ay2-applied-css.json / ay2b-members.json / ay2b-mold-users.json を読み、ay2b-visual.json / .md を書く）
// before = 現行ソースの CSS・className・inline style。
// after  = 取り除く4規則（components.css:19/30, pages-layout.css:246/255）を postcss で落とした CSS（ファイルは書き換えない）＋ TextFieldControl 標準
//          （class は comp-field__input だけ。type/disabled/inline style は保持）。
const fs = require("fs"), path = require("path"), os = require("os");
const W = "/Users/tanizawashingo/worktrees/salesanchor/release-frontend-textfield-ay2b";
const { chromium } = require(path.join(W, "frontend/node_modules/playwright"));
const postcss = require(path.join(W, "frontend/node_modules/postcss"));
// 調査入力（祖先連鎖・メンバー一覧）。base HEAD fb036a238 時点の静的解決結果で、/tmp/CC報告ファイル/ay2b-recon/ に置いてある（evidence にはコピーしない）
const DATA = "/tmp/CC報告ファイル/ay2b-recon/";
const { execSync } = require("child_process");
// before / 事前予測 after の CSS は常に git HEAD（= base fb036a238）から読む。after-real だけが作業ツリーの実ファイルを読む。
const rdRaw = (f) => execSync(`git show HEAD:${f}`, { cwd: W, encoding: "utf8", maxBuffer: 1 << 26 });
const rdReal = (f) => fs.readFileSync(path.join(W, f), "utf8");
const applied = require(DATA + "ay2-applied-css.json");
const members = require(DATA + "ay2b-members.json");
const moldUsers = require(DATA + "ay2b-mold-users.json");
const FORM_FIELD = "frontend/src/components/FormField.css";
const norm = (s) => s.replace(/\s+/g, " ").trim();
const VIEWPORTS = [1280, 375];

// ---------- 規則の取り除き ----------
const DROP = {
  "frontend/src/components.css": [/^\.form-group input$/, /^\.form-group input:focus$/],
  "frontend/src/pages-layout.css": [/^\.login-card \.form-group input$/, /^\.login-card \.form-group input:focus$/],
};
const droppedLog = [];
const removedDecls = { base: null, focus: null, loginBase: null, loginFocus: null };
function transformCss(file, text) {
  const res = DROP[file]; if (!res) return text;
  const root = postcss.parse(text);
  root.walkRules((r) => {
    const sels = r.selectors.map(norm);
    const keep = sels.filter((s) => !res.some((re) => re.test(s)));
    if (keep.length === sels.length) return;
    const decls = []; r.walkDecls((d) => decls.push([d.prop, d.value]));
    droppedLog.push({ file, line: r.source.start.line, selector: sels.join(", "), removedWholeRule: !keep.length, decls });
    if (file.endsWith("components.css")) { if (/:focus$/.test(sels[0])) removedDecls.focus = decls; else removedDecls.base = decls; }
    else { if (/:focus$/.test(sels[0])) removedDecls.loginFocus = decls; else removedDecls.loginBase = decls; }
    if (!keep.length) r.remove(); else r.selectors = keep;
  });
  return root.toString();
}
const afterCache = {};
function loadCss(file, mode) {
  const raw = file.endsWith("/index.css") ? rdRaw("frontend/src/index.css").replace(/@import\s+"\.\/tokens\.css";/, () => rdRaw("frontend/src/tokens.css")).replace(/@import\s+"\.\/components\/field-size\.css";/, () => rdRaw("frontend/src/components/field-size.css")) : rdRaw(file);
  if (mode === "before") return raw;
  if (!(file in afterCache)) afterCache[file] = transformCss(file, raw);
  return afterCache[file];
}
// ---------- 商品編集 独立規則の候補（旧 .form-group input の宣言から border だけ除く。border は company-forms.css:238 が同値で持つ） ----------
let PRODUCT_RULE = "";
function buildProductRule() {
  const decl = (arr) => arr.map(([p, v]) => `${p}: ${v};`).join(" ");
  const base = removedDecls.base.filter(([p]) => p !== "border");
  const focus = removedDecls.focus.filter(([p]) => p !== "border-color");
  PRODUCT_RULE = `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]) { ${decl(base)} }\n.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]):focus { ${decl(focus)} }\n`;
}
// mode: before | after | after+product
const cssHtmlFor = (order, mode, extra) => order.map((f) => {
  let c = loadCss(f, mode === "before" ? "before" : "after");
  if (mode === "after+product" && /company-forms\.css$/.test(f)) c += "\n" + PRODUCT_RULE;
  if (extra && extra.file && f === extra.file) c += "\n" + extra.css;
  return `<style data-f="${f}">${c}</style>`;
}).join("\n");

const PROPS = [
  "padding-top", "padding-right", "padding-bottom", "padding-left",
  "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
  "border-top-style", "border-right-style", "border-bottom-style", "border-left-style",
  "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
  "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius", "border-bottom-left-radius",
  "font-size", "font-family", "font-weight", "line-height", "color", "background-color",
  "height", "min-height", "max-height", "width", "min-width", "max-width",
  "outline-style", "outline-width", "outline-color", "outline-offset", "box-shadow", "box-sizing", "cursor", "opacity",
  "transition-property", "transition-duration",
];
const orderFor = (row) => {
  const o = ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)),
    ...row.cssImports.forwardClosure, ...row.cssImports.reverseImportersCss].filter((v, i, a) => a.indexOf(v) === i && v !== FORM_FIELD);
  o.push(FORM_FIELD); return o;
};
const moldOrder = ["frontend/src/index.css", ...applied.globalCss.filter((f) => !/index\.css$|tokens\.css$|field-size\.css$/.test(f)), FORM_FIELD];

async function build(page, css, spec) {
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${css}</head><body></body></html>`);
  await page.evaluate((spec) => {
    let parent = document.body;
    for (const a of [...spec.ancestors].reverse()) { const e = document.createElement(a.tag); if (a.classes.length) e.className = a.classes.join(" "); parent.appendChild(e); parent = e; }
    if (spec.mold) { const w = document.createElement("div"); w.className = spec.mold.wrapCls; parent.appendChild(w); if (spec.mold.label) { const l = document.createElement("label"); l.className = "comp-field__label"; l.textContent = "L"; w.appendChild(l); } parent = w; }
    const t = document.createElement("input"); t.id = "t"; if (spec.cls) t.className = spec.cls;
    if (spec.type) t.setAttribute("type", spec.type);
    t.setAttribute("placeholder", "ph"); if (spec.style) t.setAttribute("style", spec.style); if (spec.disabledAttr) t.setAttribute("data-has-disabled", "1"); parent.appendChild(t);
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
    await h.focus(); await page.waitForTimeout(250); out.focus = await grab(page); await h.evaluate((e) => e.blur());
    if (spec.disabledAttr) { await h.evaluate((e) => { e.disabled = true; }); await page.waitForTimeout(250); out.disabled = await grab(page); }
  }
  return out;
}
const diffState = (b, a) => { const d = {}; for (const k of Object.keys(b)) if (b[k] !== a[k]) d[k] = [b[k], a[k]]; return d; };
const diffAll = (b, a) => { const d = {}; for (const st of Object.keys(b)) { const x = diffState(b[st], a[st] || {}); if (Object.keys(x).length) d[st] = x; } return d; };

const parseInline = (style) => (style.props || []).filter((p) => p.prop[0] !== "(").map((p) => [p.prop, String(p.value).replace(/^['"]|['"]$/g, "")]);
const typeAttr = (t) => (t === "omitted" ? null : t === "dynamic" ? "text" : t);
const ancLabel = (anc) => anc.map((e) => e.tag + e.classes.map((c) => "." + c).join("")).join("<");
const rowByLoc = new Map(applied.rows.map((r) => [r.file + ":" + r.line, r]));

function groupLabel(m) {
  const h = m.hitDefinite.join(" ");
  if (/pages-layout/.test(h)) return "G11 login (.login-card .form-group input)";
  if (m.inlineStyle) return "G28-31 .form-group input + inline style";
  return "G01 .form-group input";
}
// 代表選定: 件数5以下のグループは全員、大グループは「近傍4祖先シグネチャ × type × disabled」ごとに1件
function planTargets() {
  const targets = members.all.filter((m) => m.category === "target" && m.hitDefinite.length);
  const byGroup = new Map(); for (const m of targets) { const g = groupLabel(m); if (!byGroup.has(g)) byGroup.set(g, []); byGroup.get(g).push(m); }
  const plan = [];
  for (const [g, list] of byGroup) {
    const small = list.length <= 5; const seen = new Map();
    for (const m of list) {
      const row = rowByLoc.get(m.file + ":" + m.line);
      const sigs = row.chains.distinctSignatures.slice(0, small ? 3 : 20);
      for (const [i, sg] of sigs.entries()) {
        const anc = sg.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
        const key = small ? m.file + ":" + m.line + "#" + i : ancLabel(anc.slice(0, 4)) + "|" + m.type + "|" + m.disabledAttr + "|" + (m.inlineStyle || "");
        if (!small && seen.has(key)) { seen.get(key).coveredMembers.add(m.file + ":" + m.line); continue; }
        const rec = { group: g, key, row, member: m, anc, sigIndex: i, coveredMembers: new Set([m.file + ":" + m.line]) };
        if (!small) seen.set(key, rec); plan.push(rec);
      }
    }
  }
  return { plan, groupSizes: Object.fromEntries([...byGroup].map(([g, l]) => [g, l.length])) };
}
const specBefore = (rec, vw) => { const r = rec.row, inline = parseInline(r.inlineStyle); return { ancestors: rec.anc, cls: r.className.staticTokens.join(" "), type: typeAttr(r.type), style: inline.map(([p, v]) => `${p}:${v}`).join(";"), disabledAttr: !!r.attrs.disabled }; };
const specAfter = (rec) => { const b = specBefore(rec); return { ancestors: b.ancestors, cls: "comp-field__input", type: b.type, style: b.style, disabledAttr: b.disabledAttr }; };

(async () => {
  if (process.argv[2] === "after-real") return;
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch({ executablePath: exe });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } }); const page = await ctx.newPage();
  const warns = []; page.on("console", (m) => warns.push(`${m.type()}: ${m.text()}`)); page.on("pageerror", (e) => warns.push(`pageerror ${e}`));
  // after CSS を一度ロードして取り除き宣言を確定
  for (const f of Object.keys(DROP)) loadCss(f, "after"); buildProductRule();
  const res = { chromium: b.version(), viewports: VIEWPORTS.map((w) => w + " light"), props: PROPS, droppedRules: droppedLog, productEditRule: PRODUCT_RULE, targets: [], hold: [], moldUsers: [], nonText: [], loginVariant: null };

  // (a) 対象
  const { plan, groupSizes } = planTargets(); res.groupSizes = groupSizes;
  for (const vw of VIEWPORTS) {
    await page.setViewportSize({ width: vw, height: 800 });
    for (const rec of plan) {
      const order = orderFor(rec.row);
      const before = await measure(page, cssHtmlFor(order, "before"), specBefore(rec), true);
      const after = await measure(page, cssHtmlFor(order, "after"), specAfter(rec), true);
      const item = { vw, group: rec.group, file: rec.row.file, line: rec.row.line, type: rec.row.type, covered: [...rec.coveredMembers].length, ancestors: ancLabel(rec.anc.slice(0, 5)), inline: specBefore(rec).style, hasDisabledAttr: !!rec.row.attrs.disabled, diff: diffAll(before, after), before: before.normal, after: after.normal };
      if (item.inline) { const afterNoInline = await measure(page, cssHtmlFor(order, "after"), { ...specAfter(rec), style: "" }, false); item.diffNoInline = diffAll({ normal: before.normal }, { normal: afterNoInline.normal }); item.afterNoInline = afterNoInline.normal; }
      res.targets.push(item);
    }
    process.stderr.write(` a@${vw}`);
  }
  // (b) 商品編集 G06
  const holdRows = members.all.filter((m) => m.category === "product-edit(hold)");
  for (const vw of VIEWPORTS) {
    await page.setViewportSize({ width: vw, height: 800 });
    for (const m of holdRows) {
      const row = rowByLoc.get(m.file + ":" + m.line); const order = orderFor(row);
      const sg = row.chains.distinctSignatures[0]; const anc = sg.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
      const spec = { ancestors: anc, cls: row.className.staticTokens.join(" "), type: typeAttr(row.type), style: "", disabledAttr: !!row.attrs.disabled };
      const before = await measure(page, cssHtmlFor(order, "before"), spec, true);
      const afterOnly = await measure(page, cssHtmlFor(order, "after"), spec, true);
      const afterProd = await measure(page, cssHtmlFor(order, "after+product"), spec, true);
      res.hold.push({ vw, file: row.file, line: row.line, type: row.type, diffRulesRemovedOnly: diffAll(before, afterOnly), diffWithStandaloneRule: diffAll(before, afterProd) });
    }
    process.stderr.write(` b@${vw}`);
  }
  // (c) 既存 TextField/TextFieldControl（.form-group 配下）: 近傍4祖先×type×fullWidth/error/label ごとに1件
  const under = moldUsers.filter((u) => u.underFormGroupDefinite);
  res.moldUsersTotalUnderFormGroup = under.length;
  const moldReps = new Map();
  for (const u of under) {
    const fi = u; const type = (u.attrs.type || '"text"').replace(/^["']|["']$/g, "");
    const key = u.formGroupSigs[0].split("<").slice(0, 4).join("<") + "|" + type + "|" + !!u.attrs.fullWidth + "|" + !!u.attrs.error + "|" + !!u.attrs.label + "|" + (u.attrs.size || "") + "|" + (u.attrs.variant || "") + "|" + u.tag;
    if (!moldReps.has(key)) moldReps.set(key, { u, type, key, count: 0, files: new Set() }); const r = moldReps.get(key); r.count++; r.files.add(u.file);
  }
  const parseAnc = (label) => label.split("<").map((s) => { const [tag, ...cls] = s.split("."); return { tag, classes: cls }; });
  for (const vw of VIEWPORTS) {
    await page.setViewportSize({ width: vw, height: 800 });
    for (const r of moldReps.values()) {
      const u = r.u; const anc = parseAnc(u.formGroupSigs[0]).slice(0, 12);
      const size = (u.attrs.size || "").replace(/["']/g, "");
      const wrap = ["comp-field", size && size !== "md" ? `comp-field--${size}` : "", u.attrs.fullWidth ? "comp-field--full" : "", u.attrs.error ? "comp-field--error" : ""].filter(Boolean).join(" ");
      const ctrl = ["comp-field__input", size && size !== "md" ? `comp-field__input--${size}` : ""].filter(Boolean).join(" ");
      const spec = { ancestors: anc, cls: ctrl, type: r.type === "text" ? null : r.type, mold: { wrapCls: wrap, label: !!u.attrs.label }, disabledAttr: !!u.attrs.disabled };
      const before = await measure(page, cssHtmlFor(moldOrder, "before"), spec, true);
      const after = await measure(page, cssHtmlFor(moldOrder, "after"), spec, true);
      res.moldUsers.push({ vw, key: r.key, represents: r.count, files: [...r.files], ancestors: u.formGroupSigs[0].split("<").slice(0, 5).join("<"), type: r.type, attrs: u.attrs, diff: diffAll(before, after), before: before.normal, after: after.normal });
    }
    process.stderr.write(` c@${vw}`);
  }
  // (d) 非テキスト input（checkbox 等）: 旧規則が当たる全件（確定+未確定のみ）。要素は変えず規則だけ外す
  const nt = members.all.filter((m) => m.category === "non-text");
  for (const vw of VIEWPORTS) {
    await page.setViewportSize({ width: vw, height: 800 });
    for (const m of nt) {
      const row = rowByLoc.get(m.file + ":" + m.line); const order = orderFor(row);
      const sg = row.chains.distinctSignatures[0]; const anc = sg.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
      const inline = parseInline(row.inlineStyle).map(([p, v]) => `${p}:${v}`).join(";");
      const spec = { ancestors: anc, cls: row.className.staticTokens.join(" "), type: typeAttr(row.type), style: inline, disabledAttr: !!row.attrs.disabled };
      const before = await measure(page, cssHtmlFor(order, "before"), spec, true);
      const after = await measure(page, cssHtmlFor(order, "after"), spec, true);
      // 比較用: 旧規則が実際に当たらない（.form-group 外）ときの同要素（= 「規則なし」の素の値）も取る
      const bare = await measure(page, cssHtmlFor(order, "after"), { ...spec, ancestors: [{ tag: "div", classes: [] }] }, false);
      res.nonText.push({ vw, file: row.file, line: row.line, type: row.type, matchedBy: m.hitDefinite.length ? "definite" : "unconfirmed-only(ancestor not resolved)", ancestors: ancLabel(anc.slice(0, 4)), className: row.className.staticTokens.join(" "), inline, diff: diffAll(before, after), before: before.normal, after: after.normal, afterEqualsBare: Object.keys(diffState(after.normal, bare.normal)).length === 0 });
    }
    process.stderr.write(` d@${vw}`);
  }
  // (e) ログイン: 標準との差（(a) の G11）に加え、size=lg を当てたとき・variant 候補を当てたときの差
  const loginRows = members.all.filter((m) => m.category === "target" && m.hitDefinite.some((h) => /pages-layout/.test(h)));
  const baseD = removedDecls.base, loginD = removedDecls.loginBase;
  // 旧 .form-group input と .login-card .form-group input の合成（後勝ち）を comp-field__input 上の宣言として表す
  const merged = new Map(); for (const [p, v] of baseD) merged.set(p, v); for (const [p, v] of loginD) merged.set(p, v);
  const decl = (arr) => arr.map(([p, v]) => `${p}: ${v};`).join(" ");
  const loginCandidates = {
    "lg (size=lg 標準)": { cls: "comp-field__input comp-field__input--lg", css: "" },
    "variant候補A 旧2規則の宣言をそのまま写す": { cls: "comp-field__input comp-input--login", css: `.comp-field__input.comp-input--login { ${decl([...merged])} }\n.comp-field__input.comp-input--login:focus { ${decl([...new Map(removedDecls.focus.concat(removedDecls.loginFocus)).entries()])} }\n` },
    "variant候補B A + font-family(revert)/line-height/transition/min-height を現行値へ戻す": { cls: "comp-field__input comp-input--login", css: `.comp-field__input.comp-input--login { ${decl([...merged])} font-family: revert; line-height: normal; transition: all 0s; min-height: 0; }\n.comp-field__input.comp-input--login:focus { ${decl([...new Map(removedDecls.focus.concat(removedDecls.loginFocus)).entries()])} }\n` },
  };
  res.loginVariant = { removedBaseDecls: removedDecls.base, removedFocusDecls: removedDecls.focus, removedLoginBase: removedDecls.loginBase, removedLoginFocus: removedDecls.loginFocus, candidates: {}, rows: [] };
  for (const [name, c] of Object.entries(loginCandidates)) res.loginVariant.candidates[name] = { cls: c.cls, css: c.css, perViewport: {} };
  for (const vw of VIEWPORTS) {
    await page.setViewportSize({ width: vw, height: 800 });
    for (const m of loginRows) {
      const row = rowByLoc.get(m.file + ":" + m.line); const order = orderFor(row);
      const sg = row.chains.distinctSignatures[0]; const anc = sg.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes }));
      const specB = { ancestors: anc, cls: "", type: typeAttr(row.type), disabledAttr: false };
      const before = await measure(page, cssHtmlFor(order, "before"), specB, true);
      for (const [name, c] of Object.entries(loginCandidates)) {
        const after = await measure(page, cssHtmlFor(order, "after", { file: "frontend/src/company-forms.css", css: c.css }), { ...specB, cls: c.cls }, true);
        (res.loginVariant.candidates[name].perViewport[vw] = res.loginVariant.candidates[name].perViewport[vw] || []).push({ file: row.file, line: row.line, type: row.type, diff: diffAll(before, after) });
      }
    }
    process.stderr.write(` e@${vw}`);
  }
  res.warnings = warns; await b.close();
  fs.writeFileSync("ay2b-visual.json", JSON.stringify(res));
  console.log("\ntargets", res.targets.length, "hold", res.hold.length, "mold", res.moldUsers.length, "nonText", res.nonText.length, "warnings", warns.length);
})();

// ============ after-real: 実装後の実ファイルの CSS と実装後の DOM（ay2b-ast-check.json の after）で測り、before / 事前予測 after と比べる ============
async function afterReal() {
  const ast = require("./ay2b-ast-check.json");
  if (!ast.after) throw new Error("ay2b-ast-check.json に after が無い（先に node ay2b-ast-check.cjs after）");
  const TARGETS = new Set(members.all.filter((m) => m.category === "target" && m.hitDefinite.length).map((m) => m.file + ":" + m.line));
  const loginSet = new Set(members.all.filter((m) => m.category === "target" && m.hitDefinite.some((h) => /pages-layout/.test(h))).map((m) => m.file + ":" + m.line));
  const afterByLoc = new Map(ast.before.elements.map((e, i) => [e.file + ":" + e.line, ast.after.elements[i]]));
  const realCss = (order) => order.map((f) => {
    const raw = f.endsWith("/index.css") ? rdReal("frontend/src/index.css").replace(/@import\s+"\.\/tokens\.css";/, () => rdReal("frontend/src/tokens.css")).replace(/@import\s+"\.\/components\/field-size\.css";/, () => rdReal("frontend/src/components/field-size.css")) : rdReal(f);
    return `<style>${raw}</style>`;
  }).join("\n");
  const tsMod = require(path.join(W, "frontend/node_modules/typescript"));
  const styleToCss = (src) => {
    if (src === null || src === undefined) return "";
    const sf = tsMod.createSourceFile("s.tsx", `const x = <i style=${src} />;`, tsMod.ScriptTarget.Latest, true, tsMod.ScriptKind.TSX);
    let obj = null; (function v(n) { if (tsMod.isObjectLiteralExpression(n) && !obj) obj = n; tsMod.forEachChild(n, v); })(sf);
    return obj.properties.map((p) => p.name.getText(sf).replace(/[A-Z]/g, (m) => "-" + m.toLowerCase()) + ":" + p.initializer.text).join(";");
  };
  const strip = (s) => (s === undefined || s === null ? null : s.replace(/^["']|["']$/g, ""));
  // after 要素の DOM 仕様: TextFieldControl が出す class（comp-field__input [+ comp-input--variant] + className prop）と type・style・disabled を after の AST から読む
  const realSpec = (loc, anc) => {
    const e = afterByLoc.get(loc); const variant = strip(e.attrs.variant);
    const cls = ["comp-field__input", variant && variant !== "standard" ? "comp-input--" + variant : "", strip(e.className) || ""].filter(Boolean).join(" ");
    const ty = e.attrs.type === undefined ? null : (/^"/.test(e.attrs.type) ? strip(e.attrs.type) : "text");
    return { ancestors: anc, cls, type: ty, style: styleToCss(e.style), disabledAttr: e.attrs.disabled !== undefined, astTag: e.tag, astVariant: variant };
  };
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch({ executablePath: exe });
  const page = await (await b.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  for (const f of Object.keys(DROP)) loadCss(f, "after");
  const out = { chromium: b.version(), g1: [], g2: [], g3: [], g4: [], g5: [], g6: [] };
  const sigOf = (row, n) => row.chains.distinctSignatures.slice(0, n).map((sg) => sg.ancestorsInnermostFirst.map((e) => ({ tag: e.tag, classes: e.classes })));
  const rowOf = (m) => rowByLoc.get(m.file + ":" + m.line);
  const placementOnly = (style) => style.split(";").filter((d) => /^(width|min-width|max-width|flex|margin)/.test(d.trim())).join(";");
  for (const vw of VIEWPORTS) {
    await page.setViewportSize({ width: vw, height: 800 });
    // (1) text 系 140（login 除く）: before / 事前予測 after / after-real
    for (const m of members.all.filter((x) => x.category === "target" && x.hitDefinite.length)) {
      const loc = m.file + ":" + m.line; const row = rowOf(m); const order = orderFor(row); const login = loginSet.has(loc);
      for (const [si, anc] of sigOf(row, 1).entries()) {
        const sb = specBefore({ row, anc }); const rs = realSpec(loc, anc);
        const before = await measure(page, cssHtmlFor(order, "before"), sb, true);
        const real = await measure(page, realCss(order), rs, true);
        if (login) { out.g2.push({ vw, loc, sig: si, diff: diffAll(before, real), tag: rs.astTag, variant: rs.astVariant }); continue; }
        const predicted = await measure(page, cssHtmlFor(order, "after"), { ...specAfter({ row, anc }), style: placementOnly(sb.style) }, true);
        out.g1.push({ vw, loc, sig: si, type: row.type, diffPredVsReal: diffAll(predicted, real), diffBeforeVsReal: diffAll(before, real), inline: sb.style, tag: rs.astTag });
      }
    }
    process.stderr.write(" g1g2@" + vw);
    // (3) 商品編集 14
    for (const m of members.all.filter((x) => x.category === "product-edit(hold)")) {
      const row = rowOf(m); const order = orderFor(row); const anc = sigOf(row, 1)[0];
      const spec = { ancestors: anc, cls: row.className.staticTokens.join(" "), type: typeAttr(row.type), style: "", disabledAttr: !!row.attrs.disabled };
      const before = await measure(page, cssHtmlFor(order, "before"), spec, true); const real = await measure(page, realCss(order), spec, true);
      out.g3.push({ vw, loc: m.file + ":" + m.line, diff: diffAll(before, real) });
    }
    // (4) 非 text（確定 9 と祖先未確定 10 の全件、各 sig 最大 5）
    for (const m of members.all.filter((x) => x.category === "non-text")) {
      const row = rowOf(m); if (!row) { (out.g4skipped = out.g4skipped || new Set()).add(m.file + ":" + m.line); continue; } // 祖先連鎖の調査入力(415行版)が失われたため、行の無い非 text は ay2b-nontext-keep.json（実装前に102条件で差分0）で代替
      const order = orderFor(row);
      const inline = parseInline(row.inlineStyle).map(([p, v]) => `${p}:${v}`).join(";");
      for (const [si, anc] of sigOf(row, 2).entries()) {
        const spec = { ancestors: anc, cls: row.className.staticTokens.join(" "), type: typeAttr(row.type), style: inline, disabledAttr: !!row.attrs.disabled };
        const before = await measure(page, cssHtmlFor(order, "before"), spec, true); const real = await measure(page, realCss(order), spec, true);
        out.g4.push({ vw, loc: m.file + ":" + m.line, type: row.type, confirmed: !!m.hitDefinite.length, sig: si, diff: diffAll(before, real) });
      }
    }
    // (5) .form-group 内の既存 TextField 代表（ay2b-visual.cjs §3 と同じ代表の取り方）
    const under = (moldUsers.filter ? moldUsers : []).filter((u) => u.underFormGroupDefinite); const reps = new Map();
    for (const u of under) { const type = (u.attrs.type || '"text"').replace(/^["']|["']$/g, ""); const key = u.formGroupSigs[0].split("<").slice(0, 4).join("<") + "|" + type + "|" + !!u.attrs.fullWidth + "|" + !!u.attrs.error + "|" + !!u.attrs.label + "|" + (u.attrs.size || "") + "|" + (u.attrs.variant || "") + "|" + u.tag; if (!reps.has(key)) reps.set(key, { u, type, n: 0 }); reps.get(key).n++; }
    for (const r of reps.values()) {
      const u = r.u; const anc = u.formGroupSigs[0].split("<").slice(0, 12).map((s) => { const [tag, ...cls] = s.split("."); return { tag, classes: cls }; });
      const size = (u.attrs.size || "").replace(/["']/g, "");
      const wrap = ["comp-field", size && size !== "md" ? `comp-field--${size}` : "", u.attrs.fullWidth ? "comp-field--full" : "", u.attrs.error ? "comp-field--error" : ""].filter(Boolean).join(" ");
      const ctrl = ["comp-field__input", size && size !== "md" ? `comp-field__input--${size}` : ""].filter(Boolean).join(" ");
      const spec = { ancestors: anc, cls: ctrl, type: r.type === "text" ? null : r.type, mold: { wrapCls: wrap, label: !!u.attrs.label }, disabledAttr: !!u.attrs.disabled };
      const before = await measure(page, cssHtmlFor(moldOrder, "before"), spec, true); const real = await measure(page, realCss(moldOrder), spec, true);
      out.g5.push({ vw, rep: r.type + " x" + r.n + " " + u.formGroupSigs[0].split("<").slice(0, 3).join("<"), diff: diffAll(before, real) });
    }
    process.stderr.write(" g3g4g5@" + vw);
  }
  await b.close();
  // ---- 集計と書き出し ----
  const nz = (a, k) => a.filter((x) => Object.keys(x[k]).length);
  const radiusOnly = (d) => Object.values(d).every((st) => Object.keys(st).every((k) => /^border-.*-radius$/.test(k)));
  const g5bad = out.g5.filter((x) => Object.keys(x.diff).length && !radiusOnly(x.diff));
  const summary = {
    g1: { measurements: out.g1.length, elements: new Set(out.g1.map((x) => x.loc)).size, diffPredVsReal: nz(out.g1, "diffPredVsReal").length, diffBeforeVsReal: nz(out.g1, "diffBeforeVsReal").length },
    g2: { measurements: out.g2.length, elements: new Set(out.g2.map((x) => x.loc)).size, nonZero: nz(out.g2, "diff").length },
    g3: { measurements: out.g3.length, elements: new Set(out.g3.map((x) => x.loc)).size, nonZero: nz(out.g3, "diff").length },
    g4: { measurements: out.g4.length, elements: new Set(out.g4.map((x) => x.loc)).size, confirmedElements: new Set(out.g4.filter((x) => x.confirmed).map((x) => x.loc)).size, nonZero: nz(out.g4, "diff").length },
    g5: { measurements: out.g5.length, withRadiusDiff: out.g5.filter((x) => Object.keys(x.diff).length).length, nonRadiusDiff: g5bad.length },
  };
  fs.writeFileSync(path.join(__dirname, "ay2b-after-real.json"), JSON.stringify({ chromium: out.chromium, summary, ...out }));
  const fmt = (d) => Object.entries(d).map(([s, x]) => s + ": " + Object.entries(x).map(([k, v]) => k + " " + v[0] + " -> " + v[1]).join("; ")).join(" || ");
  let md = `# ay2b-after-check（実装後の実測。Chromium ${out.chromium}、幅 1280・375、light）\n\n方法: ay2b-visual.cjs after-real。before / 事前予測 after の CSS は git HEAD（base fb036a238）、after-real の CSS は作業ツリーの実ファイル（components.css 絞り込み規則・pages-layout.css・company-forms.css 独立規則・FormField.css login 規則を含む）。after-real の DOM は ay2b-ast-check.json の after（実装後の TSX の AST）から class（comp-field__input [+ comp-input--login]）・type・inline style・disabled を読む。祖先連鎖は base 時点の静的解決（移管で祖先は変わらない=ast-check で確認）。\n状態: normal・focus、disabled 属性がある要素は disabled も。\n\n| # | 区分 | 測定数 | 要素数 | 差のある数 | 期待 | 判定 |\n|---|---|---|---|---|---|---|\n`;
  const row = (n, name, s, bad, exp) => `| ${n} | ${name} | ${s.measurements} | ${s.elements || "-"} | ${bad} | ${exp} | ${bad === 0 ? "○" : "×"} |\n`;
  md += row(1, "text 系 140: after-real vs 事前予測 after", summary.g1, summary.g1.diffPredVsReal, "0");
  md += row(2, "ログイン 3: before vs after-real", summary.g2, summary.g2.nonZero, "0");
  md += row(3, "商品編集 14: before vs after-real", summary.g3, summary.g3.nonZero, "0");
  md += row(4, "非 text: before vs after-real（確定 9 + 祖先未確定 10）", summary.g4, summary.g4.nonZero, "0");
  md += row(5, ".form-group 内の既存 TextField 代表: before vs after-real（角丸以外）", summary.g5, summary.g5.nonRadiusDiff, "角丸以外 0（角丸 4→6px は許容）");
  md += `\n(5) の角丸差のあった代表: ${summary.g5.withRadiusDiff}/${summary.g5.measurements}\n\n`;
  const bad = [...nz(out.g1, "diffPredVsReal").map((x) => ["(1)", x.vw, x.loc, fmt(x.diffPredVsReal)]), ...nz(out.g2, "diff").map((x) => ["(2)", x.vw, x.loc, fmt(x.diff)]), ...nz(out.g3, "diff").map((x) => ["(3)", x.vw, x.loc, fmt(x.diff)]), ...nz(out.g4, "diff").map((x) => ["(4)", x.vw, x.loc, fmt(x.diff)]), ...g5bad.map((x) => ["(5)", x.vw, x.rep, fmt(x.diff)])];
  md += bad.length ? "## 食い違い\n\n" + bad.map((b2) => `- ${b2[0]} ${b2[1]} ${b2[2]}: ${b2[3]}`).join("\n") + "\n" : "## 食い違い\n\nなし\n";
  const ex = out.g1.filter((x) => x.inline);
  md += `\n## 参考: inline style を持つ 4 件の after-real（配置宣言は保持、InventoryPicker の padding は外れて標準の余白）\n\n` + ex.filter((x) => x.sig === 0 && x.vw === 1280).map((x) => `- ${x.loc} inline(before)=${x.inline}`).join("\n") + "\n";
  const dB = out.g1.filter((x) => x.vw === 1280 && x.sig === 0 && Object.keys(x.diffBeforeVsReal).length).length;
  md += `\n## 参考: (1) の before → after-real で差のある要素（幅1280・sig0）: ${dB} / ${out.g1.filter((x) => x.vw === 1280 && x.sig === 0).length}（角丸・書体・行の高さ等。主な値は ay2b-visual.md §1）\n`;
  fs.writeFileSync(path.join(__dirname, "ay2b-after-check.md"), md);
  console.log(JSON.stringify(summary, null, 1)); console.log("mismatches:", bad.length);
  process.exit(bad.length ? 1 : 0);
}
if (process.argv[2] === "after-real") afterReal().catch((e) => { console.error(e); process.exit(2); });
