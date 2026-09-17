import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";

const classification = { division_id: null, work_id: null, manufacturer_id: null, product_category_id: null };
const product = {
  ...classification, id: "00000000-0000-4000-8000-000000000001", code: "PM01",
  japanese_title: "日本語の商品", english_title: "English product name", mark: "MODEL-01",
  release_date: "2026-09-13", search_keywords: ["Alpha", "Beta", "Gamma"], exclude_keywords: [],
  required_output_value: "Product", category_class: "Pokemon", is_active: true, created_at: "2026-09-13T00:00:00+00:00",
};
async function setup(page: Page, locale = "ja", failure = 0, loadFailure = false) {
  await installAuthBypass(page);
  await page.addInitScript(lang => { document.cookie = `locale=${lang};path=/`; }, locale);
  let current = structuredClone(product);
  let saves = 0; let reads = 0;
  const lookups = Object.fromEntries(Object.keys(classification).map(field => [field, []]));
  const response = () => ({ revision: (saves ? "b" : "a").repeat(64), product: current, lookups });
  await mockApi(page, {
    "GET /me/permissions": { permissions: ["dashboard.view"], is_super_admin: true },
    "GET /staff/me": { id: 1, locale, ui_preferences: { show_sidebar: false } },
    "GET /tcg/products/list": async route => {
      const value = { works: [], total: 1, items: [{ ...current, keyword_count: current.search_keywords.length, exclude_keyword_count: current.exclude_keywords.length }] };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(value) });
    },
    "GET /tcg/products/detail/PM01": async route => {
      reads++;
      await route.fulfill({ status: loadFailure && reads === 1 ? 404 : 200, contentType: "application/json", body: JSON.stringify(response()) });
    },
    "PUT /tcg/products/detail/PM01": async route => {
      saves++;
      const body = route.request().postDataJSON();
      expect(Object.keys(body).sort()).toEqual([...Object.keys(classification), "revision", "japanese_title", "english_title", "mark", "release_date", "search_keywords", "exclude_keywords"].sort());
      expect(body.revision).toBe("a".repeat(64));
      if (failure) {
        await route.fulfill({ status: failure, contentType: "application/json", body: JSON.stringify({ detail: "TEST_ERROR" }) }); return;
      }
      current = { ...current, ...body };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(response()) });
    },
  });
  await page.goto("/super-admin/tcg-product-master");
  await expect(page.getByRole("cell", { name: "MODEL-01", exact: true })).toBeVisible();
  return { saves: () => saves, reads: () => reads };
}

for (const locale of ["ja", "en"]) {
  for (const width of [1280, 390]) {
    test(`D1-D4 bilingual list, row editing and saved values ${locale} ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      const calls = await setup(page, locale);
      await expect(page.getByRole("columnheader")).toHaveText(locale === "ja"
        ? ["型番", "商品名", "発売日", "検索", "除外"] : ["Mark", "Product name", "Release date", "Search", "Exclude"]);
      const row = page.getByRole("row").filter({ hasText: "MODEL-01" });
      await expect(row.getByRole("cell")).toHaveCount(5);
      await expect(row).not.toContainText("PM01");
      await expect(row.getByRole("cell").nth(3)).toHaveText("3");
      await expect(row.getByRole("cell").nth(4)).toHaveText("0");
      const name = row.locator(".product-detail__name");
      const sizes = await name.evaluate(el => {
        const [ja, en] = Array.from(el.children);
        return { ja: parseFloat(getComputedStyle(ja).fontSize), en: parseFloat(getComputedStyle(en).fontSize), below: en.getBoundingClientRect().top >= ja.getBoundingClientRect().bottom };
      });
      expect(sizes.en).toBeLessThan(sizes.ja); expect(sizes.below).toBe(true);
      mkdirSync("/tmp/reports/product-detail", { recursive: true });
      await page.screenshot({ path: `/tmp/reports/product-detail/list-${locale}-${width}.png`, fullPage: true });
      await row.focus(); await page.keyboard.press("Enter");
      const dialog = page.getByRole("dialog", { name: /商品詳細|Product details/ });
      await expect(dialog.getByRole("textbox", { name: locale === "ja" ? "日本語名" : "Japanese name", exact: true })).toHaveValue(product.japanese_title);
      await expect(dialog.getByLabel(locale === "ja" ? "商品コード" : "Product code", { exact: true })).toHaveAttribute("readonly", "");
      await dialog.getByLabel(locale === "ja" ? "英語名" : "English name", { exact: true }).fill("Edited English");
      await dialog.getByLabel(locale === "ja" ? "検索キーワード" : "Search keywords", { exact: true }).fill("Changed\nSecond");
      await dialog.getByLabel(locale === "ja" ? "除外キーワード" : "Exclusion keywords", { exact: true }).fill("Excluded");
      await page.screenshot({ path: `/tmp/reports/product-detail/editor-${locale}-${width}.png`, fullPage: true });
      await dialog.locator("form").evaluate(form => { (form as HTMLFormElement).requestSubmit(); (form as HTMLFormElement).requestSubmit(); });
      await expect(dialog.getByRole("status")).toHaveText(locale === "ja" ? "保存しました。" : "Saved.");
      expect(calls.saves()).toBe(1);
      await expect(row).toContainText("Edited English");
      await expect(row.getByRole("cell").nth(3)).toHaveText("2");
      await expect(row.getByRole("cell").nth(4)).toHaveText("1");
      await dialog.getByTestId("drawer-close").click();
      await row.click();
      await expect(dialog.getByLabel(locale === "ja" ? "英語名" : "English name", { exact: true })).toHaveValue("Edited English");
      expect(calls.reads()).toBe(2);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    });
  }
}

for (const close of ["button", "escape", "overlay"]) {
  test(`D5 dirty confirmation preserves draft and discards explicitly: ${close}`, async ({ page }) => {
    const calls = await setup(page);
    const row = page.getByRole("row").filter({ hasText: "MODEL-01" });
    await row.focus(); await page.keyboard.press("Space");
    const dialog = page.getByRole("dialog", { name: "商品詳細・編集" });
    await dialog.getByRole("textbox", { name: "日本語名", exact: true }).fill("未保存の商品名");
    const closeIt = async () => {
      if (close === "button") await dialog.getByTestId("drawer-close").click();
      else if (close === "escape") await page.keyboard.press("Escape");
      else await page.locator(".comp-drawer-overlay").click({ position: { x: 10, y: 100 } });
    };
    await closeIt();
    await expect(dialog.getByRole("alert")).toContainText("未保存");
    await dialog.getByRole("button", { name: "編集に戻る" }).click();
    await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue("未保存の商品名");
    await closeIt();
    await dialog.getByRole("button", { name: "変更を破棄", exact: true }).click();
    await row.click();
    await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue(product.japanese_title);
    expect(calls.saves()).toBe(0);
  });
}

for (const failure of [409, 422, 500]) {
  test(`D6 server error ${failure} retains inputs with no automatic retry`, async ({ page }) => {
    const calls = await setup(page, "ja", failure);
    await page.getByRole("cell", { name: "MODEL-01", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "商品詳細・編集" });
    await dialog.getByRole("textbox", { name: "日本語名", exact: true }).fill("保持する入力");
    await dialog.getByRole("button", { name: "保存", exact: true }).click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue("保持する入力");
    expect(calls.saves()).toBe(1);
    if (failure !== 422) {
      await expect(dialog.getByRole("button", { name: "保存", exact: true })).toBeDisabled();
      await dialog.getByRole("button", { name: "最新の内容を読み直す" }).click();
      await dialog.getByRole("button", { name: "編集に戻る" }).click();
      await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue("保持する入力");
    }
  });
}

test("detail load failure offers reload and cannot save an empty form", async ({ page }) => {
  const calls = await setup(page, "ja", 0, true);
  await page.getByRole("cell", { name: "MODEL-01", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "商品詳細・編集" });
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "保存", exact: true })).toHaveCount(0);
  await dialog.getByRole("button", { name: "最新の内容を読み直す" }).click();
  await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue(product.japanese_title);
  expect(calls.saves()).toBe(0);
});
