/**
 * visual-language/inventory-helpers.ts — 在庫表スマホ検査で共通に使う mock と開き方
 *
 * inventory-raw-text-mobile.spec.ts（原文ボタンの合否）と
 * inventory-mobile-baseline.spec.ts（測るだけ）の両方から使う。mock の中身を
 * 2か所に分けて書くと片方だけ古くなるため、ここを唯一の置き場にする
 * （frontend/tests-e2e/visual-language/inbox-helpers.ts の書き方に倣う）。
 * このファイルは `.spec.ts` ではないので Playwright のテスト収集対象にはならない。
 */

import { expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { installAuthBypass } from "../utils/auth";
import { mockApi } from "../utils/api-mock";
import { commonMocks } from "../utils/common-mocks";

/** 在庫表の行データを n 件作る */
export function makeInventoryItems(n: number) {
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

/**
 * 原文（raw-texts）の行データを n 件作る。
 * n===1 のときは既存の固定値（"item-1" / "原文テキスト"）のまま返す
 * （既存 spec の挙動を変えないため）。n>=2 のときは行ドロワーのタブ
 * （InventoryRowDrawer.tsx:161-169、原文2件以上で出る itemTabs）を実際に
 * 出すために、id・文面を1件ずつ違う値にする。
 */
function makeRawTextItems(n: number) {
  if (n <= 1) {
    return [{ extraction_item_id: "item-1", raw_text: "原文テキスト", line_start: 1, line_end: 1 }];
  }
  return Array.from({ length: n }, (_, i) => ({
    extraction_item_id: `item-${i + 1}`,
    raw_text: `原文テキスト ${i + 1}`,
    line_start: 1,
    line_end: 1,
  }));
}

/** 認証とAPI mockだけ入れる（viewport設定・ページ遷移はしない） */
export async function installInventoryMocks(
  page: Page,
  opts?: { items?: number; rawTexts?: number },
): Promise<void> {
  const items = opts?.items ?? 5;
  const rawTexts = opts?.rawTexts ?? 1;
  await installAuthBypass(page);
  await mockApi(page, {
    ...commonMocks(),
    "GET /inventory": {
      items: makeInventoryItems(items),
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
      items: makeRawTextItems(rawTexts),
    },
  });
}

/** 在庫表を開き、viewport設定→mock→遷移→1行目が見えるまで待つ、をまとめて行う */
export async function gotoInventory(
  page: Page,
  opts?: { width?: number; height?: number; items?: number; rawTexts?: number },
): Promise<void> {
  const width = opts?.width ?? 390;
  const height = opts?.height ?? 844;
  await page.setViewportSize({ width, height });
  await installInventoryMocks(page, { items: opts?.items, rawTexts: opts?.rawTexts });
  await page.goto("/inventory");
  await expect(page.getByTestId("inventory-row-row-1")).toBeVisible();
}
