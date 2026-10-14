const L = require("./lib.cjs"); const fs = require("fs");
const PORT = process.env.PORT || "4182"; const BASE = "http://localhost:" + PORT;
const TAG = process.env.TAG || "before"; const OUT = "/tmp/CC報告ファイル/ssot-ay2t/impl/";
const ADVICE = { inputs: { monthly_kgi: 1000000, kgi_type: "revenue", period: "90d", scope: "mine" }, rates_used: { unit_price: 50000, win_rate: 0.2, deal_rate: 0.5 }, monthly_required: { wins: 20, deals: 40, leads: 200 }, weekly_required: { wins: 5, deals: 10, leads: 50 }, working_days: { remaining_month: 15, remaining_week: 4, shift_status: "submitted" }, data_sufficient: true };
const PROPS = ["background-color","font-size","line-height","height","min-height","width","border-radius","border-top-color","border-top-width","padding","box-shadow","color","font-family","transition-duration"];
const measure = ([SEL, IDX, PROPS]) => {
  const els = document.querySelectorAll(SEL); const el = els[IDX]; if (!el) return { found: false, count: els.length };
  const cs = getComputedStyle(el); const s = {}; for (const p of PROPS) s[p] = cs.getPropertyValue(p);
  const r = el.getBoundingClientRect();
  return { found: true, count: els.length, className: String(el.className), id: el.id || null, testid: el.getAttribute("data-testid"), ariaLabel: el.getAttribute("aria-label"), type: el.getAttribute("type"), min: el.getAttribute("min"), step: el.getAttribute("step"), placeholder: el.getAttribute("placeholder"), classList: [...el.classList], computed: s, rect: { left: +r.left.toFixed(2), top: +r.top.toFixed(2), width: +r.width.toFixed(2), height: +r.height.toFixed(2) } };
};
const TARGETS = [
  { name: "row0", sel: ".gs-row input", idx: 0 },
  { name: "monthly-kgi", sel: '[data-testid="goal-advisor-monthly-kgi"]', idx: 0 },
  { name: "weekly-leads", sel: '[data-testid="goal-advisor-weekly-leads"] input', idx: 0 },
  { name: "weekly-deals", sel: '[data-testid="goal-advisor-weekly-deals"] input', idx: 0 },
  { name: "weekly-wins", sel: '[data-testid="goal-advisor-weekly-wins"] input', idx: 0 },
];
async function both(page, t) {
  const o = {};
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  o.normal = await page.evaluate(measure, [t.sel, t.idx, PROPS]);
  if (o.normal.found) { await page.locator(t.sel).nth(t.idx).focus(); await page.waitForTimeout(250); o.focus = (await page.evaluate(measure, [t.sel, t.idx, PROPS])).computed; await page.evaluate(() => document.activeElement.blur()); await page.waitForTimeout(250); }
  return o;
}
(async () => {
  const browser = await L.chromium.launch({ executablePath: L.EXE }); const result = {};
  const SCEN = [[1280, false], [1440, false], [375, false], [1280, true]];
  for (const [w, dark] of SCEN) {
    const key = "goals-w" + w + (dark ? "-dark" : ""); const res = { consoleErrors: [], calls: [], posts: [], items: {}, saved: {} }; result[key] = res;
    const ctx = await browser.newContext({ viewport: { width: w, height: 1400 }, deviceScaleFactor: 2 });
    const page = await L.setup(ctx, res, (k, u, json) => {
      if (k === "POST /goals") { return json({}); }
      if (k === "GET /analytics/new-goal-advice") return json(ADVICE);
      return undefined;
    });
    // POST body capture
    page.on("request", rq => { if (rq.method() === "POST" && rq.url().includes("/goals")) res.postBodies = (res.postBodies || []).concat([rq.postData()]); });
    const err = await L.goto(page, BASE + "/goals/settings", '[data-testid="goal-advisor-monthly-kgi"]', res);
    if (err) { res.stoppedAt = err; await ctx.close(); continue; }
    if (dark) { await page.evaluate(() => { const f = () => { if (!document.documentElement.classList.contains("force-dark")) document.documentElement.classList.add("force-dark"); }; f(); new MutationObserver(f).observe(document.documentElement, { attributes: true, attributeFilter: ["class"] }); }); await page.waitForTimeout(1500); }
    await page.waitForSelector(".gs-row input", { timeout: 15000 }).catch(e => res.consoleErrors.push("no rows"));
    res.rowCount = await page.locator(".gs-row input").count();
    res.htmlClass = await page.evaluate(() => document.documentElement.className);
    res.items["row0"] = await both(page, TARGETS[0]);
    res.items["monthly-kgi"] = await both(page, TARGETS[1]);
    // advice
    await page.getByTestId("goal-advisor-monthly-kgi").fill("1000000");
    await page.getByTestId("goal-advisor-generate").click();
    await page.waitForSelector('[data-testid="goal-advisor-weekly-leads"] input', { timeout: 10000 }).catch(e => res.consoleErrors.push("no weekly"));
    await page.waitForTimeout(500);
    res.weeklyValues = await page.evaluate(() => ["leads","deals","wins"].map(k => { const i = document.querySelector(`[data-testid="goal-advisor-weekly-${k}"] input`); return i ? i.value : null; }));
    for (const t of TARGETS.slice(2)) res.items[t.name] = await both(page, t);
    res.items.weeklyGridAll = await page.evaluate(() => [...document.querySelectorAll(".gs-advisor__metric input")].map(i => i.className));
    res.allInputsClass = await page.evaluate(() => [...document.querySelectorAll(".gs-row input, .gs-advisor input")].map(i => i.className));
    res.doc = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
    await page.screenshot({ path: OUT + `${TAG}/${key}-full.png`, fullPage: true });
    // saved
    const inp = page.locator(".gs-row input").nth(0);
    await inp.fill("3000000");
    const blk = page.locator(".gs-block").filter({ has: inp }).first();
    await blk.locator(".gs-save-btn").click();
    await page.waitForSelector(".gs-saved-mark", { timeout: 10000 }).catch(e => res.consoleErrors.push("no saved mark"));
    await page.waitForTimeout(500);
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    res.saved.normal = await page.evaluate(measure, [".gs-row input", 0, PROPS]);
    res.saved.mark = await page.evaluate(() => { const i = document.querySelector(".gs-row input"); const m = i.parentElement.querySelector(".gs-saved-mark"); if (!m) return null; const a = i.getBoundingClientRect(), b = m.getBoundingClientRect(); const R = r => ({ left: +r.left.toFixed(2), top: +r.top.toFixed(2), width: +r.width.toFixed(2), height: +r.height.toFixed(2) }); return { input: R(a), mark: R(b), centerYDiff: +((b.top + b.height / 2) - (a.top + a.height / 2)).toFixed(2), insideInput: b.left >= a.left && b.right <= a.right && b.top >= a.top && b.bottom <= a.bottom }; });
    await inp.focus(); await page.waitForTimeout(250);
    res.saved.focus = (await page.evaluate(measure, [".gs-row input", 0, PROPS])).computed;
    await page.screenshot({ path: OUT + `${TAG}/${key}-saved-focus.png`, clip: await clipOf(inp, w) }).catch(() => {});
    await page.evaluate(() => document.activeElement.blur()); await page.waitForTimeout(250);
    await page.screenshot({ path: OUT + `${TAG}/${key}-saved.png`, clip: await clipOf(inp, w) }).catch(() => {});
    res.savedCount = await page.locator(".gs-saved-mark").count();
    // unsaved row1 for contrast screenshot
    await page.locator(".gs-row input").nth(1).scrollIntoViewIfNeeded().catch(()=>{});
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT + TAG + ".json", JSON.stringify(result, null, 1)); console.log("written");
})().catch(e => { console.error(e); process.exit(1); });
async function clipOf(loc, w) { const b = await loc.boundingBox(); return { x: Math.max(0, b.x - 120), y: Math.max(0, b.y - 24), width: Math.min(b.width + 140, w - Math.max(0, b.x - 120)), height: b.height + 48 }; }
function route_body() { return null; }
