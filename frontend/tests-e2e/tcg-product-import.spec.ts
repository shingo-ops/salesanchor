import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
const permissions = { permissions: ["dashboard.view"], is_super_admin: true };
const works = [
  { id: "00000000-0000-4000-8000-000000000001", code: "IP001", display_name: "Pokemon", alt_name: " ポケモン " },
  { id: "00000000-0000-4000-8000-000000000002", code: "IP002", display_name: "One Piece", alt_name: "ワンピース" },
  { id: "00000000-0000-4000-8000-000000000003", code: "IP003", display_name: "Fallback Work", alt_name: " " },
];
const csv = "mark,japanese_title,english_title,release_date,search_keywords,exclude_keywords,division_code,work_code,manufacturer_code,product_category_code\nA,Fixture,Fixture,2026-01-01,Fixture,,DIV01,IP001,MK001,PC_BOX\n";
test("list to confirmation and registration: no commit before explicit confirmation", async ({ page }) => {
  await installAuthBypass(page);
  let commits = 0;
  await mockApi(page, {
    "GET /me/permissions": permissions,
    "GET /staff/me": { id: 1, ui_preferences: { show_sidebar: true } },
    "GET /tcg/products/list": { works, total: 1, items: [{ code: "PM01", japanese_title: "Fixture", mark: "A", release_date: "2026-01-01", keyword_count: 0 }] },
    "POST /tcg/products/import/preview": { filename: "products.csv", digest: "a".repeat(64), file_errors: [], total: 1, ok: 1, blocked: 0, rows: [{ row_no: "2", japanese_title: "Fixture", mark: "A", blocking: [], warnings: ["NO_SEARCH_KEYWORD"] }] },
    "POST /tcg/products/import/commit": async route => { commits++; expect(route.request().postData()).toContain("a".repeat(64)); await route.fulfill({ contentType: "application/json", body: JSON.stringify({ job_id: "receipt", total: 1, created: 1, skipped: 0 }) }); },
  });
  await page.goto("/super-admin/tcg-product-master");
  await expect(page.getByText("Fixture", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /CSV/ }).click();
  await expect(page).toHaveURL(/tcg-product-master\/import$/);
  await page.locator('input[type="file"]').setInputFiles({ name: "products.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
  await page.getByRole("button", { name: /内容を確認|Review contents/ }).click();
  await expect(page.getByText(/検索キーワードがありません|No search keywords are specified/)).toBeVisible();
  expect(commits).toBe(0);
  await page.getByRole("button", { name: /警告を確認して登録|Confirm warnings and import/ }).click();
  await expect(page.getByRole("status")).toContainText(/登録1件|Registered: 1/);
  expect(commits).toBe(1);
  await page.screenshot({ path: "/tmp/reports/product-csv-result.png", fullPage: true });
});

for (const locale of ["ja", "en"]) {
  test(`AC8 work tabs use ${locale} names, scroll and support keyboard selection`, async ({ page }) => {
    await installAuthBypass(page);
    await page.addInitScript(lang => { document.cookie = `locale=${lang};path=/`; }, locale);
    await page.setViewportSize({ width: 390, height: 844 });
    const requests: URL[] = [];
    const candidates = [...works, ...Array.from({ length: 10 }, (_, index) => ({
      id: `00000000-0000-4000-8000-${String(index + 4).padStart(12, "0")}`,
      code: `IP${index + 4}`, display_name: `Extra work ${index + 4}`, alt_name: "",
    }))];
    await mockApi(page, {
      "GET /me/permissions": permissions,
      "GET /staff/me": { id: 1, locale, ui_preferences: { show_sidebar: false } },
      "GET /tcg/products/list": async route => {
        const url = new URL(route.request().url()); requests.push(url);
        const chosen = url.searchParams.get("work_id");
        const names = chosen ? [chosen === works[0].id ? "Pokemon fixture" : "One Piece fixture"] : ["Pokemon fixture", "One Piece fixture"];
        await route.fulfill({ contentType: "application/json", body: JSON.stringify({
          works: candidates, total: names.length,
          items: names.map((name, index) => ({ code: `P${index}`, japanese_title: name, mark: "", release_date: "2026-01-01", keyword_count: 1 })),
        }) });
      },
    });
    await page.goto("/super-admin/tcg-product-master");
    const all = page.getByRole("tab", { name: locale === "ja" ? "すべて" : "All", exact: true });
    const pokemon = page.getByRole("tab", { name: locale === "ja" ? "ポケモン" : "Pokemon", exact: true });
    const onePiece = page.getByRole("tab", { name: locale === "ja" ? "ワンピース" : "One Piece", exact: true });
    await expect(all).toHaveAttribute("aria-selected", "true");
    await expect(pokemon).toBeVisible();
    await expect(page.getByRole("tab", { name: "Fallback Work", exact: true })).toBeAttached();
    await pokemon.click();
    await expect(page.getByText("Pokemon fixture", { exact: true })).toBeVisible();
    await expect(page.getByText("One Piece fixture", { exact: true })).toHaveCount(0);
    expect(requests[requests.length - 1].searchParams.get("work_id")).toBe(works[0].id);
    await pokemon.focus();
    await page.keyboard.press("Tab");
    await expect(onePiece).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(onePiece).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText("One Piece fixture", { exact: true })).toBeVisible();
    await expect(page.getByText("Pokemon fixture", { exact: true })).toHaveCount(0);
    expect(requests[requests.length - 1].searchParams.get("work_id")).toBe(works[1].id);
    const list = page.getByRole("tablist");
    expect(await list.evaluate(element => element.scrollWidth > element.clientWidth)).toBe(true);
    await page.getByRole("tab", { name: "Extra work 13", exact: true }).scrollIntoViewIfNeeded();
    expect(await list.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
    await all.click();
    await expect(page.getByText("Pokemon fixture", { exact: true })).toBeVisible();
    await expect(page.getByText("One Piece fixture", { exact: true })).toBeVisible();
    expect(requests[requests.length - 1].searchParams.has("work_id")).toBe(false);
    await page.screenshot({ path: `/tmp/reports/product-tabs-${locale}.png`, fullPage: true });
    await page.getByRole("button", { name: /CSV/ }).click();
    await expect(page).toHaveURL(/tcg-product-master\/import$/);
  });
}

test("AC8 non-admin cannot request product list or see tabs", async ({ page }) => {
  await installAuthBypass(page);
  let productRequests = 0;
  page.on("request", request => { if (request.url().includes("/api/v1/tcg/products")) productRequests++; });
  await mockApi(page, { "GET /me/permissions": { ...permissions, is_super_admin: false } });
  await page.goto("/super-admin/tcg-product-master");
  await expect(page.getByRole("alert")).toContainText(/SaaS/);
  await expect(page.getByRole("tablist")).toHaveCount(0);
  expect(productRequests).toBe(0);
});
test("non-admin cannot enter CSV import", async ({ page }) => {
  await installAuthBypass(page);
  let productRequests = 0;
  page.on("request", request => { if (request.url().includes("/api/v1/tcg/products")) productRequests++; });
  await mockApi(page, { "GET /me/permissions": { ...permissions, is_super_admin: false } });
  await page.goto("/super-admin/tcg-product-master/import");
  await expect(page.getByRole("alert")).toContainText(/SaaS/);
  expect(productRequests).toBe(0);
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
});
