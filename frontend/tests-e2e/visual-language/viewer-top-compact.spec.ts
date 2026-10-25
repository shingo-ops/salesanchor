/**
 * visual-language/viewer-top-compact.spec.ts
 * — 閲覧ページ（/viewer/）スマホ上部コンパクト化（便3）の合否検査
 *
 * design: docs/handoff/viewer-top-compact/design.md 設計⑤ Acceptance Criteria A1〜A12。
 * recon: docs/handoff/viewer-top-compact/recon.md（実機の実測値）。
 *
 * 24時間以内の切り替えを上部から絞り込みドロワーの先頭へ移し、空いた場所にシリーズの選択を
 * 並び替えの左へ入れて「シリーズ／並び替え／絞り込み」を1行に並べる。
 *
 * 幅は spec 側で明示する: 360px・390px の両方（A12 のみ PC=1280px）。
 * 測り方の共通の決まり（design.md ⑤冒頭）: A1〜A4 は scrollIntoView を使わずに測る
 * （流用すると常に真になる）。
 *
 * playwright.config.ts の testMatch（:64・:69・:74）が visual-language/ 配下に限るため、
 * このファイルを tests-e2e/ 直下に置くと CI で1本も走らない（recon §6・design ⑪の注意と同じ）。
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { gotoViewer, installViewerMocks, makeConditionValues, makeProviderNames, makeViewerRows } from "./viewer-helpers";
import type { ViewerFixture } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** タップ領域の下限（ADR-140。design.md ③） */
const MIN_TAP_PX = 44;
/** 一覧の先頭カードの y の上限（design.md ③・K1。現状236px→192px以内） */
const MAX_TOP_Y = 192;
/** シリーズのタブに常時出る3つ（本便のテストでは意図的に外側のシリーズ名を使う。viewerFilter.ts の MAIN_SERIES） */
// eslint-disable-next-line local/no-japanese-literal -- tests-e2e は ESLint 対象外。DB の series 名（画面文言ではない）
const OTHER_SERIES = "アクア";

/** viewer.filter.pageOf（例:「1 / 2 ページ（全 60 件）」）から件数を取り出す（既存 spec と同じ方式） */
function extractRowCount(text: string | null): number {
  // eslint-disable-next-line local/no-japanese-literal -- tests-e2e は ESLint 対象外。画面文言の正規表現
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

/** 一覧の先頭カード（.comp-table__card）の y（scrollIntoView は使わない。design.md ⑤冒頭） */
async function firstCardY(page: Page): Promise<number> {
  const card = page.locator(".comp-table__card").first();
  await expect(card).toBeVisible();
  const box = await card.boundingBox();
  expect(box).not.toBeNull();
  return box!.y;
}

/** 絞り込みドロワーを開き、スライドが収まるまで待つ（便2 spec と同じ作り） */
async function openFilterDrawer(page: Page) {
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

/** シリーズに一部だけ MAIN_SERIES 外の値を振った fixture を直接作る（A10 用。ヘルパーの既定挙動は変えない） */
async function gotoViewerWithSeries(page: Page, width: number, height: number): Promise<ViewerFixture> {
  const providers = makeProviderNames(25);
  const conditions = makeConditionValues(2);
  const rows = makeViewerRows(60, providers, conditions).map((r, i) => ({
    ...r,
    series: i % 3 === 0 ? OTHER_SERIES : "",
  }));
  const fixture: ViewerFixture = {
    providers,
    conditions,
    response: { updated_at: new Date().toISOString(), fresh_window_hours: 24, rows },
  };
  await page.setViewportSize({ width, height });
  await installViewerMocks(page, fixture);
  await page.goto("/viewer/");
  await expect(page.getByTestId("viewer-filter-toggle").or(page.getByTestId("viewer-provider-filter-button"))).toBeVisible();
  return fixture;
}

for (const width of MOBILE_WIDTHS) {
  const height = 844;
  test.describe(`visual-language: 閲覧ページ 上部コンパクト化 ${width}px`, () => {
    test("A1: 一覧の先頭カードの y が192px以内", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const y = await firstCardY(page);
      expect(y).toBeLessThanOrEqual(MAX_TOP_Y);
    });

    test("A2・A3・A4: シリーズ・並び替え・絞り込みが1行に並び、検索欄は単独で1行", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const search = page.getByTestId("viewer-search");
      const series = page.getByTestId("viewer-tab-select");
      const sort = page.getByTestId("viewer-sort-menu");
      const filter = page.getByTestId("viewer-filter-toggle");

      const [searchBox, seriesBox, sortBox, filterBox] = await Promise.all([
        search.boundingBox(),
        series.boundingBox(),
        sort.boundingBox(),
        filter.boundingBox(),
      ]);
      expect(searchBox).not.toBeNull();
      expect(seriesBox).not.toBeNull();
      expect(sortBox).not.toBeNull();
      expect(filterBox).not.toBeNull();

      // A2: シリーズ・並び替え・絞り込みの y が同じ（1行に並ぶ）
      expect(seriesBox!.y).toBe(sortBox!.y);
      expect(sortBox!.y).toBe(filterBox!.y);

      // A4: 検索欄は単独の1行（シリーズと y が違う）
      expect(searchBox!.y).not.toBe(seriesBox!.y);

      // A3: 3つの右端が画面幅以内・高さが44px以上
      for (const box of [seriesBox!, sortBox!, filterBox!]) {
        expect(box.x + box.width).toBeLessThanOrEqual(width);
        expect(box.height).toBeGreaterThanOrEqual(MIN_TAP_PX);
      }

      await expectNoPageOverflow(page);
    });

    test("A5: スマホの上部に viewer-fresh-toggle が0件", async ({ page }) => {
      await gotoViewer(page, { width, height });
      await expect(page.getByTestId("viewer-fresh-toggle")).toHaveCount(0);
    });

    test("A6: 絞り込み画面の先頭に viewer-fresh-check があり、高さ44px以上", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);

      const check = panel.getByTestId("viewer-fresh-check");
      await expect(check).toBeVisible();
      const box = await check.evaluate((el) => {
        const label = el.closest("label");
        const r = (label ?? el).getBoundingClientRect();
        return { y: r.y, height: r.height };
      });
      expect(box.height).toBeGreaterThanOrEqual(MIN_TAP_PX);

      // 先頭（提供者の行より上）にあることを確認
      const providerBox = await panel.getByTestId("viewer-provider-row").boundingBox();
      expect(providerBox).not.toBeNull();
      expect(box.y).toBeLessThan(providerBox!.y);
    });

    test("A7: viewer-fresh-check を外すと一覧の件数が増える（24時間より古い行がある）", async ({ page }) => {
      await gotoViewer(page, { width, height, fixtureOpts: { staleRowCount: 5 } });
      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());

      const panel = await openFilterDrawer(page);
      const check = panel.getByTestId("viewer-fresh-check");
      // ちゃんと開いていて、既定でオンであることを先に確定させる（空振り検査を避ける）
      await expect(check).toBeChecked();
      await check.click();
      await expect(check).not.toBeChecked();

      const after = extractRowCount(await pageInfo.textContent());
      expect(after).toBeGreaterThan(before);
    });

    test("A8: 開いた直後は viewer-fresh-check がオン", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);
      await expect(panel.getByTestId("viewer-fresh-check")).toBeChecked();
    });

    test("A9: 絞り込みボタンの文字が既定で「(1)」を含み、すべて外すと含まない", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const filterButton = page.getByTestId("viewer-filter-toggle");
      await expect(filterButton).toHaveText(/\(1\)/);

      const panel = await openFilterDrawer(page);
      const check = panel.getByTestId("viewer-fresh-check");
      await expect(check).toBeChecked();
      await check.click();
      await expect(check).not.toBeChecked();

      await expect(filterButton).not.toHaveText(/\(1\)/);
      await expect(filterButton).not.toHaveText(/\(\d+\)/);
    });

    test("A10: シリーズを選ぶと一覧の件数が変わる", async ({ page }) => {
      await gotoViewerWithSeries(page, width, height);
      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());

      await page.getByTestId("viewer-tab-select").selectOption(OTHER_SERIES);

      const after = extractRowCount(await pageInfo.textContent());
      expect(after).toBeLessThan(before);
    });

    test("A11: 横はみ出しが0", async ({ page }) => {
      await gotoViewer(page, { width, height });
      await expectNoPageOverflow(page);
    });
  });
}

test.describe("visual-language: 閲覧ページ 上部コンパクト化 PC(1280px)", () => {
  test("A12: PCは今のまま（上部に viewer-fresh-toggle が居る・タブが出る・シリーズ選択は無い）", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    await expect(page.getByTestId("viewer-fresh-toggle")).toBeVisible();
    await expect(page.getByRole("tablist")).toBeVisible();
    await expect(page.getByTestId("viewer-tab-select")).toHaveCount(0);
  });
});
