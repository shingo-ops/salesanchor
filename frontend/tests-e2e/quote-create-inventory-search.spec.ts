/**
 * QuoteCreatePage の「検索して追加」検索バー UI smoke。
 *
 * ADR-093 (2026-06-03) で明細 UX を刷新:
 *   - 行内検索を廃止し、明細ゾーン下に単一の「検索して追加／新規追加」検索バーを配置
 *     (testIdPrefix="quote-add-search")。候補選択で明細行を「追加」する（上書きではない）。
 *   - 商品名は自由記入可。AND/OR トグルは検索バー内に存続。
 *
 * Note:
 *   - 本 spec は `/api/v1/inventory/search` を Playwright route で mock 化する。
 *   - 実 PG 横断 / ranking / pg_trgm の SLO 検証は backend/tests/test_inventory_search*.py で実施。
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const INVENTORY_RESPONSE = {
  query: "リザードン",
  op: "or",
  total: 2,
  masked: false,
  candidates: [
    {
      product_id: 101,
      name: "リザードン ex SAR (in-stock)",
      name_en: "Charizard ex SAR",
      product_code: "S7-LIZ-001",
      expansion_code: "SV1a",
      card_number: "SV1a-001",
      jan_code: null,
      unit_price: 1500,
      stock_quantity: 5,
      supplier_default_id: 1,
      supplier_name: "Sample Supplier",
      image_url: null,
      matched_via: "products_name",
      score: 13,
    },
    {
      product_id: 102,
      name: "リザードン ex SAR (zero stock)",
      name_en: "Charizard ex SAR (out)",
      product_code: "S7-LIZ-002",
      expansion_code: "SV1a",
      card_number: "SV1a-002",
      jan_code: null,
      unit_price: 1200,
      stock_quantity: 0,
      supplier_default_id: 1,
      supplier_name: "Sample Supplier",
      image_url: null,
      matched_via: "products_name",
      score: 1013,
    },
  ],
};

const EMPTY_RESPONSE = { query: "", op: "or", total: 0, masked: false, candidates: [] };

async function setupQuoteCreatePageMocks(page: import("@playwright/test").Page) {
  await installAuthBypass(page);
  await mockApi(page, {
    ...commonMocks(),
    "GET /products": [],
    "GET /companies": [],
    "GET /contacts": [],
    "GET /inventory/search": (route) => {
      const url = new URL(route.request().url());
      const q = url.searchParams.get("q") || "";
      if (!q.trim()) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(EMPTY_RESPONSE),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(INVENTORY_RESPONSE),
      });
    },
  });
}

test.describe("ADR-093 — QuoteCreatePage 検索して追加 UI smoke", () => {
  test("検索バーが描画され placeholder が i18n 経由", async ({ page }) => {
    await setupQuoteCreatePageMocks(page);
    await page.goto("/quotes/new");

    // 既定で「検索して追加」モード → 検索バーが表示される
    const input = page.getByTestId("quote-add-search-input");
    await expect(input).toBeVisible({ timeout: 20_000 });
    const placeholder = await input.getAttribute("placeholder");
    expect(placeholder).toBeTruthy();
    expect(placeholder!.length).toBeGreaterThan(0);
  });

  test("AND/OR トグルが UI 上でクリック可能", async ({ page }) => {
    await setupQuoteCreatePageMocks(page);
    await page.goto("/quotes/new");

    const input = page.getByTestId("quote-add-search-input");
    const orBtn = page.getByTestId("quote-add-search-op-or");
    const andBtn = page.getByTestId("quote-add-search-op-and");
    await expect(orBtn).toBeVisible({ timeout: 20_000 });
    await expect(andBtn).toBeVisible();
    await expect(orBtn).toHaveAttribute("aria-pressed", "true");

    // 1 単語では AND/OR は同義のため disable。2 単語以上で切替可能。
    await input.fill("リザードン ex");
    await andBtn.click();
    await expect(andBtn).toHaveAttribute("aria-pressed", "true");
    await expect(orBtn).toHaveAttribute("aria-pressed", "false");
  });

  test("候補選択 → 明細に行が追加され、在庫 0 行は警告が出る", async ({ page }) => {
    await setupQuoteCreatePageMocks(page);
    await page.goto("/quotes/new");

    const input = page.getByTestId("quote-add-search-input");
    await input.fill("リザードン");
    await page.waitForTimeout(400); // debounce 250ms

    const result0 = page.getByTestId("quote-add-search-result-0");
    await expect(result0).toBeVisible();
    await expect(page.getByTestId("quote-add-search-result-0-name")).toContainText(
      "リザードン ex SAR (in-stock)",
    );
    // 在庫 0 の候補は data-zero-stock=true
    await expect(page.getByTestId("quote-add-search-result-1")).toHaveAttribute("data-zero-stock", "true");

    // in-stock を選択 → 既存の空行(0)に続けて行(1)が追加され、標準名が入る
    await result0.click();
    await expect(page.getByTestId("quote-item-row-1-name")).toHaveValue("リザードン ex SAR (in-stock)");

    // 再検索 → zero-stock を選択 → さらに行(2)が追加され、警告が表示される
    await input.fill("リザードン");
    await page.waitForTimeout(400);
    await page.getByTestId("quote-add-search-result-1").click();
    await expect(page.getByTestId("quote-item-row-2-zero-stock-warning")).toBeVisible();
  });
});
