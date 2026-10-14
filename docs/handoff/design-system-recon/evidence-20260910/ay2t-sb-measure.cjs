const L = require("./lib.cjs"); const fs = require("fs");
(async () => {
  const browser = await L.chromium.launch({ executablePath: L.EXE }); const out = {};
  for (const dark of [false, true]) {
    const ctx = await browser.newContext({ viewport: { width: 800, height: 600 }, deviceScaleFactor: 2 }); const page = await ctx.newPage();
    await page.goto("http://localhost:6007/iframe.html?id=pages-goalsetting--saved-input-state&viewMode=story", { waitUntil: "networkidle" });
    await page.waitForSelector("input.comp-field__input");
    if (dark) { await page.evaluate(() => document.documentElement.classList.add("force-dark")); await page.waitForTimeout(1500); }
    const m = () => page.evaluate(() => { const c = getComputedStyle(document.querySelector("input")); return { cls: document.querySelector("input").className, border: c.borderTopColor, bg: c.backgroundColor, shadow: c.boxShadow }; });
    const r = { normal: await m() }; await page.locator("input").focus(); await page.waitForTimeout(300); r.focus = await m();
    await page.screenshot({ path: `sb-saved-focus${dark ? "-dark" : ""}.png` });
    out[dark ? "dark" : "light"] = r; await ctx.close();
  }
  await browser.close(); fs.writeFileSync("storybook-saved.json", JSON.stringify(out, null, 1)); console.log(JSON.stringify(out));
})();
