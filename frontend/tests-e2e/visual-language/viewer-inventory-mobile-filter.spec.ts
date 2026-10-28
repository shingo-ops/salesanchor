/**
 * visual-language/viewer-inventory-mobile-filter.spec.ts
 * — 閲覧ページ（/viewer/）スマホ絞り込み副画面の合否検査
 *
 * design: docs/handoff/viewer-filter-subscreen/design.md 設計⑤ Acceptance Criteria A1〜A18。
 * recon: docs/handoff/viewer-filter-subscreen/recon.md（実機の実測値）。
 *
 * 便1（docs/handoff/viewer-inventory-mobile-filter/design.md）で「その場に全部並べる」形にしたところ、
 * コンディションに辿り着くまでに提供者42件ぶんのスクロールが要る不具合が残った（PO「使いづらい」）。
 * 本便はメルカリと同じ「項目をタップ→次の画面で選ぶ」形に変える。この spec は旧 A4〜A13 を全面書き換え。
 *
 * 幅は spec 側で明示する: 360px・390px の両方（recon の実機実測は360、project 既定の vl-mobile-390 は390。
 * 両方測らないと片方だけ収まる場合を見逃す）。A18 のみ PC（1280px）。
 *
 * 測り方の共通の決まり（design.md ⑤ 冒頭）: A1・A4・A6 は scrollIntoView を使わずに測る
 * （流用すると常に真になる）。「見えている」は boundingBox() が 0 <= y かつ y + height <= innerHeight。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer, waitPanelSlidIn } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** タップ領域の下限（ADR-140 の G4 と同じ測り方。design.md ③） */
const MIN_TAP_PX = 44;
/** A6: 選択画面で一度に見える件数（下限・上限。design.md ③・⑤）。
 *  便13a（docs/handoff/viewer-filter-choices-mercari/design.md C11）で行の高さを44px→61pxに
 *  したぶん見える件数が約28%減るため下限を引き下げる: 8 × 44/61 = 5.77 → 5 */
const MIN_VISIBLE_OPTIONS = 5;
const MAX_VISIBLE_OPTIONS = 20;

/**
 * 絞り込みボタンを押してドロワーを開き、スライドの transition（--transition-slow）が
 * 収まるまで待つ。同じ data-testid（supplier-drawer）を持つ要素が複数存在しうるため
 * `.comp-drawer-panel--open` で絞る（design.md 4-4b・PR #4602 の strict mode violation の教訓）。
 */
async function openFilterDrawer(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-filter-toggle").click();
  const panel = page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
  await waitPanelSlidIn(panel, page);
  return panel;
}

/** 要素そのものの bounding box（layout="row" の <button> や drawer-back など、label に包まれない要素用） */
async function elementBox(locator: Locator): Promise<{ x: number; y: number; width: number; height: number } | null> {
  return locator.boundingBox();
}

/** 選択画面（layout="inline"）のチェック欄 data-testid から、行全体（<label>）の bounding box を取る。無ければ null。 */
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

/** `0 <= y` かつ `y + height <= innerHeight`（design.md ⑤ 冒頭の「見えている」の定義。scrollIntoView は使わない） */
function isFullyVisible(box: { y: number; height: number }, innerHeight: number): boolean {
  return box.y >= 0 && box.y + box.height <= innerHeight;
}

/** 選択画面でスクロールせずに見える行の数（A6）。label-wrap のチェック欄 testid 接頭辞から数える */
async function countVisibleOptionRows(panel: Locator, optionTestIdPrefix: string, innerHeight: number): Promise<number> {
  const checkboxes = panel.locator(`[data-testid^="${optionTestIdPrefix}-option-"]`);
  const n = await checkboxes.count();
  let visible = 0;
  for (let i = 0; i < n; i++) {
    const box = await checkboxes.nth(i).evaluate((el) => {
      const label = el.closest("label");
      if (!label) return null;
      const r = label.getBoundingClientRect();
      return { y: r.y, height: r.height };
    });
    if (box && box.y >= 0 && box.y + box.height <= innerHeight) visible++;
  }
  return visible;
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

/** A15: 浮かぶパネル（Popover）を document 全体で使っていないこと */
async function expectNoFloatingPopover(page: Page): Promise<void> {
  expect(await page.locator(".comp-popover").count()).toBe(0);
}

for (const width of MOBILE_WIDTHS) {
  const height = 700;
  test.describe(`visual-language: 閲覧ページ 絞り込み副画面 ${width}px`, () => {
    test("A1: 最初の画面（root）に4項目が収まる（スクロールせずに測る）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      // 押す前は drawer-back が無い（A2 の前半）
      await expect(panel.getByTestId("drawer-back")).toHaveCount(0);

      // 「数量の範囲」下限欄の下端が innerHeight 以内（scrollIntoView は使わない）
      const box = await elementBox(panel.getByTestId("viewer-qty-max"));
      expect(box).not.toBeNull();
      expect(box!.y + box!.height).toBeLessThanOrEqual(height);

      await expectNoPageOverflow(page);
    });

    test("A2・A3・A14: 提供者の行を押すと選択画面になり、← で root に戻る。フォーカスも往復する", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      await panel.getByTestId("viewer-provider-row").click();
      const back = panel.getByTestId("drawer-back");
      await expect(back).toBeVisible();
      // A14: 画面が変わった直後のフォーカスが「←」にある
      await expect(back).toBeFocused();

      await back.click();
      await expect(panel.getByTestId("drawer-back")).toHaveCount(0);
      // A3: 題が「絞り込み」に戻る
      await expect(panel.locator(".comp-drawer-title")).toHaveText("絞り込み");
      // A14: root に戻ったら元の行にフォーカスが戻る
      await expect(panel.getByTestId("viewer-provider-row")).toBeFocused();
    });

    test("A4: コンディションの行がスクロールせずに画面内にある（便1 は 2024 だった）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const box = await elementBox(panel.getByTestId("viewer-condition-row"));
      expect(box).not.toBeNull();
      expect(box!.y).toBeGreaterThanOrEqual(0);
      expect(box!.y + box!.height).toBeLessThanOrEqual(height);
    });

    test("A5・A6・A15: 選択画面の行が44px以上・画面内に収まり、8〜20件見える。浮かぶパネルは0件", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      // A15: ドロワーが開いている間、document 全体で .comp-popover が 0 件
      await expectNoFloatingPopover(page);

      await panel.getByTestId("viewer-provider-row").click();
      const firstOptionId = `viewer-provider-options-option-${fixture.providers[0]}`;
      await expect(panel.getByTestId(firstOptionId)).toBeVisible();

      // A5: 選択画面の行の高さが44px以上・x>=0 かつ x+width<=innerWidth
      const box = await optionRowBox(panel, firstOptionId);
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);

      // A6: スクロールせずに見える行が8件以上・20件以下（上限も見る）
      const visibleCount = await countVisibleOptionRows(panel, "viewer-provider-options", height);
      expect(visibleCount).toBeGreaterThanOrEqual(MIN_VISIBLE_OPTIONS);
      expect(visibleCount).toBeLessThanOrEqual(MAX_VISIBLE_OPTIONS);

      // 選んでいる間も浮かぶパネルは使わない
      await expectNoFloatingPopover(page);
      await expectNoPageOverflow(page);
    });

    test("A7・A9: 2件選ぶと一覧が絞られ、親の行に選んだ名前が出る（検索で絞っている間も生の値に化けない）", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());

      await panel.getByTestId("viewer-provider-row").click();
      const [p0, p1] = fixture.providers;
      await panel.getByTestId(`viewer-provider-options-option-${p0}`).click();
      await panel.getByTestId(`viewer-provider-options-option-${p1}`).click();

      // A9: 検索で候補を絞っている間も選択済みの名前は生の値に化けない（ここでは要約表示で確認）。
      // 実際は value と label が同じ文字列（viewer-helpers.ts の makeProviderNames）のため、
      // この spec 単独では退行を観測できない。実際の守り手は frontend/src/components/MultiSelect.test.tsx
      // （design.md ⑤ A9・⑪）
      await panel.getByTestId("viewer-filter-option-search").fill(p1);
      await expect(panel.getByTestId(`viewer-provider-options-option-${p0}`)).toHaveCount(0);
      const summary = panel.locator(".comp-multiselect__inline-summary");
      await expect(summary).toHaveText(`${p0}, ${p1}`);

      // root に戻って親の行で確認（検索欄は離れると空に戻る＝A17）
      await panel.getByTestId("drawer-back").click();
      await expect(panel.getByTestId("viewer-provider-row")).toHaveText(new RegExp(`${p0}, ${p1}`));

      const after = extractRowCount(await pageInfo.textContent());
      expect(after).toBeLessThan(before);
    });

    test("A8・A10・A17: 検索欄で候補を絞れる・0件表示・画面を離れると空に戻る", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      await panel.getByTestId("viewer-provider-row").click();
      const search = panel.getByTestId("viewer-filter-option-search");

      const totalBefore = await panel.locator('[data-testid^="viewer-provider-options-option-"]').count();
      expect(totalBefore).toBe(fixture.providers.length);

      // A8: 文字を入れると候補が絞られる
      await search.fill(fixture.providers[0]);
      const narrowed = await panel.locator('[data-testid^="viewer-provider-options-option-"]').count();
      expect(narrowed).toBeLessThan(totalBefore);

      // 消すと件数が元に戻る
      await search.fill("");
      const restored = await panel.locator('[data-testid^="viewer-provider-options-option-"]').count();
      expect(restored).toBe(totalBefore);

      // A10: 候補が0件になる語を入れると noOptions の文字が出る
      await search.fill("no-such-provider-xyz");
      await expect(panel.getByText("見つかりません")).toBeVisible();

      // A17: ← で画面を離れると検索欄が空に戻る
      await panel.getByTestId("drawer-back").click();
      await panel.getByTestId("viewer-provider-row").click();
      await expect(panel.getByTestId("viewer-filter-option-search")).toHaveValue("");
    });

    test("A11: 「決定する」を押すと最初の画面に戻り、選択は残っている", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());

      await panel.getByTestId("viewer-provider-row").click();
      await panel.getByTestId(`viewer-provider-options-option-${fixture.providers[0]}`).click();
      await panel.getByTestId("viewer-filter-apply").click();

      await expect(panel.getByTestId("drawer-back")).toHaveCount(0);
      await expect(panel.locator(".comp-drawer-title")).toHaveText("絞り込み");
      await expect(panel.getByTestId("viewer-provider-row")).toHaveText(new RegExp(fixture.providers[0]));

      const after = extractRowCount(await pageInfo.textContent());
      expect(after).toBeLessThan(before);
    });

    test("A12・A13: Esc で root に戻る（ドロワーは閉じない）。Tab / Shift+Tab は端で回り込む", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      await panel.getByTestId("viewer-provider-row").click();
      const back = panel.getByTestId("drawer-back");
      await expect(back).toBeVisible();

      // A13: 選択画面に入った直後は先頭（←）にフォーカスがある。Tab を10回押すだけでは
      // 端に届かず空振りする（候補25件＋←／✕／検索欄／選択をクリア／決定する＝約30個）ため、
      // 端の回り込みを直接測る（design.md ⑤・審査指摘「A13が空振り」の修正4）。
      await expect(back).toBeFocused();
      // 先頭で Shift+Tab を押すと末尾（決定する）に回り込む
      await page.keyboard.press("Shift+Tab");
      await expect(panel.getByTestId("viewer-filter-apply")).toBeFocused();
      // 逆向き: 末尾で Tab を押すと先頭（←）に回り込む
      await page.keyboard.press("Tab");
      await expect(back).toBeFocused();

      // A12: Esc で root に戻る。ドロワー自体は閉じない
      await page.keyboard.press("Escape");
      await expect(panel.getByTestId("drawer-back")).toHaveCount(0);
      await expect(page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open')).toHaveCount(1);
    });

    test("A17: 選択画面のまま ✕ を押すとドロワーが閉じる。開き直すと最初の画面に戻り、検索欄が空になっている", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      await panel.getByTestId("viewer-provider-row").click();
      await panel.getByTestId("viewer-filter-option-search").fill("abc");

      // ✕ は onClose 固定（Esc・onEscape とは別経路）のため、選択画面のままでも1回で閉じる
      // （修正1: 以前は Esc と同じ関数で一段戻るだけだった＝名前「閉じる」と動作が食い違っていた）
      await panel.getByTestId("drawer-close").click();
      await expect(page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open')).toHaveCount(0);

      const reopened = await openFilterDrawer(page);
      await expect(reopened.getByTestId("drawer-back")).toHaveCount(0);
      await reopened.getByTestId("viewer-provider-row").click();
      await expect(reopened.getByTestId("viewer-filter-option-search")).toHaveValue("");
    });

    test("コンディションでも A5・A7 が成り立つ（本便の主眼である A4 は別テストで確認済み）", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());

      await panel.getByTestId("viewer-condition-row").click();
      const firstOptionId = `viewer-condition-options-option-${fixture.conditions[0]}`;
      await expect(panel.getByTestId(firstOptionId)).toBeVisible();

      const box = await optionRowBox(panel, firstOptionId);
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);

      await panel.getByTestId(firstOptionId).click();
      await panel.getByTestId("drawer-back").click();
      await expect(panel.getByTestId("viewer-condition-row")).toHaveText(new RegExp(fixture.conditions[0]));

      const after = extractRowCount(await pageInfo.textContent());
      // fixture は60行をコンディション2種類に均等配分（viewer-helpers.ts）なので、1種類を
      // 選べば必ず30件に減る。toBeLessThanOrEqual では絞り込みが全く効かなくても緑になる（修正5）
      expect(after).toBeLessThan(before);

      await expectNoPageOverflow(page);
    });
  });
}

test.describe("visual-language: 閲覧ページ PC(1280px) の絞り込み", () => {
  test("A18: PC は popover のまま。一覧の幅は400px以上", async ({ page }) => {
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

  test("A18: コンディションも PC では popover のまま", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    await page.getByTestId("viewer-condition-filter-button").click();

    const popover = page.locator(".comp-popover");
    await expect(popover).toHaveCount(1);
    await expect(popover).toBeVisible();
  });
});
