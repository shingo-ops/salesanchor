/**
 * ProductEditPage の tcg_type 選択が master code を表示・保存することを確認する E2E。
 *
 * - dark mode でフォームが描画される
 * - 既存値が master label で表示される
 * - 変更後の PATCH payload に master code が入る
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi, type MockMap } from "./utils/api-mock";
import { commonMocks, ALL_PERMISSIONS } from "./utils/common-mocks";

const productFixture = {
  id: 123,
  product_code: "PD-00123",
  name_ja: "編集対象商品",
  name_en: "Editable Product",
  product_kind: "TCG",
  category: "Pokemon TCG",
  mark: "SV1",
  status: "active",
  condition: null,
  unit_price: null,
  quantity: 0,
  weight: null,
  notes: null,
  release_date: null,
  created_at: "2026-06-22T00:00:00Z",
  updated_at: "2026-06-22T00:00:00Z",
  jan_code: null,
  card_number: null,
  expansion_code: null,
  rarity: null,
  language: null,
  unit_price_usd: null,
  unit_price_eur: null,
  image_url: null,
  is_archived: false,
  archived_at: null,
  supplier_default_id: null,
  tcg_type: "one_piece",
  set_type: null,
  unit: null,
  boxes_per_case: null,
  packs_per_box: null,
  box_weight_kg: null,
  case_weight_kg: null,
  volume_weight: null,
  moq: null,
  hs_code: null,
  material: null,
  item: null,
  required_output_value: null,
  search_keywords: null,
  exclude_keywords: null,
  related_series: null,
  display_order: null,
};

function baseMocks(): MockMap {
  return {
    ...commonMocks(),
    "GET /me/permissions": {
      permissions: [...ALL_PERMISSIONS, "products.view", "products.create", "products.update"],
    },
    "GET /staff/me": {
      id: 1,
      primary_email: "review@salesanchor.jp",
      theme: "dark",
      ui_preferences: {
        dark_mode: true,
        show_chat_menu: true,
        show_sales_menu: true,
        show_settings_menu: true,
        show_admin_menu: true,
        show_sidebar: true,
      },
    },
    "GET /products/tcg-types": [
      { code: "pokemon_booster_box", name_ja: "ポケモンカード" },
      { code: "one_piece", name_ja: "ワンピース" },
      { code: "dragon_ball", name_ja: "ドラゴンボール" },
    ],
    "GET /products/attribute-options": {},
    "GET /products/123": { body: productFixture },
  };
}

test.describe("ProductEditPage tcg_type master selector", () => {
  test("master label を表示し、保存時に master code を送る", async ({ page }) => {
    let patchBody: Record<string, unknown> | null = null;

    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "PATCH /products/123": async (route) => {
        patchBody = route.request().postDataJSON() as Record<string, unknown>;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...productFixture,
            tcg_type: patchBody?.tcg_type ?? null,
          }),
        });
      },
    });

    await page.goto("/admin/products/123/edit");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("html")).toHaveClass(/force-dark/);
    const tcgTypeSelect = page.getByTestId("product-edit-tcg-type");
    await expect(tcgTypeSelect).toBeVisible();
    await expect(page.locator('[data-testid="product-edit-tcg-type"] option:checked')).toHaveText("ワンピース");

    await tcgTypeSelect.selectOption("pokemon_booster_box");
    await expect(page.locator('[data-testid="product-edit-tcg-type"] option:checked')).toHaveText("ポケモンカード");

    await page.getByTestId("product-edit-save").click();
    await expect.poll(() => patchBody?.tcg_type).toBe("pokemon_booster_box");
  });
});
