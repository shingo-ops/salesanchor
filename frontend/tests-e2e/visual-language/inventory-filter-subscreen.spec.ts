/**
 * visual-language/inventory-filter-subscreen.spec.ts
 * — 在庫表（/inventory）スマホの詳細フィルタを「右から出るパネル→項目を押すと次の画面で選ぶ」形に
 *   作り替える便（便3）の合否検査。
 *
 * design: docs/handoff/inventory-filter-subscreen/design.md 設計④・⑤ Acceptance Criteria G1〜G9・
 * P1〜P11。宣言はちょうど9本（J1〜J9・審査 M6）。visual-language/*.spec.ts は vl-mobile-390 /
 * vl-tablet-768 / vl-desktop-1280 の3 project で走るため9宣言＝27実行（design.md ⑤）。
 *
 * 幅は360px固定（design.md 4-9 と同じ便の既存 spec に合わせる）。J7 だけ PC（1280px）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoInventory, makeInventoryItems } from "./inventory-helpers";

const WIDTH = 360;
const HEIGHT = 800;
const PC_WIDTH = 1280;

/** design.md ③ P1: パネル幅は画面幅の83%、左端xは画面幅の17%（frontend/src/tokens.css:445） */
const PANEL_WIDTH_RATIO = 0.83;
const PANEL_INSET_RATIO = 0.17;
/** design.md ③ P2: root の押せる行の高さ下限（.comp-multiselect__row は53px） */
const MIN_ROOT_ROW_H = 44;
/** design.md ③ P3: 次の画面の選択行の高さ下限（--comp-multiselect-check-row-h: 61px） */
const MIN_OPTION_ROW_H = 61;

/** 「詳細フィルタ」を押してパネルの中身（inventory-filter-panel）を開く。
 *  中身は開く前から DOM にあるため（design.md 4-3）、スライドの完了は待たない
 *  （既存 D6・D7・E10 と同じ形。frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts:87-92） */
async function openFilterPanel(page: Page): Promise<Locator> {
  await page.getByTestId("inventory-filter-toggle").click();
  const panel = page.getByTestId("inventory-filter-panel");
  await expect(panel).toBeVisible();
  return panel;
}

/** 詳細フィルタの Drawer 本体（mobileInset 持ち）が右端まで収まるのを待つ。
 *  mobileInset のため左端は0にならないので、お手本（閲覧ページ）と同じく右端(x+width)が
 *  viewport 右端に一致することで判定する（frontend/tests-e2e/visual-language/viewer-helpers.ts
 *  の waitPanelSlidIn と同じ考え方。design.md 4-3） */
async function openFilterDrawerOuter(page: Page): Promise<Locator> {
  await page.getByTestId("inventory-filter-toggle").click();
  const outer = page.locator(".comp-drawer-panel--mobile-inset.comp-drawer-panel--open");
  await expect(outer).toHaveCount(1);
  const viewportRight = await page.evaluate(() => document.documentElement.clientWidth);
  await expect
    .poll(async () => {
      const box = await outer.boundingBox();
      return box ? Math.round(box.x + box.width) : null;
    })
    .toBe(viewportRight);
  return outer;
}

async function expectNoPageOverflow(page: Page): Promise<void> {
  const data = await page.evaluate(() => {
    const mc = document.querySelector(".mobile-content");
    return {
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      mobileContent: mc ? mc.scrollWidth - mc.clientWidth : 0,
    };
  });
  expect(data.doc).toBeLessThanOrEqual(0);
  expect(data.mobileContent).toBeLessThanOrEqual(0);
}

test.describe("visual-language: 在庫表 詳細フィルタの副画面", () => {
  test("J1: パネル幅=画面の83%±1px・左端=17%±1px（G1・P1）。地（オーバーレイ）を押すと閉じる", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });
    const outer = await openFilterDrawerOuter(page);

    const box = await outer.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(WIDTH * PANEL_WIDTH_RATIO - 1);
    expect(box!.width).toBeLessThanOrEqual(WIDTH * PANEL_WIDTH_RATIO + 1);
    expect(box!.x).toBeGreaterThanOrEqual(WIDTH * PANEL_INSET_RATIO - 1);
    expect(box!.x).toBeLessThanOrEqual(WIDTH * PANEL_INSET_RATIO + 1);

    // 左に残った地（オーバーレイ）を押すと閉じる
    const probeX = Math.round(box!.x / 2);
    const probeY = Math.round(HEIGHT / 2);
    await page.locator(".comp-drawer-overlay").click({ position: { x: probeX, y: probeY } });
    await expect(page.locator(".comp-drawer-panel--mobile-inset.comp-drawer-panel--open")).toHaveCount(0);
  });

  test("J2: root に12個が縦に並び、順番も今のまま（G2）。見える「閉じる」ボタンは0件（✕ の読み上げ名1件は除く）", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });
    const panel = await openFilterPanel(page);

    const ids = [
      "inventory-fresh-check",
      "inventory-expiry-warning",
      "inventory-supplier-filter-row",
      "inventory-condition-filter-row",
      "inventory-price-min",
      "inventory-qty-min",
      "inventory-filter-enabled",
      "inventory-category-filter-row",
      "inventory-columns-filter-row",
      "inventory-unit-filter-row",
      "inventory-offertype-filter-row",
      "inventory-reset-in-panel",
    ];
    const ys: number[] = [];
    for (const id of ids) {
      const el = panel.getByTestId(id);
      await expect(el).toBeVisible();
      const box = await el.boundingBox();
      expect(box).not.toBeNull();
      ys.push(box!.y);
    }
    for (let i = 0; i < ys.length - 1; i++) expect(ys[i]).toBeLessThan(ys[i + 1]);

    // 「閉じる」ボタンは✕（drawer-close・読み上げ名「閉じる」）の1件だけ（design.md 4-9・PO 決定3）。
    // ページ全体で数えてはいけない: ✕ は headerContent の無い Drawer すべてに無条件で描かれ
    // （frontend/src/components/Drawer.tsx:176-185）、Drawer は閉じても DOM に残る（同:132 のコメント）
    // ため、スマホの在庫表には同時に3枚（設定パネル frontend/src/pages/inventory/InventoryPage.tsx:601・
    // 種別/並び替えパネル 同:719-729・本便のパネル frontend/src/pages/inventory/InventoryFilterDrawer.tsx:464）
    // がマウントされている。よって本便のパネル（mobileInset を持つ外枠）の中だけで数える
    const outer = page.locator(".comp-drawer-panel--mobile-inset.comp-drawer-panel--open");
    await expect(outer).toHaveCount(1);
    await expect(outer.getByRole("button", { name: "閉じる" })).toHaveCount(1);
    await expect(outer.getByTestId("drawer-close")).toHaveCount(1);
  });

  test("J3: 「＞」の6行を押すと次の画面になり「←」が出る。「決定する」で root に戻り、選んだ名前が行の右に出る（G3）", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });
    const panel = await openFilterPanel(page);

    const cases = [
      { row: "inventory-supplier-filter-row", option: "inventory-supplier-filter-option-1", label: "仕入先 1" },
      { row: "inventory-condition-filter-row", option: "inventory-condition-filter-option-sealed", label: "sealed" },
      { row: "inventory-category-filter-row", option: "inventory-category-filter-option-pokemon", label: "pokemon" },
      { row: "inventory-columns-filter-row", option: "inventory-columns-filter-option-mark", label: "型番" },
      { row: "inventory-unit-filter-row", option: "inventory-unit-filter-option-BOX", label: "BOX" },
      { row: "inventory-offertype-filter-row", option: "inventory-offertype-filter-option-in_stock", label: "在庫" },
    ];

    for (const c of cases) {
      await panel.getByTestId(c.row).click();
      const back = page.getByTestId("drawer-back");
      await expect(back).toBeVisible();

      await panel.getByTestId(c.option).click();
      await page.getByTestId("inventory-filter-apply").click();

      await expect(page.getByTestId("drawer-back")).toHaveCount(0);
      await expect(panel.getByTestId(c.row)).toContainText(c.label);
    }
  });

  test("J4: 6項目すべてが一覧に効き、4項目を選ぶと「フィルタを有効化」が自動で入る（G4・G8後半・P10・P11の裏取り）", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });

    const urls: string[] = [];
    await page.route(/\/api\/v1\/inventory(\?|$)/, async (route) => {
      urls.push(route.request().url());
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: makeInventoryItems(5),
          total: 5,
          page: 1,
          per_page: 50,
          suppliers: [{ id: 1, name: "仕入先 1" }],
          categories: ["pokemon"],
          conditions: ["sealed"],
          units: ["BOX"],
          window_hours: 0,
          fresh_window_hours: 24,
        }),
      });
    });

    const enabledCheckbox = page.getByTestId("inventory-filter-enabled");
    const panel = await openFilterPanel(page);
    await expect(enabledCheckbox).not.toBeChecked();

    // 提供者・コンディション: 有効化に関わらず常に効く（design.md 4-5a の対象外）
    await panel.getByTestId("inventory-supplier-filter-row").click();
    await panel.getByTestId("inventory-supplier-filter-option-1").click();
    await page.getByTestId("inventory-filter-apply").click();
    await expect.poll(() => urls[urls.length - 1] ?? "").toContain("supplier_ids=1");

    await panel.getByTestId("inventory-condition-filter-row").click();
    await panel.getByTestId("inventory-condition-filter-option-sealed").click();
    await page.getByTestId("inventory-filter-apply").click();
    await expect.poll(() => urls[urls.length - 1] ?? "").toContain("condition_in=sealed");

    await expect(enabledCheckbox).not.toBeChecked();

    // 隠すシリーズ: 問い合わせに hide_categories が乗り、有効化が自動で入る（PO 決定6）
    await panel.getByTestId("inventory-category-filter-row").click();
    await panel.getByTestId("inventory-category-filter-option-pokemon").click();
    await page.getByTestId("inventory-filter-apply").click();
    await expect(enabledCheckbox).toBeChecked();
    await expect.poll(() => urls[urls.length - 1] ?? "").toContain("hide_categories=pokemon");

    // 形態
    await panel.getByTestId("inventory-unit-filter-row").click();
    await panel.getByTestId("inventory-unit-filter-option-BOX").click();
    await page.getByTestId("inventory-filter-apply").click();
    await expect.poll(() => urls[urls.length - 1] ?? "").toContain("unit_in=BOX");

    // 在庫・予約
    await panel.getByTestId("inventory-offertype-filter-row").click();
    await panel.getByTestId("inventory-offertype-filter-option-in_stock").click();
    await page.getByTestId("inventory-filter-apply").click();
    await expect.poll(() => urls[urls.length - 1] ?? "").toContain("offer_type_in=in_stock");

    // 隠す列: 問い合わせに語は乗らない（列の見せ方だけの変更）が、行の表示は選んだ名前に変わる
    await panel.getByTestId("inventory-columns-filter-row").click();
    await panel.getByTestId("inventory-columns-filter-option-mark").click();
    await page.getByTestId("inventory-filter-apply").click();
    await expect(panel.getByTestId("inventory-columns-filter-row")).toContainText("型番");
  });

  test("J5: ボタンの文字は常に「詳細フィルタ」と完全一致し、数字を含まない（G5）", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });
    const toggle = page.getByTestId("inventory-filter-toggle");
    await expect(toggle).toHaveText("詳細フィルタ");

    const panel = await openFilterPanel(page);
    await panel.getByTestId("inventory-fresh-check").click();
    await expect(toggle).toHaveText("詳細フィルタ");

    await panel.getByTestId("inventory-category-filter-row").click();
    await panel.getByTestId("inventory-category-filter-option-pokemon").click();
    await page.getByTestId("inventory-filter-apply").click();
    await expect(toggle).toHaveText("詳細フィルタ");
    expect(await toggle.textContent()).not.toMatch(/\(\d+\)/);
  });

  test("J6: 横スクロール0・はみ出し0（G6）。パネル内の子の右端がパネル幅以内", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });
    const panel = await openFilterPanel(page);

    const panelBox = await panel.boundingBox();
    expect(panelBox).not.toBeNull();
    const childRights = await panel.evaluate((el) => Array.from(el.children).map((c) => c.getBoundingClientRect().right));
    for (const right of childRights) expect(right).toBeLessThanOrEqual(panelBox!.x + panelBox!.width + 0.5);

    await expectNoPageOverflow(page);
  });

  test(`J7: PC（幅${PC_WIDTH}px）は1pxも変わらない（G7）。.content-toolbar あり／inventory-filter-panel は section／supplier-drawer の枚数が今と同じ`, async ({ page }) => {
    await gotoInventory(page, { width: PC_WIDTH, height: 800 });

    await expect(page.locator(".content-toolbar")).toHaveCount(1);
    await expect(page.locator(".inventory-toolbar")).toHaveCount(0);

    await page.getByTestId("inventory-filter-toggle").click();
    const panel = page.getByTestId("inventory-filter-panel");
    await expect(panel).toBeVisible();
    expect(await panel.evaluate((el) => el.tagName)).toBe("SECTION");

    // PC では右から出るパネル（InventoryFilterDrawer の Drawer）は増えない。
    // supplier-drawer testid を持つのは今までどおり設定パネルの1枚だけ
    await expect(page.locator('[data-testid="supplier-drawer"]')).toHaveCount(1);
  });

  test("J8: root の行の高さが44px以上・次の画面の行の高さが61px以上（P2・P3）。「隠す〜」の行の右の文字が読める（G8前半）", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });
    const panel = await openFilterPanel(page);

    const rootRowBox = await panel.getByTestId("inventory-supplier-filter-row").boundingBox();
    expect(rootRowBox).not.toBeNull();
    expect(rootRowBox!.height).toBeGreaterThanOrEqual(MIN_ROOT_ROW_H);

    // 既定（なにも隠していない）でも「隠すシリーズ」の行の右の文字が読める（幅>0・文字が空でない）
    const catValue = panel.getByTestId("inventory-category-filter-row").locator(".comp-multiselect__row-value");
    await expect(catValue).toBeVisible();
    const catValueBox = await catValue.boundingBox();
    expect(catValueBox).not.toBeNull();
    expect(catValueBox!.width).toBeGreaterThan(0);
    expect((await catValue.textContent())?.trim().length).toBeGreaterThan(0);

    await panel.getByTestId("inventory-category-filter-row").click();
    const optionRow = page.getByTestId("inventory-category-filter-option-pokemon").locator("xpath=ancestor::label[1]");
    await expect(optionRow).toBeVisible();
    const optionBox = await optionRow.boundingBox();
    expect(optionBox).not.toBeNull();
    expect(optionBox!.height).toBeGreaterThanOrEqual(MIN_OPTION_ROW_H);
  });

  test("J9: フォーカスは次の画面で「←」へ、戻ると押した行へ移る（P8）。閉じている間は注記（inventory-expiry-warning）が0件（P9）", async ({ page }) => {
    await gotoInventory(page, { width: WIDTH, height: HEIGHT });
    await expect(page.getByTestId("inventory-expiry-warning")).toHaveCount(0);

    const panel = await openFilterPanel(page);
    await expect(page.getByTestId("inventory-expiry-warning")).toBeVisible();

    const supplierRow = panel.getByTestId("inventory-supplier-filter-row");
    await supplierRow.click();
    await expect(page.getByTestId("drawer-back")).toBeFocused();

    await page.getByTestId("drawer-back").click();
    await expect(supplierRow).toBeFocused();

    // root では Esc が onClose になる（onEscape 未設定）ため、Esc で閉じて P9 を確認する
    await page.keyboard.press("Escape");
    await expect(page.locator(".comp-drawer-panel--mobile-inset.comp-drawer-panel--open")).toHaveCount(0);
    await expect(page.getByTestId("inventory-expiry-warning")).toHaveCount(0);
  });
});
