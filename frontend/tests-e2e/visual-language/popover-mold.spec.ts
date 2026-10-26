/**
 * visual-language/popover-mold.spec.ts
 * — Popover 金型（宿題 C2）3欠陥修正の合否検査
 *
 * design: docs/handoff/popover-mold-fix/design.md 設計④・⑤ Acceptance Criteria C1・C4・C5・C8・C10（C9 は下の注記のとおり対象外）。
 *
 * Popover の実利用は MultiSelect（layout="popover" 既定）経由のみ。本番画面で popover が出るのは
 * 非モバイル幅のみ（InventoryToolbar.tsx:110 は isMobile で早期 return、閲覧ページ InventoryView.tsx は
 * PC 枝＝:597-598 の providerSelect/conditionSelect だけが既定 popover）。ログイン不要で開ける
 * 閲覧ページの PC 幅（768・1280）を使って検査する（gotoViewer）。
 *
 * 測り方の共通の決まり（design.md ⑤冒頭）: scrollIntoView は使わない。開いているパネルは
 * .comp-popover で取り、count を 1 で assert して曖昧さを消す（閉じているパネルは DOM に無い）。
 *
 * playwright.config.ts の testMatch が visual-language/ 配下に限るため、このファイルを
 * tests-e2e/ 直下に置くと CI で1本も走らない（既存 spec 群・viewer-header-remove.spec.ts と同じ注意）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer } from "./viewer-helpers";

/** トリガーとパネルの間隔（Popover.tsx の gap=6）の許容誤差（design.md ③） */
const GAP_PX = 6;
const GAP_TOLERANCE = 2;
/** 画面端との最低間隔（design.md 4-2・ContextMenu.tsx と同値） */
const EDGE_MARGIN = 8;
/** PC の一覧パネル幅の下限（A18 と同じ不変条件。design.md ⑤ C10） */
const MIN_PANEL_WIDTH = 400;

/** 提供者の絞り込みボタンを押して開いた .comp-popover を返す（1件であることを確認済み） */
async function openProviderPopover(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-provider-filter-button").click();
  const popover = page.locator(".comp-popover");
  await expect(popover).toHaveCount(1);
  await expect(popover).toBeVisible();
  return popover;
}

async function expectNoPageOverflow(page: Page): Promise<void> {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
}

/** パネルが画面の中に収まっていること（design.md ③・C4・C8） */
async function expectWithinViewport(page: Page, popover: Locator): Promise<void> {
  const box = await popover.boundingBox();
  expect(box).not.toBeNull();
  const innerWidth = await page.evaluate(() => window.innerWidth);

  expect(box!.x).toBeGreaterThanOrEqual(EDGE_MARGIN);
  // +1 は端数の余裕（design.md の指示どおり）
  expect(box!.x + box!.width).toBeLessThanOrEqual(innerWidth - EDGE_MARGIN + 1);
  expect(box!.width).toBeLessThanOrEqual(innerWidth - EDGE_MARGIN * 2 + 1);

  await expectNoPageOverflow(page);
}

/**
 * 窓（ページ全体）を縦に動かせる状態にする。
 * 閲覧ページは DataTable の stickyHeader（DataTable.css:208-209 の max-height + overflow: auto・
 * トークンは tokens.css:530 の calc(100vh - 18rem)）で表の中だけがスクロールするため、
 * 既定では document の高さが画面を超えず window.scrollY が常に 0 になる
 * （2026-10-26 の CI run 40301919199 で B1 がこの前提で3幅とも赤になって判明）。
 * 検査用に body を高くして「窓が動く」状況だけを作る（製品の CSS は変えない）。
 */
async function makePageScrollable(page: Page): Promise<void> {
  await page.addStyleTag({ content: "body { min-height: 300vh; }" });
  await expect(async () => {
    const { scrollHeight, innerHeight } = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      innerHeight: window.innerHeight,
    }));
    expect(scrollHeight).toBeGreaterThan(innerHeight + 400);
  }).toPass();
}

test.describe("visual-language: Popover 金型（スクロール追従・画面内収め）", () => {
  test("B1（C1）スクロールしてから開くと押したボタンのすぐ下に出る", async ({ page }) => {
    // fixture（60行）は通常の高さ(900)では縦スクロールの余地が無いことがあるため、
    // viewport の高さを 500 に縮めて縦スクロールを作る（design.md の指示どおり）
    await gotoViewer(page, { width: 1280, height: 500 });
    // 閲覧ページは表の中だけがスクロールするため、窓自体も動く状況を別途作る（上の注記）
    await makePageScrollable(page);

    const button = page.getByTestId("viewer-provider-filter-button");
    const startBox = await button.boundingBox();
    expect(startBox).not.toBeNull();
    // ボタンが画面の中に残る範囲で最大まで送る。画面の上へ外すと click 前に Playwright が
    // 自動で画面内へ戻すため、測った基準だけが古くなる（CI job 121523200091 で gap=406 になった）
    const delta = Math.floor(startBox!.y) - EDGE_MARGIN * 2;
    expect(delta).toBeGreaterThanOrEqual(60); // これ未満だと「送ってから開く」を試せていない
    await page.evaluate((d) => window.scrollBy(0, d), delta);
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThanOrEqual(delta - 2);

    const popover = await openProviderPopover(page);
    // 基準はパネルを開いたあとに測り直す（クリックで画面が動いても食い違わないように）
    const buttonBox = await button.boundingBox();
    expect(buttonBox).not.toBeNull();
    const popoverBox = await popover.boundingBox();
    expect(popoverBox).not.toBeNull();
    // click が画面内へ自動で戻していないこと（戻っていると↑の buttonBox が古い基準のままになる）
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThanOrEqual(delta - 2);

    const gap = popoverBox!.y - (buttonBox!.y + buttonBox!.height);
    // 直す前の実装なら gap は 6 + delta になるので、この検査は直す前なら赤（RED-first は保たれる）
    expect(gap).toBeGreaterThanOrEqual(GAP_PX - GAP_TOLERANCE);
    expect(gap).toBeLessThanOrEqual(GAP_PX + GAP_TOLERANCE);
  });

  test("B2（C5）開いたまま動かすと付いてくる", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });
    // 窓が動かないと、ボタンもパネルも動かず gap が変わらないまま空振りで緑になる（上の注記）
    await makePageScrollable(page);

    const button = page.getByTestId("viewer-provider-filter-button");
    const popover = await openProviderPopover(page);

    const beforeBox = await button.boundingBox();
    expect(beforeBox).not.toBeNull();
    // ボタンが画面の中に残る範囲で最大まで送る。画面の外まで送ると、画面内へ収める処理
    // （Popover.tsx の top = Math.max(margin, top)）が働いて gap が 6 でなくなる
    // （C-out・既知。CI job 121523200091 で gap=76.8 になった）。だからボタンが画面に
    // 残る範囲で送る。
    const delta = Math.floor(beforeBox!.y) - EDGE_MARGIN * 2;
    expect(delta).toBeGreaterThanOrEqual(60); // これ未満だと「動かす」を試せていない
    await page.evaluate((d) => window.scrollBy(0, d), delta);

    // scroll イベントの測り直し（Popover.tsx の measure()）が反映されるまで待つ
    // （固定時間の waitForTimeout は使わない。design.md の指示どおり toPass を使う）
    await expect(async () => {
      const afterBox = await button.boundingBox();
      const popoverBox = await popover.boundingBox();
      expect(afterBox).not.toBeNull();
      expect(popoverBox).not.toBeNull();
      const gap = popoverBox!.y - (afterBox!.y + afterBox!.height);
      expect(gap).toBeGreaterThanOrEqual(GAP_PX - GAP_TOLERANCE);
      expect(gap).toBeLessThanOrEqual(GAP_PX + GAP_TOLERANCE);
      // 空振りで緑にならないこと：窓が動いた分だけボタンも実際に画面内で上へ動いていること
      expect(beforeBox!.y - afterBox!.y).toBeGreaterThanOrEqual(delta - 2);
    }).toPass();
  });

  test("B3（C10）PC で今までどおりの位置", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    const button = page.getByTestId("viewer-provider-filter-button");
    const buttonBox = await button.boundingBox();
    expect(buttonBox).not.toBeNull();

    const popover = await openProviderPopover(page);
    const popoverBox = await popover.boundingBox();
    expect(popoverBox).not.toBeNull();

    const gap = popoverBox!.y - (buttonBox!.y + buttonBox!.height);
    expect(gap).toBeGreaterThanOrEqual(GAP_PX - GAP_TOLERANCE);
    expect(gap).toBeLessThanOrEqual(GAP_PX + GAP_TOLERANCE);

    // 横位置は design.md 4-2 の式どおり＝「ボタンの横中央そろえ」を画面内へ寄せた値。
    // ボタンが画面の左寄りにあって中央そろえだと左端 8px を割る場合は 8px に寄る（寄せが効く）。
    // どちらの場合も1つの式で表せるので、式のまま突き合わせる（中央そろえだけを assert すると
    // 寄せが効く位置にボタンが来たときに「正しいのに赤」になる）。
    const innerWidth = await page.evaluate(() => window.innerWidth);
    const buttonCenterX = buttonBox!.x + buttonBox!.width / 2;
    const centered = buttonCenterX - popoverBox!.width / 2;
    const expectedLeft = Math.max(
      EDGE_MARGIN,
      Math.min(centered, innerWidth - popoverBox!.width - EDGE_MARGIN),
    );
    expect(Math.abs(popoverBox!.x - expectedLeft)).toBeLessThanOrEqual(2);
  });

  test("B4（C4・C8）画面の中に収まる（1280px）", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });
    const popover = await openProviderPopover(page);
    await expectWithinViewport(page, popover);
  });

  test("B4（C4・C8）画面の中に収まる（768px）", async ({ page }) => {
    await gotoViewer(page, { width: 768, height: 900 });
    const popover = await openProviderPopover(page);
    await expectWithinViewport(page, popover);
  });

  /**
   * B5（C9）は削除した。
   * design.md ⑤ C9 は「選択肢1行44px以上（ADR-140・不変）」と書いていたが、
   * 現物の CSS では 44px（--size-icon-btn-lg）が付いているのは
   * .comp-multiselect__option--inline（MultiSelect.css:42-45）と空文言（:77）だけで、
   * popover 層の .comp-multiselect__option（:28-36）には min-height が無い
   * （便1 の実測も30px）。本便は位置と幅しか触っていないので 44px を新たに
   * 要求すると「直していない所を検査で赤にする」ことになる。
   * design.md ⑫ C-tap として起票し、この便では測らない。
   */
  test("B6 既存の形が変わっていないこと（パネル幅400px以上・PC）", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });
    const popover = await openProviderPopover(page);

    const box = await popover.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(MIN_PANEL_WIDTH);
  });
});
