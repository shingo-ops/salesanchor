import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
const permissions = { permissions: ["dashboard.view"], is_super_admin: true };
const csv = "mark,japanese_title,english_title,release_date,search_keywords,exclude_keywords,division_code,work_code,manufacturer_code,product_category_code\nA,Fixture,Fixture,2026-01-01,Fixture,,DIV01,IP001,MK001,PC_BOX\n";
test("list to confirmation and registration: no commit before explicit confirmation", async ({ page }) => {
  await installAuthBypass(page);
  let commits = 0;
  await mockApi(page, {
    "GET /me/permissions": permissions,
    "GET /staff/me": { id: 1, ui_preferences: { show_sidebar: true } },
    "GET /tcg/products/list": { total: 1, items: [{ code: "PM01", japanese_title: "Fixture", mark: "A", release_date: "2026-01-01", keyword_count: 0 }] },
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
