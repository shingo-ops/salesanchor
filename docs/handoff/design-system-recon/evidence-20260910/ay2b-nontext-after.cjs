// AY-2b: 非 text input（checkbox/radio/range/file）の変更前後の見た目比較。
// before = origin/main 92db2c38b の frontend/src 全 CSS、after = 作業ツリー（PR HEAD）の全 CSS。どちらも同じ並べ順で結合し、同じ fixture を Chromium で描画して
// computed style 全項目 + 寸法を 幅1280・375 × normal・focus で比較する。並べ順は読み込み順が不定なので 昼夜 alpha / reverse / 競合規則を持つファイルを先頭・末尾に置いた順 を網羅する。
// 使い方: node ay2b-nontext-after.cjs <before-sha> <出力md> <出力json>
const fs = require("fs"), path = require("path"), os = require("os"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "../../../..");
const { chromium } = require(path.join(ROOT, "frontend/node_modules/playwright"));
const BASE = process.argv[2];
const sh = (c) => cp.execSync(c, { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 28 });
const cssList = sh(`git ls-tree -r --name-only ${BASE} frontend/src`).split("\n").filter((f) => f.endsWith(".css")).sort();
const strip = (t) => t.replace(/@import\s+[^;]+;/g, "");
const before = Object.fromEntries(cssList.map((f) => [f, strip(sh(`git show ${BASE}:${f}`))]));
const after = Object.fromEntries(cssList.map((f) => [f, strip(fs.readFileSync(path.join(ROOT, f), "utf8"))]));
const onlyNew = sh(`git ls-files frontend/src`).split("\n").filter((f) => f.endsWith(".css") && !cssList.includes(f));
const comp = JSON.parse(fs.readFileSync("/tmp/CC報告ファイル/ssot-ay2b/impl/nontext-competing-rules.json", "utf8"));
const compFiles = [...new Set(comp.inRange.map((r) => r.file.replace(/\\/g, "/")))];
const orders = [["alpha", cssList], ["reverse", [...cssList].reverse()]];
for (const f of compFiles) { orders.push([f.split("/").pop() + " last", [...cssList.filter((x) => x !== f), f]]); orders.push([f.split("/").pop() + " first", [f, ...cssList.filter((x) => x !== f)]]); }
// ---- fixture ----
const TYPES = ["checkbox", "radio", "range", "file"];
const inp = (t, extra = "") => `<input type="${t}" ${extra} data-fx>`;
const fx = []; // {id, html}
const add = (id, html) => fx.push({ id, html: `<div data-id="${id}">${html}</div>` });
const modal = (inner) => `<div class="comp-modal-overlay"><div class="comp-modal-dialog comp-modal-dialog--md"><div class="comp-modal-body">${inner}</div></div></div>`;
// A. 実 DOM 9 件（JSX の祖先連鎖どおり）
add("A1 PriorityScoreOverride:81 range", modal(`<p class="text-muted">x</p><form><div class="form-group"><label>score</label><input type="range" min="0" max="100" value="50" data-fx></div></form>`));
add("A2 ContactEditPage:171 checkbox", `<div class="page-layout"><form><div class="form-group"><label><input type="checkbox" data-fx> primary</label></div></form></div>`);
add("A3 FedexEtdSetupGuide:509 file", `<section class="etd-guide"><div class="etd-upload"><div class="etd-upload__grid"><div class="form-group"><label>l</label><p class="form-hint">h</p><input type="file" accept="image/gif,image/png" data-fx></div></div></div></section>`);
add("A4 FedexEtdSetupGuide:538 file", `<section class="etd-guide"><div class="etd-upload"><div class="etd-upload__grid"><div class="form-group"><label>s</label><p class="form-hint">h</p><input type="file" accept="image/gif,image/png" data-fx></div></div></div></section>`);
add("A5 RolesPage:506 radio legacy", `<div class="page roles-page">${modal(`<form><div class="form-group"><label>c</label><div class="color-picker" role="radiogroup"><label class="color-swatch selected color-swatch-legacy" style="background:#123456"><input type="radio" name="role-color" value="x" checked readonly data-fx></label></div></div></form>`)}</div>`);
add("A6 RolesPage:522 radio palette", `<div class="page roles-page">${modal(`<form><div class="form-group"><label>c</label><div class="color-picker" role="radiogroup"><label class="color-swatch" style="background:#abcdef"><input type="radio" name="role-color" value="y" data-fx></label><label class="color-swatch selected" style="background:#fedcba"><input type="radio" name="role-color" value="z" checked data-fx></label></div></div></form>`)}</div>`);
add("A7 RolesPage:562 checkbox", `<div class="page roles-page">${modal(`<div class="form-group"><label style="display:block;padding:var(--space-1)"><input type="checkbox" data-fx> <span class="badge">r</span></label></div>`)}</div>`);
add("A8 StaffEditPage:220 checkbox", `<div class="page-layout"><form><div class="form-group"><label><input type="checkbox" checked data-fx> pref</label></div></form></div>`);
add("A9 StaffPage:293 checkbox", `<div class="page-layout">${modal(`<form><div class="form-group"><label><input type="checkbox" data-fx> pref</label></div></form>`)}</div>`);
// B. 網羅: 競合規則の祖先クラス × .form-group の全組み合わせ（実在しない組み合わせも含めて、勝敗が変わりうる場所を全部測る）
const CHAINS = { "search-bar": ["<form class=\"search-bar\">", "</form>"], "toggle-switch": ["<label class=\"toggle-switch\">", "</label>"], "source-search": ["<div class=\"source-search\">", "</div>"], "pmd-field": ["<label class=\"pmd-field\">", "</label>"], "inbox-toggle": ["<label class=\"inbox-toggle\">", "</label>"], "topbar-search": ["<div class=\"topbar-search\">", "</div>"], "color-swatch": ["<label class=\"color-swatch\">", "</label>"], "chk-label": ["<label class=\"chk-label\">", "</label>"], "permission-item": ["<label class=\"permission-item\">", "</label>"], "sales-form-option": ["<label class=\"sales-form-option\">", "</label>"], "form-grid>form-row": ["<div class=\"form-grid\"><div class=\"form-row\">", "</div></div>"], "modal-content form-row": ["<div class=\"modal-content\"><div class=\"form-row\">", "</div></div>"], "modal-content-wide form-row": ["<div class=\"modal-content-wide\"><div class=\"form-row\">", "</div></div>"] };
for (const [k, [o, c]] of Object.entries(CHAINS)) for (const t of TYPES) {
  add(`B ${k} outer / form-group inner / ${t}`, `${o}<div class="form-group">${inp(t)}</div>${c}`);
  add(`B ${k} inner / form-group outer / ${t}`, `<div class="form-group">${o}${inp(t)}${c}</div>`);
}
const html = `<!doctype html><html><body>${fx.map((f) => f.html).join("\n")}</body></html>`;
const measure = async (page, state) => page.evaluate(async (state) => {
  const out = {};
  for (const wrap of document.querySelectorAll("[data-id]")) {
    const el = wrap.querySelector("[data-fx]"); if (!el) continue;
    if (state === "focus") el.focus();
    const cs = getComputedStyle(el); const o = {};
    for (let i = 0; i < cs.length; i++) o[cs[i]] = cs.getPropertyValue(cs[i]);
    const w0 = wrap.getBoundingClientRect(); const r = el.getBoundingClientRect(); const fg = el.closest(".form-group"); const q = fg.getBoundingClientRect(); // 位置は .form-group 基準（modal の position:fixed と先行 fixture の高さ変動の影響を避ける）
    o["#rect-in-fg"] = [r.x - q.x, r.y - q.y, r.width, r.height].map((v) => Math.round(v * 100) / 100).join(",");
    o["#offset"] = [el.offsetWidth, el.offsetHeight].join("x"); o["#fg-size"] = [q.width, q.height].map((v) => Math.round(v * 100) / 100).join("x"); o["#wrap-size"] = [Math.round(w0.width * 100) / 100, Math.round(w0.height * 100) / 100].join("x");
    out[wrap.getAttribute("data-id")] = o; if (state === "focus") el.blur();
  }
  return out;
}, state);
(async () => {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch({ executablePath: exe });
  const page = await (await b.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const res = { chromium: b.version(), baseSha: BASE, cssFiles: cssList.length, onlyInAfter: onlyNew, orders: orders.map((o) => o[0]), fixtures: fx.map((f) => f.id), diffs: [], measured: 0, elements: fx.length, selfCheck: null };
  const sheet = (set, order) => order.map((f) => `<style data-f="${f}">${set[f] || ""}</style>`).join("\n");
  let sampleBadge = null;
  for (const vw of [1280, 375]) for (const [oname, order] of orders) for (const state of ["normal", "focus"]) {
    await page.setViewportSize({ width: vw, height: 800 });
    const run = async (set) => { await page.setContent(html.replace("<body>", "<body>" + sheet(set, order)), { waitUntil: "load" }); return measure(page, state); };
    const mb = await run(before), ma = await run(after);
    for (const id of Object.keys(mb)) {
      res.measured++;
      const d = {}; const b1 = mb[id], a1 = ma[id];
      for (const k of new Set([...Object.keys(b1), ...Object.keys(a1)])) if (b1[k] !== a1[k]) d[k] = [b1[k], a1[k]];
      if (Object.keys(d).length) res.diffs.push({ vw, order: oname, state, id, diff: d });
    }
    if (!sampleBadge) sampleBadge = Object.keys(mb["A5 RolesPage:506 radio legacy"] || {}).length;
  }
  res.propsPerElement = sampleBadge;
  // 検出力の確認: 意図的に after の .form-group input[type=checkbox] 規則を壊すと差が出ること
  const broken = Object.fromEntries(Object.entries(after).map(([f, t]) => [f, f.endsWith("src/components.css") ? t.replace(/(\.form-group input\[type="checkbox"\],?)/, "$1 .zzz,").replace("padding: var(--space-2) var(--space-3);", "padding: 1px 2px;") : t]));
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.setContent(html.replace("<body>", "<body>" + sheet(before, cssList)), { waitUntil: "load" }); const mb = await measure(page, "normal");
  await page.setContent(html.replace("<body>", "<body>" + sheet(broken, cssList)), { waitUntil: "load" }); const mx = await measure(page, "normal");
  res.selfCheck = { ids: Object.keys(mb).filter((id) => JSON.stringify(mb[id]) !== JSON.stringify(mx[id])).length, note: "components.css の .form-group input[type=checkbox...] の padding を意図的に変えた after を比べ、差が検出されること（検出力の確認）" };
  await b.close();
  fs.writeFileSync(process.argv[4], JSON.stringify(res));
  const nzA = res.diffs.filter((d) => d.id.startsWith("A")).length, nzB = res.diffs.filter((d) => d.id.startsWith("B")).length; const nz = res.diffs.length;
  let md = `# nontext-after（非 text input の変更前後。Chromium ${res.chromium}、light）\n\n方法: before = ${BASE} の frontend/src 全 CSS ${cssList.length} ファイル、after = PR HEAD の全 CSS（作業ツリー）。@import は除去して結合。読み込み順が不定のため ${orders.length} 通りの並べ順（alpha・reverse・競合規則を持つ ${compFiles.length} ファイルを先頭/末尾に置いた順）で、幅 1280・375 × normal・focus、fixture ${fx.length} 要素（A: 実 DOM の 9 件、B: 競合クラス × .form-group の全組み合わせ ${fx.length - 9} 要素）を描画し、computed style 全項目（${res.propsPerElement} 項目）と getBoundingClientRect・offset 寸法・親 .form-group の寸法を比較。\n\n測定: ${res.measured} 比較（要素×並べ順×幅×状態）。差のある数: A（実 DOM 9 件と祖先連鎖どおりの実在の組み合わせ）**${nzA}**、B（網羅用の仮想の組み合わせ）**${nzB}**\n\n検出力の確認: ${res.selfCheck.note} → 差が出た要素数 ${res.selfCheck.ids}（0 でなければ検出できている）。\n\n`;
  if (nz) { md += "## 差分\n\n"; const g = {}; for (const d of res.diffs) { const k = d.id + " | " + Object.keys(d.diff).join(","); (g[k] = g[k] || []).push(d); } for (const [k, v] of Object.entries(g)) md += `- ${k} (${v.length}件; 例 ${v[0].vw}/${v[0].order}/${v[0].state}): ${Object.entries(v[0].diff).slice(0, 6).map(([p, x]) => p + " " + x[0] + " -> " + x[1]).join("; ")}\n`; } else md += "## 差分\n\nなし\n";
  md += `\n## fixture 一覧\n\n` + fx.map((f) => "- " + f.id).join("\n") + "\n";
  fs.writeFileSync(process.argv[3], md);
  console.log(JSON.stringify({ measured: res.measured, diffsA: nzA, diffsB: nzB, selfCheckDetected: res.selfCheck.ids, propsPerElement: res.propsPerElement, orders: orders.length, elements: fx.length }));
  process.exit(nzA ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
