/**
 * inventory-table-layout.spec.ts — 在庫表 (/inventory) のレイアウト検査（便2）
 *
 * - 375px: カード表示（thead なし）。横はみ出しは document ではなく .mobile-content と各カードで測る
 *   （mobile-shell.css:22-25 で .mobile-content が横スクロールを持つため）
 * - 900px: 表が枠の幅に合わせて縮み（--comp-table-fit-zoom < 1）、見出し固定の表が画面内に収まる
 * - 1440px: 縮まない（--comp-table-fit-zoom が未設定）
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const LONG_NAME =
  "ポケモンカードゲーム スカーレット＆バイオレット 拡張パック 超電ブレイカー 未開封 1BOX シュリンク付き 国内正規品 特別限定セット";
const LONG_NOTE =
  "状態は非常に良好です。箱に目立つ傷や凹みはありません。 発送は入金確認後に順次行います。 同梱希望の場合は事前にご連絡ください。";

function makeItems(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `row-${i + 1}`,
    product_id: 100 + i,
    product_name: i < 3 ? LONG_NAME : `テスト商品 ${i + 1}`,
    name_en: i < 3 ? "Pokemon Card Game Scarlet and Violet Expansion Pack Super Electric Breaker" : null,
    category: "pokemon",
    mark: "SV8",
    condition: ["sealed", "damaged", "case", "New"][i % 4],
    unit: "BOX",
    offer_type: i % 5 === 0 ? "pre_order" : "in_stock",
    status: "in_stock",
    note_ja: i < 3 ? LONG_NOTE : "備考 あり",
    ship_ja: i < 3 ? LONG_NOTE : "即日 発送",
    merged_count: i % 7 === 0 ? 3 : 1,
    posted_at: null,
    ship_timing: i % 5 === 0 ? "on_release" : null,
    supplier_id: 1 + (i % 3),
    supplier_name: `仕入先 ${1 + (i % 3)}`,
    unit_price: 5000 + i * 100,
    quantity: 10 + i,
    work_code: "pokemon_booster_box",
    offered_at: "2026-10-15T01:00:00Z",
    release_date: "2026-09-01",
  }));
}

async function setup(page: Page, width: number, height: number, items = 25) {
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
      conditions: ["sealed", "damaged", "case", "New"],
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
  });
}

test.describe("在庫表レイアウト", () => {
  test("375px: カード表示で横にはみ出さない", async ({ page }) => {
    await setup(page, 375, 800);
    await page.goto("/inventory");
    const firstCard = page.getByTestId("inventory-row-row-1");
    await expect(firstCard).toBeVisible();
    await expect(page.locator("thead")).toHaveCount(0);
    const m = await page.evaluate(() => {
      const mc = document.querySelector(".mobile-content");
      const cards = Array.from(document.querySelectorAll('[data-testid^="inventory-row-"][role="listitem"]'));
      return {
        hasMobileContent: !!mc,
        mcScroll: mc ? mc.scrollWidth : -1,
        mcClient: mc ? mc.clientWidth : -1,
        docScroll: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        cardCount: cards.length,
        maxRight: Math.max(...cards.map((c) => c.getBoundingClientRect().right)),
      };
    });
    console.log("375px", JSON.stringify(m));
    expect(m.hasMobileContent).toBe(true);
    expect(m.cardCount).toBeGreaterThanOrEqual(20);
    expect(m.mcScroll).toBeLessThanOrEqual(m.mcClient);
    expect(m.maxRight).toBeLessThanOrEqual(m.innerWidth);
    expect(m.docScroll).toBeLessThanOrEqual(m.innerWidth);
  });

  test("900px: 表が縮み、見出し固定の表が画面内に収まる", async ({ page }) => {
    await setup(page, 900, 800);
    await page.goto("/inventory");
    await expect(page.getByTestId("inventory-row-row-1")).toBeVisible();
    await expect.poll(async () =>
      page.evaluate(() => {
        const v = document.querySelector<HTMLElement>(".comp-table-fit__card")?.style.getPropertyValue("--comp-table-fit-zoom");
        return v ? parseFloat(v) : 1;
      }),
    ).toBeLessThan(1);
    const m = await page.evaluate(() => {
      const card = document.querySelector<HTMLElement>(".comp-table-fit__card")!;
      const box = document.querySelector<HTMLElement>(".comp-table--sticky")!;
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
      const frame = document.querySelector<HTMLElement>(".comp-table-frame")!;
      return {
        zoom: parseFloat(card.style.getPropertyValue("--comp-table-fit-zoom")),
        boxHeight: box.getBoundingClientRect().height,
        limit: window.innerHeight - 18 * rem,
        boxRight: box.getBoundingClientRect().right,
        frameRight: frame.getBoundingClientRect().right,
        boxScrollW: box.scrollWidth,
        boxClientW: box.clientWidth,
        docScroll: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
      };
    });
    console.log("900px", JSON.stringify(m));
    expect(m.zoom).toBeLessThan(1);
    expect(m.boxHeight).toBeLessThanOrEqual(m.limit + 1);
    expect(m.boxRight).toBeLessThanOrEqual(m.frameRight + 1);
    expect(m.docScroll).toBeLessThanOrEqual(m.innerWidth);
  });

  test("1440px: 縮まない", async ({ page }) => {
    await setup(page, 1440, 900);
    await page.goto("/inventory");
    await expect(page.getByTestId("inventory-row-row-1")).toBeVisible();
    const zoom = await page.evaluate(
      () => document.querySelector<HTMLElement>(".comp-table-fit__card")?.style.getPropertyValue("--comp-table-fit-zoom") ?? "",
    );
    console.log("1440px zoom=[" + zoom + "]");
    expect(zoom).toBe("");
  });
});
