/**
 * visual-language/viewer-inventory-mobile-filter.spec.ts
 * — 閲覧ページ（/viewer/）スマホ絞り込みの合否検査
 *
 * design: docs/handoff/viewer-inventory-mobile-filter/design.md 設計⑤ Acceptance Criteria A4〜A13。
 * recon: docs/handoff/viewer-inventory-mobile-filter/recon.md（実機の実測値）。
 *
 * RED-first（design.md 4-4）: 1本目のコミット（この spec とヘルパーだけ。frontend/src は0行）では
 * 不具合がまだ直っていないため、ここに書いた検査は赤になる想定。2本目のコミット
 * （MultiSelect に layout="inline" を足し、ドロワーの中だけ使う）で緑にする。
 *
 * 幅は spec 側で明示する（design.md 4-5）: 360px・390px の両方（recon の実機実測は360、
 * project 既定の vl-mobile-390 は390。両方測らないと片方だけ収まる場合を見逃す）。
 * A13 のみ PC（1280px）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** タップ領域の下限（ADR-140 の G4 と同じ測り方。design.md 4-2） */
const MIN_TAP_PX = 44;

/**
 * 絞り込みボタンを押してドロワーを開き、スライドの transition（--transition-slow）が
 * 収まるまで待つ。同じ data-testid（supplier-drawer）を持つ要素が複数存在しうるため
 * `.comp-drawer-panel--open` で絞る（design.md 4-5・PR #4602 の strict mode violation の教訓）。
 */
async function openFilterDrawer(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-filter-toggle").click();
  const panel = page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
  await expect(panel).toHaveCount(1);
  await expect(panel).toBeVisible();
  // スライドインの途中で測ると x が 0 でない（画面外からアニメーション中）ため収まるまで待つ
  await expect
    .poll(async () => {
      const box = await panel.boundingBox();
      return box ? Math.round(box.x) : null;
    })
    .toBe(0);
  return panel;
}

/** チェック欄の data-testid から、行全体（<label>）の bounding box を取る。無ければ null。 */
async function optionRowBox(
  panel: Locator,
  testId: string,
): Promise<{ x: number; y: number; width: number; height: number } | null> {
  return panel.getByTestId(testId).evaluate((el) => {
    const label = el.closest("label");
    if (!label) return null;
    const r = label.getBoundingClientRect();
    return { x: r.x, y: r.y, width: r.width, height: r.height };
  });
}

/** viewer.filter.pageOf（例:「1 / 2 ページ（全 60 件）」）から件数を取り出す */
function extractRowCount(text: string | null): number {
  const m = (text ?? "").match(/([\d,]+)\s*(?:件|items)/);
  if (!m) throw new Error(`row count not found in pagination label: "${text}"`);
  return Number(m[1].replace(/,/g, ""));
}

async function expectNoPageOverflow(page: Page): Promise<void> {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
}

/** A8: 浮かぶパネル（Popover）を document 全体で使っていないこと */
async function expectNoFloatingPopover(page: Page): Promise<void> {
  expect(await page.locator(".comp-popover").count()).toBe(0);
}

for (const width of MOBILE_WIDTHS) {
  test.describe(`visual-language: 閲覧ページ スマホ絞り込み ${width}px`, () => {
    test("A4・A5・A6・A7・A8・A9: 提供者の選択肢が見えて選べる。浮かぶパネルは使わない", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height: 700 });
      const panel = await openFilterDrawer(page);

      // A8: ドロワーが開いている間、document 全体で .comp-popover が 0 件
      await expectNoFloatingPopover(page);

      // A4: 提供者の選択肢が見えている（360px・390px の両方）
      const firstOptionId = `viewer-provider-filter-option-${fixture.providers[0]}`;
      await expect(panel.getByTestId(firstOptionId)).toBeVisible();

      // A5: 選択肢の行が画面幅に収まる／A6: 行の高さが44px以上
      const box = await optionRowBox(panel, firstOptionId);
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);

      // A7: ページ全体の横はみ出しが0
      await expectNoPageOverflow(page);

      // A9: 2件選ぶと表の行数が減る
      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());
      await panel.getByTestId(firstOptionId).click();
      await panel.getByTestId(`viewer-provider-filter-option-${fixture.providers[1]}`).click();
      const after = extractRowCount(await pageInfo.textContent());
      expect(after).toBeLessThan(before);

      // 選んでいる間も浮かぶパネルは使わない
      await expectNoFloatingPopover(page);
    });

    test("A10: 提供者20件以上の fixture で、選択肢の総数が一致し最後の1件まで見える", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height: 700 });
      const panel = await openFilterDrawer(page);

      const options = panel.locator('[data-testid^="viewer-provider-filter-option-"]');
      await expect(options).toHaveCount(fixture.providers.length);

      const lastValue = fixture.providers[fixture.providers.length - 1];
      const last = panel.getByTestId(`viewer-provider-filter-option-${lastValue}`);
      await last.scrollIntoViewIfNeeded();
      await expect(last).toBeVisible();
    });

    test("A11: 一覧を下にスクロールしてから絞り込みを開いても選択肢が見える", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height: 700 });
      await page.evaluate(() => window.scrollTo(0, 2000));

      const panel = await openFilterDrawer(page);
      const firstOptionId = `viewer-provider-filter-option-${fixture.providers[0]}`;
      await expect(panel.getByTestId(firstOptionId)).toBeVisible();
      const box = await optionRowBox(panel, firstOptionId);
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    });

    test("A12: コンディションでも A4〜A10 が成り立つ", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height: 700 });
      const panel = await openFilterDrawer(page);

      await expectNoFloatingPopover(page);

      const firstOptionId = `viewer-condition-filter-option-${fixture.conditions[0]}`;
      await expect(panel.getByTestId(firstOptionId)).toBeVisible();

      const box = await optionRowBox(panel, firstOptionId);
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);

      await expectNoPageOverflow(page);

      const options = panel.locator('[data-testid^="viewer-condition-filter-option-"]');
      await expect(options).toHaveCount(fixture.conditions.length);
      const lastValue = fixture.conditions[fixture.conditions.length - 1];
      const last = panel.getByTestId(`viewer-condition-filter-option-${lastValue}`);
      await last.scrollIntoViewIfNeeded();
      await expect(last).toBeVisible();

      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());
      await panel.getByTestId(firstOptionId).click();
      const after = extractRowCount(await pageInfo.textContent());
      expect(after).toBeLessThanOrEqual(before);
    });
  });
}

test.describe("visual-language: 閲覧ページ PC(1280px) の絞り込み", () => {
  test("A13: PC は popover のまま。一覧の幅は400px以上", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    await expect(page.locator(".comp-popover")).toHaveCount(0);
    await page.getByTestId("viewer-provider-filter-button").click();

    const popover = page.locator(".comp-popover");
    await expect(popover).toHaveCount(1);
    await expect(popover).toBeVisible();

    const box = await popover.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(400);
  });

  test("A13: コンディションも PC では popover のまま", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    await page.getByTestId("viewer-condition-filter-button").click();

    const popover = page.locator(".comp-popover");
    await expect(popover).toHaveCount(1);
    await expect(popover).toBeVisible();
  });
});
