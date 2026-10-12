// AW-2b 外観実測: Chromium で computed style を変更前後に記録する。
// (A) 保留: 商品編集 `.product-edit-form .form-group select`（通常・focus）
// (B) 保留: CommissionPanel と同じ祖先（Modal 内の表の td）の素の select
// (C) 代表グループ: before は旧 DOM、after は SelectControl の出力 class
// 使い方（作業台のルートから）: node docs/handoff/design-system-recon/evidence-20260910/aw2b-visual.cjs before|after
const fs = require("fs"), path = require("path"), os = require("os");
const ROOT = path.resolve(__dirname, "..", "..", "..", "..");
const { chromium } = require(path.join(ROOT, "frontend", "node_modules", "playwright"));
const SRC = path.join(ROOT, "frontend", "src");
const rd = (f) => fs.readFileSync(path.join(SRC, f), "utf8");
const idx = rd("index.css")
  .replace(/@import\s+"\.\/tokens\.css";/, () => rd("tokens.css"))
  .replace(/@import\s+"\.\/components\/field-size\.css";/, () => rd("components/field-size.css"));
const order = [
  "index.css (+@import tokens.css, components/field-size.css inlined)",
  "components.css", "company-forms.css", "pages/inbox/InboxPage.css",
  "pages/goal-setting/GoalSettingPage.css", "pages/account-settings/account-settings.css",
  "pages/schedule.css", "components/FormField.css",
];
const css = [idx, ...order.slice(1).map(rd)].map((c) => `<style>${c}</style>`).join("\n");
const OPTS = "<option>A</option><option>B</option>";
const PROPS = [
  "padding-top", "padding-right", "padding-bottom", "padding-left",
  "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
  "border-top-style", "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
  "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius", "border-bottom-left-radius",
  "font-size", "font-family", "color", "background-color", "background-image",
  "height", "min-height", "width", "line-height", "appearance", "cursor",
  "box-shadow", "outline-style", "outline-width", "outline-color",
];

const SC = "comp-select__control";
const G = (before, after, wrapBefore, wrapAfter) => ({ before, after, wrapBefore, wrapAfter });
const wrap = (open, close) => (inner) => `${open}${inner}${close}`;
const formGroup = wrap('<div class="form-group"><label>L</label>', "</div>");
const formGrid = wrap('<div class="form-grid"><div class="form-row"><label>L</label>', "</div></div>");
const modalWide = wrap('<div class="modal-content-wide"><div class="form-row"><label>L</label>', "</div></div>");
const toolbar = wrap('<div class="content-toolbar">', "</div>");
const gsWrap = wrap('<div class="gs-team-select-wrap">', "</div>");
const inboxWrap = wrap('<div class="inbox-page-filter-wrap">', "</div>");
const plain = (x) => x;

// (A)(B) は変更前後とも同一 DOM（保留のため移管しない）
const HELD = {
  A_product_edit: { html: `<form class="product-edit-form"><div class="form-group"><label>L</label><select id="t">${OPTS}</select></div></form>`, states: ["normal", "focus"] },
  B_commission_panel: { html: `<div class="comp-modal-overlay"><div class="comp-modal-dialog comp-modal-dialog--lg"><div class="comp-modal-body"><table class="data-table"><tbody><tr><td>L</td><td><select id="t">${OPTS}</select></td></tr></tbody></table></div></div></div>`, states: ["normal", "focus"] },
};
// (C) 代表グループ
const GROUPS = {
  "C1 .form-group select (md full)": [formGroup, `<select id="t">`, `<select id="t" class="${SC} ${SC}--full">`],
  "C2 .form-grid > .form-row select (md full)": [formGrid, `<select id="t">`, `<select id="t" class="${SC} ${SC}--full">`],
  "C3 .modal-content-wide .form-row select (md full)": [modalWide, `<select id="t">`, `<select id="t" class="${SC} ${SC}--full">`],
  "C4 field-w-sm toolbar (md, field-h-md field-w-sm)": [toolbar, `<select id="t" class="field-h-md field-w-sm">`, `<select id="t" class="${SC} field-w-sm">`],
  "C5 field field-h-md in form-group (md full)": [formGroup, `<select id="t" class="field field-h-md">`, `<select id="t" class="${SC} ${SC}--full">`],
  "C6 .gs-select (sm)": [gsWrap, `<select id="t" class="gs-select">`, `<select id="t" class="${SC} ${SC}--sm gs-select">`],
  "C7 .account-settings-lang-select (sm)": [plain, `<select id="t" class="account-settings-lang-select">`, `<select id="t" class="${SC} ${SC}--sm account-settings-lang-select">`],
  "C8 .inbox-page-filter-select (sm full)": [inboxWrap, `<select id="t" class="inbox-page-filter-select">`, `<select id="t" class="${SC} ${SC}--sm ${SC}--full">`],
  "C9 .inbox-settings-select (sm)": [plain, `<select id="t" class="inbox-settings-select">`, `<select id="t" class="${SC} ${SC}--sm">`],
  "C10 .schedule-input (sm full)": [plain, `<select id="t" class="schedule-input">`, `<select id="t" class="${SC} ${SC}--sm ${SC}--full">`],
  "C11 decoration-free (md)": [plain, `<select id="t">`, `<select id="t" class="${SC}">`],
};

async function measure(page, html, state) {
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${css}</head><body style="margin:20px">${html}</body></html>`);
  const h = page.locator("#t");
  await page.mouse.move(1, 1);
  if (state === "focus") await h.focus();
  await page.waitForTimeout(250);
  return h.evaluate((e, props) => {
    const c = getComputedStyle(e);
    const o = {};
    for (const k of props) o[k] = c.getPropertyValue(k);
    o["background-image"] = c.getPropertyValue("background-image") === "none" ? "none" : "(image)";
    o._focused = document.activeElement === e;
    return o;
  }, PROPS);
}

(async () => {
  const mode = process.argv[2];
  if (mode !== "before" && mode !== "after") { console.error("usage: node aw2b-visual.cjs before|after"); process.exit(2); }
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch({ executablePath: exe });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  const warns = [];
  page.on("console", (m) => warns.push(`${m.type()}: ${m.text()}`));
  page.on("pageerror", (e) => warns.push(`pageerror ${e}`));
  const out = { held: {}, groups: {} };
  for (const [name, { html, states }] of Object.entries(HELD)) {
    out.held[name] = {};
    for (const st of states) out.held[name][st] = await measure(page, html, st);
  }
  for (const [name, [wrapFn, bHtml, aHtml]] of Object.entries(GROUPS)) {
    out.groups[name] = {};
    const sel = (mode === "before" ? bHtml : aHtml) + OPTS + "</select>";
    for (const st of ["normal", "focus"]) out.groups[name][st] = await measure(page, wrapFn(sel), st);
  }
  const ver = b.version();
  await b.close();

  const jsonPath = path.join(__dirname, "aw2b-visual.json");
  const saved = fs.existsSync(jsonPath) ? JSON.parse(fs.readFileSync(jsonPath, "utf8")) : {};
  saved.chromium = ver; saved.cssOrder = order; saved.viewport = "1280x800 light";
  saved[mode] = out; saved[`${mode}Warnings`] = warns;
  fs.writeFileSync(jsonPath, JSON.stringify(saved, null, 1) + "\n");
  console.log(`${mode}: chromium ${ver}, held ${Object.keys(out.held).length}, groups ${Object.keys(out.groups).length}, warnings ${warns.length}`);

  if (mode === "after") {
    const diffOf = (x, y) => PROPS.filter((k) => x[k] !== y[k]).map((k) => ({ prop: k, before: x[k], after: y[k] }));
    const heldDiffs = [];
    for (const [name, sts] of Object.entries(saved.before.held))
      for (const [st, v] of Object.entries(sts)) { const d = diffOf(v, saved.after.held[name][st]); if (d.length) heldDiffs.push({ name, st, diffs: d }); }
    let md = `# AW-2b 外観実測（Chromium ${ver}、幅1280・light）\n\nCSS 読込順: ${order.join(" → ")}\n\nconsole 警告: ${[...(saved.beforeWarnings || []), ...warns].length ? [...(saved.beforeWarnings || []), ...warns].join("; ") : "なし"}\n\n`;
    md += `## (A)(B) 保留10件の変更前後（通常・focus）\n\n差分: ${heldDiffs.length ? JSON.stringify(heldDiffs, null, 1) : "0件"}\n\n`;
    md += `## (C) 代表グループの前後表（差のある項目のみ。normal / focus）\n\n`;
    for (const name of Object.keys(saved.before.groups)) {
      md += `### ${name}\n\n`;
      for (const st of ["normal", "focus"]) {
        const d = diffOf(saved.before.groups[name][st], saved.after.groups[name][st]);
        md += `${st}: ${d.length ? "" : "差分0\n\n"}`;
        if (d.length) { md += "\n\n| 項目 | 変更前 | 変更後 |\n|---|---|---|\n"; for (const r of d) md += `| ${r.prop} | ${String(r.before).slice(0, 60)} | ${String(r.after).slice(0, 60)} |\n`; md += "\n"; }
      }
    }
    fs.writeFileSync(path.join(__dirname, "aw2b-visual.md"), md);
    console.log(`held diffs: ${heldDiffs.length}`);
    process.exit(heldDiffs.length === 0 ? 0 : 1);
  }
})();
