/**
 * inventory-raw-text-mobile.spec.ts — スマホの在庫カードから原文を見られるようにする（便1）
 *
 * design.md 設計 ⑤ Acceptance Criteria の A1〜A4・A6 を検査する。
 * 書き方は既存 `inventory-table-layout.spec.ts` を踏襲
 * （installAuthBypass → mockApi(page, {...commonMocks(), ...}) → page.goto("/inventory")
 *   → 1行目の testid 待ち）。
 *
 * 参照: docs/handoff/inventory-mobile-raw-text/design.md
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

function makeItems(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `row-${i + 1}`,
    product_id: 100 + i,
    product_name: `テスト商品 ${i + 1}`,
    name_en: null,
    category: "pokemon",
    mark: "SV8",
    condition: "sealed",
    unit: "BOX",
    offer_type: "in_stock",
    status: "in_stock",
    note_ja: "備考 あり",
    ship_ja: "即日 発送",
    merged_count: 1,
    extraction_item_ids: [`item-${i + 1}`],
    posted_at: null,
    ship_timing: null,
    supplier_id: 1,
    supplier_name: "仕入先 1",
    unit_price: 5000 + i * 100,
    quantity: 10 + i,
    work_code: "pokemon_booster_box",
    offered_at: "2026-10-15T01:00:00Z",
    release_date: "2026-09-01",
  }));
}

async function setup(page: Page, width: number, height: number, items = 5) {
  await page.setViewportSize({ width, height });
  await installAuthBypass(page);
  await mockApi(page, {
    ...commonMocks(),
    "GET /inventory": {
      items: makeItems(items),
      total: items,
      page: 1,
      per_page: 50,
      suppliers: [{ id: 1, name: "仕入先 1" }],
      categories: ["pokemon"],
      conditions: ["sealed"],
      units: ["BOX"],
      window_hours: 0,
      fresh_window_hours: 24,
    },
    "GET /me/inventory-filters": {
      enabled: false,
      hidden_supplier_ids: [],
      hidden_categories: [],
      hidden_columns: [],
    },
    "GET /products/tcg-types": [{ code: "pokemon_booster_box", name_ja: "ポケモン" }],
    "GET /inventory/raw-texts": {
      items: [{ extraction_item_id: "item-1", raw_text: "原文テキスト", line_start: 1, line_end: 1 }],
    },
  });
}

test.describe("在庫表スマホ原文ボタン（便1）", () => {
  test("375px: 各カードに原文ボタンが1つ・44x44以上（A1/A2）", async ({ page }) => {
    await setup(page, 375, 800);
    await page.goto("/inventory");
    await expect(page.getByTestId("inventory-row-row-1")).toBeVisible();

    const cardCount = await page
      .locator('[data-testid^="inventory-row-"][role="listitem"]')
      .count();
    const buttons = page.locator('[data-testid^="inventory-raw-text-"]');
    await expect(buttons).toHaveCount(cardCount);

    const sizes = await buttons.evaluateAll((els) =>
      els.map((el) => {
        const r = el.getBoundingClientRect();
        return { width: r.width, height: r.height };
      }),
    );
    console.log("A2 button sizes", JSON.stringify(sizes));
    for (const s of sizes) {
      expect(s.width).toBeGreaterThanOrEqual(44);
      expect(s.height).toBeGreaterThanOrEqual(44);
    }
  });

  test("375px: 原文ボタンを押すと全画面のパネルが開き下部タブを覆う（A3/A4）", async ({ page }) => {
    await setup(page, 375, 800);
    await page.goto("/inventory");
    await expect(page.getByTestId("inventory-row-row-1")).toBeVisible();

    await page.getByTestId("inventory-raw-text-row-1").click();
    const panel = page.getByTestId("supplier-drawer");
    await expect(panel).toBeVisible();

    const viewport = page.viewportSize();
    if (!viewport) throw new Error("viewport size is null");

    // Drawer はトランジション（--transition-slow 280ms）でスライドインするため、
    // 位置が viewport と一致するまで polling で待つ。
    await expect
      .poll(async () => {
        const box = await panel.boundingBox();
        return box ? { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) } : null;
      })
      .toEqual({ x: 0, y: 0, width: viewport.width, height: viewport.height });

    // A4: 下部タブバー（.mobile-tabbar）の中心を document.elementFromPoint で調べ、
    // 返るのがパネル側の要素であることを確かめる（z-index の数値比較だけでは確定しないため実測）。
    const hit = await page.evaluate(() => {
      const tabbar = document.querySelector(".mobile-tabbar");
      const panelEl = document.querySelector('[data-testid="supplier-drawer"]');
      if (!tabbar || !panelEl) return { tabbarFound: false, panelFound: !!panelEl, hitInPanel: false, hitInTabbar: false, hitTag: null, hitTestId: null };
      const r = tabbar.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const el = document.elementFromPoint(cx, cy);
      return {
        tabbarFound: true,
        panelFound: true,
        hitInPanel: !!el && (el === panelEl || panelEl.contains(el)),
        hitInTabbar: !!el && (el === tabbar || tabbar.contains(el)),
        hitTag: el ? el.tagName : null,
        hitTestId: el ? (el as HTMLElement).getAttribute("data-testid") : null,
      };
    });
    console.log("A4 elementFromPoint", JSON.stringify(hit));
    expect(hit.tabbarFound).toBe(true);
    expect(hit.hitInPanel).toBe(true);
    expect(hit.hitInTabbar).toBe(false);
  });

  test("1440px: 原文ボタンは出ない（A6）", async ({ page }) => {
    await setup(page, 1440, 900);
    await page.goto("/inventory");
    await expect(page.getByTestId("inventory-row-row-1")).toBeVisible();
    await expect(page.locator('[data-testid^="inventory-raw-text-"]')).toHaveCount(0);
  });
});
