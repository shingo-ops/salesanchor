// AY-3b 実測スクリプト（設計 §5）。
// 使い方: node ay3b-measure.cjs <before|after> <css> <outJson> <shotDir>
//   before: 旧 DOM（JSX の字面どおり手書き）。after: Toggle を renderToStaticMarkup した HTML。
// 条件: 390/1280px × light/dark × 場所 4 ページ（8 トグル）× OFF/ON/focus-visible(Tab)。
const path = require("path"), fs = require("fs"), cp = require("child_process"), os = require("os");
const FRONT = path.resolve(__dirname, "../../../../frontend");
const { chromium } = require(path.join(FRONT, "node_modules/playwright"));
const [, , MODE, CSS, OUT, SHOTS] = process.argv;
const css = fs.readFileSync(CSS, "utf8").replace(/@import[^;]+;/g, "");

let AFTER = null;
if (MODE === "after") {
  const esbuild = require(path.join(FRONT, "node_modules/esbuild"));
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ay3b-"));
  const outfile = path.join(tmp, "render.cjs");
  esbuild.buildSync({ entryPoints: [path.join(__dirname, "ay3b-render-toggle.tsx")], bundle: true, platform: "node", format: "cjs", outfile, jsx: "automatic", loader: { ".css": "empty" }, nodePaths: [path.join(FRONT, "node_modules")], absWorkingDir: FRONT });
  AFTER = JSON.parse(cp.execFileSync("node", [outfile], { encoding: "utf8" }));
}

// 旧 DOM（JSX 原文どおり）
const OLD = {
  "inbox-1": (on) => `<label class="toggle-switch"><input type="checkbox" ${on ? "checked" : ""}><span class="toggle-switch-slider"></span></label>`,
  pref: (on) => `<label class="toggle-switch"><input id="dark-mode-toggle" type="checkbox" ${on ? "checked" : ""}><span class="toggle-slider" aria-hidden="true"></span></label>`,
  allday: (on) => `<label class="toggle-switch"><input type="checkbox" ${on ? "checked" : ""}><span class="toggle-switch-slider"></span></label>`,
  "sched-self": (on) => `<label class="toggle-switch" aria-label="Visible"><input type="checkbox" ${on ? "checked" : ""}><span class="toggle-switch-slider"></span></label>`,
};
OLD["inbox-2"] = OLD["inbox-3"] = OLD["inbox-4"] = OLD["inbox-1"];
OLD["sched-other"] = OLD["sched-self"];
const T = (k, on) => (MODE === "after" ? AFTER[k][on ? "on" : "off"] : OLD[k](on));

const PAGES = {
  modal: { keys: ["inbox-1", "inbox-2", "inbox-3", "inbox-4"], rowSel: ".inbox-settings-row", build: (t) => `
<div class="comp-modal-overlay"><div class="comp-modal-dialog comp-modal-dialog--sm" role="dialog"><div class="comp-modal-header"><h2 class="comp-modal-title">Inbox settings</h2></div><div class="comp-modal-body">
<div class="inbox-settings-section-title">Display</div>
<div class="inbox-settings-row"><span class="inbox-settings-label">Show right panel</span>${t(0)}</div>
<div class="inbox-settings-row"><span class="inbox-settings-label">Default tab</span><select><option>All</option></select></div>
<div class="inbox-settings-row"><span class="inbox-settings-label">Default unread only</span>${t(1)}</div>
<div class="inbox-settings-section-title" style="margin-top:var(--space-4)">Notifications</div>
<div class="inbox-settings-row"><span class="inbox-settings-label">Browser notifications</span>${t(2)}</div>
<div class="inbox-settings-row"><span class="inbox-settings-label">Sound</span>${t(3)}</div>
</div></div></div>` },
  pref: { keys: ["pref"], rowSel: ".account-settings-pref-row", build: (t) => `
<div class="account-settings-page"><section class="account-settings-section"><div class="account-settings-section-title">Preferences</div>
<div class="account-settings-pref-row"><label for="dark-mode-toggle" class="account-settings-pref-label">Dark mode</label>${t(0)}</div>
<div class="account-settings-pref-row"><label for="language-select" class="account-settings-pref-label">Language</label><select id="language-select"><option>English</option></select></div>
</section></div>` },
  allday: { keys: ["allday"], rowSel: ".schedule-field--inline", build: (t) => `
<div class="schedule-page"><div class="schedule-popover-backdrop"></div><div class="schedule-popover" style="top:60px;left:100px"><div class="schedule-popover__body schedule-popover__body--form">
<label class="schedule-field"><span class="schedule-field__label">Title</span><input type="text"></label>
<div class="schedule-field schedule-field--inline"><span class="schedule-field__label">All day</span>${t(0)}</div>
</div></div></div>` },
  settings: { keys: ["sched-self", "sched-other"], rowSel: ".schedule-settings__calendar-row", build: (t) => {
    const row = (i) => `<div class="schedule-settings__calendar-row"><div class="schedule-settings__row-copy"><span>Owner ${i}</span><span class="schedule-settings__description">Show this calendar</span></div><div class="schedule-settings__calendar-actions"><input type="color" value="#336699">${t(i)}<select><option>Self</option></select><button type="button">Save</button></div></div>`;
    return `<div class="schedule-settings"><div class="schedule-settings__shell"><nav class="schedule-settings__nav"><button type="button" class="schedule-settings__nav-item">My calendars</button></nav><div class="schedule-settings__content"><section class="schedule-settings__card"><div class="schedule-settings__card-title">My calendars</div><div class="schedule-settings__card-body">${row(0)}${row(1)}</div></section></div></div></div>`; } },
};

const measure = () => {
  const num = (s) => parseFloat(s);
  const out = { toggles: [], rows: [] };
  for (const lab of document.querySelectorAll("label")) {
    if (!lab.querySelector("input[type=checkbox]")) continue;
    const inp = lab.querySelector("input"), tr = lab.querySelector("span");
    const cl = getComputedStyle(lab), cs = getComputedStyle(tr), bef = getComputedStyle(tr, "::before"), ci = getComputedStyle(inp);
    const lr = lab.getBoundingClientRect(), sr = tr.getBoundingClientRect();
    const m = bef.transform === "none" ? 0 : new DOMMatrix(bef.transform).m41;
    const forLab = inp.id ? document.querySelector(`label[for="${inp.id}"]`) : null;
    out.toggles.push({
      trackW: sr.width, trackH: sr.height, labelW: lr.width, labelH: lr.height,
      knobW: num(bef.width), knobH: num(bef.height), knobTop: num(bef.top),
      knobMove: m, knobLeftEdge: sr.left + num(bef.left) + m - sr.left, knobRightGap: sr.width - (num(bef.left) + m + num(bef.width)),
      trackBg: cs.backgroundColor, knobBg: bef.backgroundColor, knobShadow: bef.boxShadow, radius: cs.borderTopLeftRadius,
      trackTransition: cs.transitionProperty + " " + cs.transitionDuration, knobTransition: bef.transitionProperty + " " + bef.transitionDuration,
      trackShadow: cs.boxShadow, display: cl.display, flexShrink: cl.flexShrink, inputOpacity: ci.opacity, inputW: ci.width, inputPos: ci.position,
      role: inp.getAttribute("role") || "checkbox(implicit)",
      name: inp.getAttribute("aria-label") ? "input aria-label=" + inp.getAttribute("aria-label")
        : lab.getAttribute("aria-label") ? "label aria-label=" + lab.getAttribute("aria-label")
        : forLab ? "label[for] text=" + forLab.textContent.trim() : "(none)",
    });
  }
  return out;
};
const rowMeasure = (sel) => [...document.querySelectorAll(sel)].map((r) => {
  const a = r.querySelector(".schedule-settings__calendar-actions");
  return { h: r.getBoundingClientRect().height, w: r.getBoundingClientRect().width, scrollW: r.scrollWidth, clientW: r.clientWidth, actionsW: a ? a.getBoundingClientRect().width : null, actionsScrollW: a ? a.scrollWidth : null, actionsClientW: a ? a.clientWidth : null };
});

(async () => {
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b = await chromium.launch(fs.existsSync(exe) ? { executablePath: exe } : {});
  const res = { mode: MODE, css: CSS, chromium: b.version(), results: {} };
  fs.mkdirSync(SHOTS, { recursive: true });
  for (const vw of [390, 1280]) for (const theme of ["light", "dark"]) {
    const page = await (await b.newContext({ viewport: { width: vw, height: 800 } })).newPage();
    for (const [pn, P] of Object.entries(PAGES)) {
      const load = async (states) => {
        const body = P.build((i) => T(P.keys[i], states[i]));
        await page.setContent(`<!doctype html><html class="${theme === "dark" ? "force-dark" : ""}"><head><meta name="viewport" content="width=device-width"><style>${css}</style></head><body>${body}</body></html>`, { waitUntil: "load" });
        await page.waitForTimeout(150);
      };
      const key = `${vw}/${theme}/${pn}`;
      const r = {};
      await load(P.keys.map(() => false)); r.off = await page.evaluate(measure); r.off.rows = await page.evaluate(rowMeasure, P.rowSel);
      await load(P.keys.map(() => true)); r.on = await page.evaluate(measure); r.on.rows = await page.evaluate(rowMeasure, P.rowSel);
      // focus-visible: Tab で各トグルへ
      await load(P.keys.map(() => false)); r.focus = [];
      for (let n = 0; n < P.keys.length; n++) {
        await page.evaluate(() => document.activeElement && document.activeElement.blur());
        let hit = false;
        for (let i = 0; i < 30 && !hit; i++) {
          await page.keyboard.press("Tab");
          hit = await page.evaluate((n) => { const inp = [...document.querySelectorAll("label")].filter((l) => l.querySelector("input[type=checkbox]")).map((l) => l.querySelector("input"))[n]; return document.activeElement === inp; }, n);
        }
        r.focus.push(hit ? await page.evaluate((n) => { const l = [...document.querySelectorAll("label")].filter((l) => l.querySelector("input[type=checkbox]"))[n]; const tr = l.querySelector("span"); return { tabbed: true, trackShadow: getComputedStyle(tr).boxShadow }; }, n) : { tabbed: false });
      }
      if (vw === 1280) { // 見た目: 奇数番目だけ ON
        await load(P.keys.map((_, i) => i % 2 === 1 || P.keys.length === 1));
        await page.screenshot({ path: path.join(SHOTS, `${MODE}-${theme}-${pn}.png`) });
      }
      res.results[key] = r;
    }
    await page.context().close();
  }
  fs.writeFileSync(OUT, JSON.stringify(res, null, 1));
  await b.close();
})();
