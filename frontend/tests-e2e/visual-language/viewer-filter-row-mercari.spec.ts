/**
 * visual-language/viewer-filter-row-mercari.spec.ts
 * — 閲覧ページ（/viewer/）スマホ絞り込み副画面「提供者」「コンディション」の項目の行を
 *   お手本（メルカリ）と同じ高さ・同じ文字の大きさ・同じ未選択文言にする便（便11）の合否検査。
 *
 * design: docs/handoff/viewer-filter-row-mercari/design.md 設計④・⑤ Acceptance Criteria B1〜B9。
 * recon: docs/handoff/viewer-filter-row-mercari/recon.md（現物調査）。
 *
 * B1〜B4・B6 は「直す前は赤」（design.md ⑤）。B5・B5b は項目の行の文言変更が要約の組み立て
 * （MultiSelect.tsx:82 の selectedSummary）を壊していないことの確認（0件/1件/2件の3状態）。
 *
 * 幅は spec 側で明示する: スマホは360px・390pxの両方。B6（PC）のみ1280px
 * （vl-mobile-390/vl-tablet-768/vl-desktop-1280 の3 project すべてがこの spec を収集するため、
 * 明示しないと project 既定の幅で赤になる。design.md ⑤・独立審査の指摘7。
 * frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts の A18 と同じ形）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** design.md ③P1: 項目の行の高さ（お手本実測52.7dp→53px） */
const EXPECTED_ROW_HEIGHT = 53;
/** design.md ③P2・P3: 左ラベル・右の現在値の文字（お手本17.7dp箱→14.4px） */
const EXPECTED_FONT_SIZE = "14.4px";

/**
 * 絞り込みボタンを押してドロワーを開き、スライドの transition が収まるまで待つ
 * （frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts の
 * openFilterDrawer と同じ形。同ファイルは helper を export していないためここに複製する）。
 */
async function openFilterDrawer(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-filter-toggle").click();
  const panel = page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
  await expect(panel).toHaveCount(1);
  await expect(panel).toBeVisible();
  await expect
    .poll(async () => {
      const box = await panel.boundingBox();
      return box ? Math.round(box.x) : null;
    })
    .toBe(0);
  return panel;
}

/** getComputedStyle(el).fontSize を取る */
async function fontSizeOf(locator: Locator): Promise<string> {
  return locator.evaluate((el) => getComputedStyle(el).fontSize);
}

for (const width of MOBILE_WIDTHS) {
  const height = 700;
  test.describe(`visual-language: 閲覧ページ 絞り込みの項目の行 ${width}px`, () => {
    test("B1: 提供者・コンディションの行の高さが53pxちょうど（直す前は赤=44px）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const providerRow = panel.getByTestId("viewer-provider-row");
      const conditionRow = panel.getByTestId("viewer-condition-row");
      await expect(providerRow).toBeVisible();
      await expect(conditionRow).toBeVisible();

      const providerBox = await providerRow.boundingBox();
      const conditionBox = await conditionRow.boundingBox();
      expect(providerBox).not.toBeNull();
      expect(conditionBox).not.toBeNull();
      expect(providerBox!.height).toBe(EXPECTED_ROW_HEIGHT);
      expect(conditionBox!.height).toBe(EXPECTED_ROW_HEIGHT);
    });

    test("B2・B3: 行の左ラベル・右の現在値の文字が14.4px（直す前は赤=13.6px）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const providerRow = panel.getByTestId("viewer-provider-row");
      await expect(providerRow).toBeVisible();

      const label = providerRow.locator(".comp-multiselect__row-label");
      const value = providerRow.locator(".comp-multiselect__row-value");
      await expect(label).toBeVisible();
      await expect(value).toBeVisible();

      expect(await fontSizeOf(label)).toBe(EXPECTED_FONT_SIZE);
      expect(await fontSizeOf(value)).toBe(EXPECTED_FONT_SIZE);
    });

    test("B4: 未選択のとき、提供者行の現在値が「指定しない」（直す前は赤=「すべて」）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const value = panel.getByTestId("viewer-provider-row").locator(".comp-multiselect__row-value");
      await expect(value).toBeVisible();
      await expect(value).toHaveText("指定しない");
    });

    test("B5: 0件→1件→2件で提供者行の文字が切り替わる（退行防止）", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const row = panel.getByTestId("viewer-provider-row");
      const value = row.locator(".comp-multiselect__row-value");
      await expect(value).toBeVisible();

      // 0件: 「指定しない」
      await expect(value).toHaveText("指定しない");

      // 1件: 選んだ名前そのまま
      const [p0, p1] = fixture.providers;
      await row.click();
      await panel.getByTestId(`viewer-provider-options-option-${p0}`).click();
      await panel.getByTestId("drawer-back").click();
      await expect(value).toHaveText(p0);

      // 2件: カンマつなぎ
      await row.click();
      await panel.getByTestId(`viewer-provider-options-option-${p1}`).click();
      await panel.getByTestId("drawer-back").click();
      await expect(value).toHaveText(`${p0}, ${p1}`);
    });

    test("B5b: 選択画面の要約欄が未選択で「指定しない」・1行のまま（直す前は赤=「すべて」）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      await panel.getByTestId("viewer-provider-row").click();
      const summary = panel.locator(".comp-multiselect__inline-summary");
      await expect(summary).toBeVisible();
      await expect(summary).toHaveText("指定しない");

      const wrapped = await summary.evaluate((el) => el.scrollHeight > el.clientHeight + 1);
      expect(wrapped).toBe(false);
    });
  });
}

test.describe("visual-language: 閲覧ページ PC(1280px) 絞り込みの文言", () => {
  test("B6: 提供者の浮かぶプルダウンのボタンに「指定しない」が出る（直す前は赤=「すべて」）", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    const button = page.getByTestId("viewer-provider-filter-button");
    await expect(button).toBeVisible();
    await expect(button).toHaveText("提供者: 指定しない");

    const box = await button.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x + box!.width).toBeLessThanOrEqual(1280);
  });

  test("B6: コンディションの浮かぶプルダウンのボタンにも「指定しない」が出る", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    const button = page.getByTestId("viewer-condition-filter-button");
    await expect(button).toBeVisible();
    await expect(button).toHaveText("コンディション: 指定しない");

    const box = await button.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x + box!.width).toBeLessThanOrEqual(1280);
  });
});
