/**
 * InventoryModeTabs mock E2E.
 *
 * /inventory と /own-inventory のタブ切替を、実 backend なしで確認する。
 * Firebase は auth bypass、API は Playwright route で mock する。
 */
import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const inventoryResponse = {
  items: [
    {
      id: 101,
      product_id: 1001,
      product_name: "リザードン ex SAR",
      name_en: "Charizard ex SAR",
      category: "ポケモン",
      mark: "SV3",
      condition: "sealed",
      unit: "box",
      offer_type: "in_stock",
      ship_timing: "immediate",
      supplier_id: 1,
      supplier_name: "Sample Supplier",
      unit_price: 1500,
      quantity: 3,
      tcg_type: null,
      offered_at: "2026-06-19T00:00:00+09:00",
    },
  ],
  total: 1,
  page: 1,
  per_page: 50,
  suppliers: [{ id: 1, name: "Sample Supplier" }],
  categories: ["ポケモン"],
  conditions: ["sealed"],
  units: ["box"],
};

const ownInventoryResponse = [
  {
    id: 201,
    tenant_id: 1,
    product_id: 2001,
    physical_qty: 5,
    reserved_qty: 1,
    available_qty: 4,
    unit_price: 2000,
    condition: "near_mint",
    status: "active",
    note_ja: null,
    note_en: null,
    antique_ledger_id: null,
    created_at: "2026-06-19T00:00:00+09:00",
    updated_at: "2026-06-19T00:00:00+09:00",
  },
];

async function setupMocks(page: Parameters<typeof installAuthBypass>[0]) {
  await installAuthBypass(page);
  await mockApi(page, {
    ...commonMocks(),
    "GET /products/tcg-types": [],
    "GET /me/inventory-filters": {
      enabled: false,
      hidden_supplier_ids: [],
      hidden_categories: [],
      hidden_columns: [],
      show_conditions: [],
      show_units: [],
      show_offer_types: [],
      qty_min: null,
      qty_max: null,
      price_min: null,
      price_max: null,
    },
    "PATCH /me/inventory-filters": {
      enabled: false,
      hidden_supplier_ids: [],
      hidden_categories: [],
      hidden_columns: [],
      show_conditions: [],
      show_units: [],
      show_offer_types: [],
      qty_min: null,
      qty_max: null,
      price_min: null,
      price_max: null,
    },
    "GET /inventory": inventoryResponse,
    "GET /own-inventory": ownInventoryResponse,
  });
}

test.describe("Inventory mode tabs", () => {
  test("/inventory で WEGO在庫が active、/own-inventory へ切替できる", async ({
    page,
  }) => {
    await setupMocks(page);
    await page.goto("/inventory");

    await expect(page).toHaveURL("/inventory");
    await expect(page.getByRole("heading", { name: "在庫表" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "WEGO在庫" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("tab", { name: "自社在庫" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    await expect(page.getByText("WEGO", { exact: true })).toBeVisible();
    await expect(page.getByTestId("inventory-table")).toBeVisible();
    await expect(page.getByText("リザードン ex SAR")).toBeVisible();

    await page.getByRole("tab", { name: "自社在庫" }).click();

    await expect(page).toHaveURL("/own-inventory");
    await expect(page.getByRole("heading", { name: "在庫表" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "自社在庫" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("tab", { name: "WEGO在庫" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    await expect(page.getByText("自社", { exact: true })).toBeVisible();
    await expect(page.getByText("2001")).toBeVisible();
  });

  test("/own-inventory を直接開くと自社在庫が active", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/own-inventory");

    await expect(page).toHaveURL("/own-inventory");
    await expect(page.getByRole("heading", { name: "在庫表" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "自社在庫" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("tab", { name: "WEGO在庫" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    await expect(page.getByText("自社", { exact: true })).toBeVisible();
    await expect(page.getByText("2001")).toBeVisible();
  });
});
