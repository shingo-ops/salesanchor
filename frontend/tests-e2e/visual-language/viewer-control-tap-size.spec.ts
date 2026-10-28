/**
 * visual-language/viewer-control-tap-size.spec.ts
 * — 閲覧ページ（/viewer/）検索欄とプルダウンをお手本の48dpにそろえる（便10）の合否検査
 *
 * design: docs/handoff/viewer-control-tap-size/design.md 設計⑤ Acceptance Criteria B1〜B9。
 * recon: docs/handoff/viewer-control-tap-size/recon.md（お手本の実測値・横幅の算数）。
 *
 * 操作ボタン3つ（シリーズ・並び替え・絞り込み）と検索欄・「決定する」をお手本（メルカリ）と同じ
 * 高さ48px・文字13.6pxにそろえ、山形を16pxにしてシリーズ名が切れないようにする便の検査。
 * PC（767px超）は1px も動かさない（B4b で固定）。
 *
 * B10（閲覧ページ JS 300KB 以下）は CI の check-viewer-bundle.js が測るためここでは測らない。
 * B11（既存 viewer-inventory-mobile-filter.spec.ts の A5・A6・A15）はそのファイルを変更せず
 * 緑のままであることを確認するだけなので、ここにも書かない。
 * 一覧の先頭カードの y の上限（design.md ⑤ B9）は既存3本（viewer-top-compact.spec.ts・
 * viewer-choice-sheet.spec.ts・viewer-header-remove.spec.ts）の MAX_TOP_Y を128→132に更新して
 * 満たしているため、このファイルでは測らない。
 *
 * 幅は spec 側で明示する: 360px・390px の両方（B4b だけ PC=1280px）。
 * 測り方の共通の決まり（design.md ⑤冒頭）: scrollIntoView を使わずに測る（流用すると常に真になる）。
 * 測る前に「要素が存在する」ことを toBeVisible で確かめてから測る（空振り防止）。
 *
 * locator の注意（design ⑤・recon §5）: B7a・B7b・B7c・B7d は必ず viewer-tab-select の配下の
 * .viewer-toolbar__label に限る。.viewer-toolbar__label は並び替え側にもあり、そちらは
 * flex: 0 0 auto で絶対に切れないため .first() 等を使うと常に緑になる空振りが起きる。
 *
 * playwright.config.ts の testMatch が visual-language/ 配下に限るため、
 * このファイルを tests-e2e/ 直下に置くと CI で1本も走らない（design ⑪の注意と同じ）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer, waitPanelSlidIn as waitFilterPanelSlidIn } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** B4b: PC 幅（design.md ⑤。PC は1px も動かさない固定） */
const PC_WIDTH = 1280;
/** B1・B4・B5・B6: お手本（メルカリ）の操作単位（design.md ③ P1/P4/P5/P6） */
const TAP_HEIGHT_PX = 48;
/** B2: 操作ボタンの文字（design.md ③ P2。recon §1 の逆算） */
const TAP_FONT_SIZE = "13.6px";
/** B3: 山形の幅（design.md ③ P3） */
const CARET_WIDTH_PX = 16;
/** B4b: PC では検索欄に field-h-md（36px）が効いたまま＝スマホ限定の field-h-tap は適用されない（design.md 4-3） */
const PC_SEARCH_MIN_HEIGHT = "36px";
/** B7b: シリーズのラベル枠の下限（1文字分。design.md ⑤） */
const MIN_SERIES_LABEL_WIDTH_PX = 13.6;

async function expectNoPageOverflow(page: Page): Promise<void> {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
}

/** 絞り込みドロワーを開き、スライドが収まるまで待つ（既存 spec と同じ作り） */
async function openFilterDrawer(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-filter-toggle").click();
  const panel = page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
  await waitFilterPanelSlidIn(panel, page);
  return panel;
}

/** シリーズ/並び替えの選択パネル（supplier-drawer を共有するため .comp-drawer-panel--open で絞る） */
function openPanel(page: Page): Locator {
  return page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
}

async function waitPanelSlidIn(panel: Locator): Promise<void> {
  await expect(panel).toHaveCount(1);
  await expect(panel).toBeVisible();
  await expect
    .poll(async () => {
      const box = await panel.boundingBox();
      return box ? Math.round(box.x) : null;
    })
    .toBe(0);
}

/** 高さちょうど・文字ちょうどを測る対象（design.md ⑤ B1・B2） */
const OPERATION_BUTTON_TESTIDS = ["viewer-tab-select", "viewer-sort-menu", "viewer-filter-toggle"] as const;

for (const width of MOBILE_WIDTHS) {
  const height = 700;
  test.describe(`visual-language: 閲覧ページ 検索欄とプルダウンの大きさ ${width}px`, () => {
    test("B1: 操作ボタン3つの高さが48pxちょうど", async ({ page }) => {
      await gotoViewer(page, { width, height });
      for (const testId of OPERATION_BUTTON_TESTIDS) {
        const button = page.getByTestId(testId);
        await expect(button).toBeVisible();
        const box = await button.boundingBox();
        expect(box).not.toBeNull();
        expect(box!.height).toBe(TAP_HEIGHT_PX);
      }
    });

    test("B2: 操作ボタン3つの文字が13.6px", async ({ page }) => {
      await gotoViewer(page, { width, height });
      for (const testId of OPERATION_BUTTON_TESTIDS) {
        const button = page.getByTestId(testId);
        await expect(button).toBeVisible();
        const fontSize = await button.evaluate((el) => getComputedStyle(el).fontSize);
        expect(fontSize).toBe(TAP_FONT_SIZE);
      }
    });

    test("B3: 山形2つの幅が16px", async ({ page }) => {
      await gotoViewer(page, { width, height });
      for (const testId of ["viewer-tab-select", "viewer-sort-menu"] as const) {
        const caret = page.getByTestId(testId).locator(".viewer-toolbar__caret");
        await expect(caret).toBeVisible();
        const box = await caret.boundingBox();
        expect(box).not.toBeNull();
        expect(box!.width).toBe(CARET_WIDTH_PX);
      }
    });

    test("B4: 上部の検索欄の高さが48pxちょうど", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const search = page.getByTestId("viewer-search");
      await expect(search).toBeVisible();
      const box = await search.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBe(TAP_HEIGHT_PX);
    });

    test("B5: パネル内の候補を絞る検索欄の高さが48px", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);
      await panel.getByTestId("viewer-provider-row").click();

      const search = panel.getByTestId("viewer-filter-option-search");
      await expect(search).toBeVisible();
      const box = await search.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBe(TAP_HEIGHT_PX);
    });

    test("B6: 「決定する」の高さが48px", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);
      await panel.getByTestId("viewer-provider-row").click();

      const apply = panel.getByTestId("viewer-filter-apply");
      await expect(apply).toBeVisible();
      const box = await apply.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBe(TAP_HEIGHT_PX);
    });

    test("B7a: 既定の表示でシリーズ名が切れていない", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const label = page.getByTestId("viewer-tab-select").locator(".viewer-toolbar__label");
      await expect(label).toBeVisible();
      const { scrollWidth, clientWidth } = await label.evaluate((el) => ({
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
      }));
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
    });

    test("B7b: 並び替えに最長の項目を選んだ後も、シリーズのラベル枠が1文字分以上", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const trigger = page.getByTestId("viewer-sort-menu");
      await trigger.click();
      const panel = openPanel(page);
      await waitPanelSlidIn(panel);
      // 最長は quantity:desc（「在庫が多い順」6字。recon §4・design.md ⑤B7b）
      await panel.getByTestId("viewer-sort-option-quantity:desc").click();
      await expect(openPanel(page)).toHaveCount(0);

      const label = page.getByTestId("viewer-tab-select").locator(".viewer-toolbar__label");
      await expect(label).toBeVisible();
      const box = await label.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeGreaterThanOrEqual(MIN_SERIES_LABEL_WIDTH_PX);
    });

    test("B8: 3つの高さ・配置（y が同じ・右端が画面幅以内・ページの横はみ出し無し）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const series = page.getByTestId("viewer-tab-select");
      const sort = page.getByTestId("viewer-sort-menu");
      const filter = page.getByTestId("viewer-filter-toggle");
      await expect(series).toBeVisible();
      await expect(sort).toBeVisible();
      await expect(filter).toBeVisible();

      const [seriesBox, sortBox, filterBox] = await Promise.all([
        series.boundingBox(),
        sort.boundingBox(),
        filter.boundingBox(),
      ]);
      expect(seriesBox).not.toBeNull();
      expect(sortBox).not.toBeNull();
      expect(filterBox).not.toBeNull();

      expect(seriesBox!.y).toBe(sortBox!.y);
      expect(sortBox!.y).toBe(filterBox!.y);

      for (const box of [seriesBox!, sortBox!, filterBox!]) {
        expect(box.x + box.width).toBeLessThanOrEqual(width);
      }

      await expectNoPageOverflow(page);
    });
  });
}

// B7c・B7d は「壊した状態を作って切れることを検出できる」ことを示す（design.md ⑤。
// 便6〜便9 で3便連続で B7a 相当の検査が空振りだったため、本便はここで証明する）。
// 360px だけでよい（recon §4: 390px では採用案の余りが38pxあり、どちらを壊しても切れない）。
test.describe("visual-language: 閲覧ページ シリーズ名が切れることの検出（空振り対策）360px", () => {
  const width = 360;
  const height = 700;

  test("B7c: 操作ボタンの文字を16pxに差し替えると、シリーズ名が切れる", async ({ page }) => {
    await gotoViewer(page, { width, height });
    await page.addStyleTag({ content: '[data-testid="viewer-tab-select"], [data-testid="viewer-sort-menu"], [data-testid="viewer-filter-toggle"] { font-size: 16px !important; }' });

    const label = page.getByTestId("viewer-tab-select").locator(".viewer-toolbar__label");
    await expect(label).toBeVisible();
    const { scrollWidth, clientWidth } = await label.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(scrollWidth).toBeGreaterThan(clientWidth);
  });

  test("B7d: 山形を24pxに差し替えると、シリーズ名が切れる", async ({ page }) => {
    await gotoViewer(page, { width, height });
    await page.addStyleTag({ content: ".viewer-toolbar__caret { width: 24px !important; height: 24px !important; }" });

    const label = page.getByTestId("viewer-tab-select").locator(".viewer-toolbar__label");
    await expect(label).toBeVisible();
    const { scrollWidth, clientWidth } = await label.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(scrollWidth).toBeGreaterThan(clientWidth);
  });
});

test.describe("visual-language: 閲覧ページ PC は検索欄の高さが不変", () => {
  test(`B4b: PC幅（${PC_WIDTH}px）では上部の検索欄に field-h-tap が効かない`, async ({ page }) => {
    await gotoViewer(page, { width: PC_WIDTH, height: 800 });
    const search = page.getByTestId("viewer-search");
    await expect(search).toBeVisible();
    // 「どちらの規則が勝ったか」を min-height で測る。実際の高さは中身
    // （文字 var(--font-base) 14.4px × var(--line-height-base) 1.5 ＋ 余白 var(--space-2) 8px ×2 ＋ 枠 1px ×2 ＝ 39.6px）が
    // min-height 36px を上回るので 39.6px になり、「36px ちょうど」では赤になる（FormField.css の .comp-field__input）。
    const minHeight = await search.evaluate((el) => getComputedStyle(el).minHeight);
    expect(minHeight).toBe(PC_SEARCH_MIN_HEIGHT);
    // 48px（スマホの段）になっていないことも確かめる
    const box = await search.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeLessThan(TAP_HEIGHT_PX);
  });
});
