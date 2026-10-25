/**
 * visual-language/viewer-choice-sheet.spec.ts
 * — 閲覧ページ（/viewer/）「シリーズ」「並び替え」を枠なしボタン＋パネル選択にする（便5）の合否検査
 *
 * design: docs/handoff/viewer-choice-sheet/design.md 設計⑤ Acceptance Criteria B1〜B13。
 * recon: docs/handoff/viewer-choice-sheet/recon.md。
 *
 * メルカリと同じ「押す前は枠なしの文字ボタン → 押すと右からパネルが出て1つ選ぶ」形に変える便。
 * 並び替え・シリーズの絞り込みドロワー（便2・便3）には触らない（別の Drawer インスタンス）。
 *
 * 幅は spec 側で明示する: 360px・390px の両方（B13 のみ PC=1280px）。
 * 測り方の共通の決まり（design.md ⑤冒頭）: scrollIntoView を使わずに測る（流用すると常に真になる）。
 * パネルを開く前に「開いていないこと」、選ぶ前に「選ばれていないこと」を先に確かめてから操作する。
 *
 * playwright.config.ts の testMatch（:64・:69・:74）が visual-language/ 配下に限るため、
 * このファイルを tests-e2e/ 直下に置くと CI で1本も走らない（design ⑪の注意と同じ）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer, installViewerMocks, makeConditionValues, makeProviderNames, makeViewerRows } from "./viewer-helpers";
import type { ViewerFixture } from "./viewer-helpers";
import type { ViewerRow } from "../../src/pages/viewer/types";

const MOBILE_WIDTHS = [360, 390] as const;
/** タップ領域の下限（ADR-140。design.md ③） */
const MIN_TAP_PX = 44;
/** B5: パネルで一度に見える行数の下限（design.md ③） */
const MIN_VISIBLE_ROWS = 8;
/** 一覧の先頭カードの y の上限（design.md ③・便3 の値を維持） */
const MAX_TOP_Y = 192;

// eslint-disable-next-line local/no-japanese-literal -- tests-e2e は ESLint 対象外。DB の series 名（画面文言ではない）に見せかけた fixture 専用の名前
const SERIES_NAMES = Array.from({ length: 15 }, (_, i) => `しりーず${String(i + 1).padStart(2, "0")}`);

/** 現在時刻を posted_at の形（タイムゾーン無しの日本時間 'YYYY-MM-DD HH:MM:SS'）にする（viewer-helpers.ts の非公開版と同じ） */
function jstNow(): string {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 19).replace("T", " ");
}

/** シリーズを15件に振った fixture（B5「8行以上見える」を確かめるのに十分な数・design.md ③） */
async function gotoViewerWithSeries(page: Page, width: number, height: number): Promise<void> {
  const providers = makeProviderNames(5);
  const conditions = makeConditionValues(2);
  const base = makeViewerRows(SERIES_NAMES.length, providers, conditions);
  const rows = base.map((r, i) => ({ ...r, series: SERIES_NAMES[i] }));
  const fixture: ViewerFixture = {
    providers,
    conditions,
    response: { updated_at: new Date().toISOString(), fresh_window_hours: 24, rows },
  };
  await page.setViewportSize({ width, height });
  await installViewerMocks(page, fixture);
  await page.goto("/viewer/");
  await expect(page.getByTestId("viewer-tab-select")).toBeVisible();
}

/**
 * 並び替えが実際に効くことを見るための専用 fixture（design.md 4-2・4-3）。
 * 同じ商品・同じ状態（release_date・english_title・japanese_title・condition が同じ）の2行を、
 * 単価だけ逆にして用意する（viewerFilter.ts の sortRows は「まとまりの中」でしか選んだ列を見ないため、
 * 同じまとまりの行が無いと並び替えの効果が見えない）。
 */
async function gotoViewerForSort(page: Page, width: number, height: number): Promise<void> {
  const common = {
    posted_at: jstNow(),
    japanese_title: "",
    // eslint-disable-next-line local/no-japanese-literal -- tests-e2e は ESLint 対象外
    english_title: "並び替えfixture商品",
    condition: "sealed",
    release_date: "",
    note_ja: "",
    status: "In Stock",
    series: "",
    provider: "P1",
    search_keywords: "",
    ship_ja: "",
    offer_type: "in_stock" as const,
  };
  const rows: ViewerRow[] = [
    { ...common, mark: "HIGH", unit_price: "900", quantity: "1" },
    { ...common, mark: "LOW", unit_price: "100", quantity: "5" },
  ];
  const fixture: ViewerFixture = {
    providers: ["P1"],
    conditions: ["sealed"],
    response: { updated_at: new Date().toISOString(), fresh_window_hours: 24, rows },
  };
  await page.setViewportSize({ width, height });
  await installViewerMocks(page, fixture);
  await page.goto("/viewer/");
  await expect(page.getByTestId("viewer-sort-menu")).toBeVisible();
}

/** viewer.filter.pageOf（例:「1 / 2 ページ（全 60 件）」）から件数を取り出す（既存 spec と同じ方式） */
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

/** 一覧の先頭カード（.comp-table__card）の y（scrollIntoView は使わない） */
async function firstCardY(page: Page): Promise<number> {
  const card = page.locator(".comp-table__card").first();
  await expect(card).toBeVisible();
  const box = await card.boundingBox();
  expect(box).not.toBeNull();
  return box!.y;
}

/**
 * 開いている方のパネル（絞り込みドロワー・シリーズ/並び替えパネルはどちらも
 * data-testid="supplier-drawer" を持ち DOM に常にマウントされるため、
 * .comp-drawer-panel--open で絞る。既存 spec と同じ作り）。
 */
function openPanel(page: Page): Locator {
  return page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
}

/** パネルのスライドインが収まるまで待つ（既存 spec と同じ作り） */
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

/** プレフィックスに一致する行（label で包んだ RadioControl）のうち、画面内に収まって見える件数 */
async function countVisibleChoiceRows(panel: Locator, testIdPrefix: string, innerHeight: number): Promise<number> {
  const radios = panel.locator(`[data-testid^="${testIdPrefix}"]`);
  const n = await radios.count();
  let visible = 0;
  for (let i = 0; i < n; i++) {
    const box = await radios.nth(i).evaluate((el) => {
      const label = el.closest("label");
      if (!label) return null;
      const r = label.getBoundingClientRect();
      return { y: r.y, height: r.height };
    });
    if (box && box.y >= 0 && box.y + box.height <= innerHeight) visible++;
  }
  return visible;
}

for (const width of MOBILE_WIDTHS) {
  const height = 844;
  test.describe(`visual-language: 閲覧ページ choice sheet ${width}px`, () => {
    test("B1・B2・B3: 3つのボタンが枠なしで1行に並び、44px以上・画面内、main の中の select は0件", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const series = page.getByTestId("viewer-tab-select");
      const sort = page.getByTestId("viewer-sort-menu");
      const filter = page.getByTestId("viewer-filter-toggle");

      // B1: 背景・枠が透明
      for (const btn of [series, sort, filter]) {
        const style = await btn.evaluate((el) => {
          const cs = getComputedStyle(el);
          return { bg: cs.backgroundColor, border: cs.borderColor };
        });
        expect(style.bg).toBe("rgba(0, 0, 0, 0)");
        expect(style.border).toBe("rgba(0, 0, 0, 0)");
      }

      // B2: 1行に並ぶ・44px以上・右端が画面幅以内
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
        expect(box.height).toBeGreaterThanOrEqual(MIN_TAP_PX);
        expect(box.x + box.width).toBeLessThanOrEqual(width);
      }

      // B3: main の中に select が0件（viewer-lang は header 側なので対象外）
      expect(await page.locator("main select").count()).toBe(0);

      await expectNoPageOverflow(page);
    });

    test("B4・B5: シリーズを押すとパネルが開き題が「シリーズ」。行は44px以上で8行以上見える", async ({ page }) => {
      await gotoViewerWithSeries(page, width, height);
      // 押す前は開いていない（空振り検査を避ける）
      expect(await openPanel(page).count()).toBe(0);

      await page.getByTestId("viewer-tab-select").click();
      const panel = openPanel(page);
      await waitPanelSlidIn(panel);
      await expect(panel.locator(".comp-drawer-title")).toHaveText("シリーズ");

      const firstRowTestId = `viewer-series-option-${SERIES_NAMES[0]}`;
      const box = await panel.getByTestId(firstRowTestId).evaluate((el) => {
        const label = el.closest("label");
        if (!label) return null;
        const r = label.getBoundingClientRect();
        return { x: r.x, y: r.y, width: r.width, height: r.height };
      });
      expect(box).not.toBeNull();
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);

      const visible = await countVisibleChoiceRows(panel, "viewer-series-option-", height);
      expect(visible).toBeGreaterThanOrEqual(MIN_VISIBLE_ROWS);

      // 絞り込みドロワーとシリーズ/並び替えパネルが同時に開いていないこと（どちらも DOM に常在するため）
      expect(await page.locator(".comp-drawer-panel--open").count()).toBe(1);
    });

    test("B6・B7・B8: シリーズの行を選ぶと即閉じて一覧が絞られ、ボタンの文字が選んだ名前になり件数は入らない", async ({ page }) => {
      await gotoViewerWithSeries(page, width, height);
      const trigger = page.getByTestId("viewer-tab-select");
      const pageInfo = page.getByTestId("viewer-pagination-label");
      const before = extractRowCount(await pageInfo.textContent());

      // B8: 開く前の文字に件数が入っていない
      await expect(trigger).not.toContainText("(");

      await trigger.click();
      const panel = openPanel(page);
      await waitPanelSlidIn(panel);
      const target = SERIES_NAMES[3];
      await panel.getByTestId(`viewer-series-option-${target}`).click();

      // B6: 選ぶと即閉じる
      expect(await openPanel(page).count()).toBe(0);
      // B7: ボタンの文字が選んだシリーズ名になる
      await expect(trigger).toHaveText(target);
      // B8: 選んだ後も件数は入らない
      await expect(trigger).not.toContainText("(");

      const after = extractRowCount(await pageInfo.textContent());
      expect(after).toBeLessThan(before);
    });

    test("B6b: すでに選ばれている行を押してもパネルが閉じる", async ({ page }) => {
      await gotoViewerWithSeries(page, width, height);
      const trigger = page.getByTestId("viewer-tab-select");
      const target = SERIES_NAMES[2];

      await trigger.click();
      let panel = openPanel(page);
      await waitPanelSlidIn(panel);
      await panel.getByTestId(`viewer-series-option-${target}`).click();
      await expect(openPanel(page)).toHaveCount(0);

      // もう一度開いて「いま選ばれている行」を押す。ネイティブ radio は値が変わらないと
      // change を出さないため、onChange だけに頼った実装ではここで閉じない（審査 R1）
      await trigger.click();
      panel = openPanel(page);
      await waitPanelSlidIn(panel);
      const same = panel.getByTestId(`viewer-series-option-${target}`);
      await expect(same).toBeChecked();
      await same.click();
      await expect(openPanel(page)).toHaveCount(0);
      await expect(trigger).toHaveText(target);
    });

    test("B9: 並び替えパネルは4行（既定＋3択）。選ぶと即反映し、既定を選ぶと並びが既定に戻る", async ({ page }) => {
      await gotoViewerForSort(page, width, height);
      const trigger = page.getByTestId("viewer-sort-menu");
      const firstCard = () => page.locator(".comp-table__card").first();

      // 既定（発売日が新しい順）は release_date が同じ2行では元の順を保つため、先に入れた HIGH(¥900) が先頭
      await expect(firstCard()).toContainText("¥900");
      await expect(trigger).toHaveText("並び替え");
      expect(await openPanel(page).count()).toBe(0);

      await trigger.click();
      let panel = openPanel(page);
      await waitPanelSlidIn(panel);
      await expect(panel.locator('[data-testid^="viewer-sort-option-"]')).toHaveCount(4);

      await panel.getByTestId("viewer-sort-option-unit_price:asc").click();
      // 選ぶと即閉じて反映
      expect(await openPanel(page).count()).toBe(0);
      await expect(firstCard()).toContainText("¥100");

      await trigger.click();
      panel = openPanel(page);
      await waitPanelSlidIn(panel);
      await panel.getByTestId("viewer-sort-option-default").click();

      // 既定に戻る
      expect(await openPanel(page).count()).toBe(0);
      await expect(firstCard()).toContainText("¥900");
      await expect(trigger).toHaveText("並び替え");
    });

    test("B10: パネルは Esc と ✕ で閉じる（スマホは全幅のため背景を押す余地が無い）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const trigger = page.getByTestId("viewer-tab-select");

      await trigger.click();
      let panel = openPanel(page);
      await waitPanelSlidIn(panel);
      await page.keyboard.press("Escape");
      await expect(openPanel(page)).toHaveCount(0);

      await trigger.click();
      panel = openPanel(page);
      await waitPanelSlidIn(panel);

      // スマホ幅では Drawer 金型が全幅になる（frontend/src/components/Drawer.css:114-118）。
      // そのため「背景（オーバーレイ）を押して閉じる」は**物理的に押せる場所が無い**。
      // CI 実測（PR #4759 の1回目）: オーバーレイをクリックしようとすると
      // comp-drawer-panel--open の subtree が pointer events を遮り 15 秒でタイムアウトした。
      // 便2 の記録（スマホは全幅で背景タップができない）と一致する。
      // ここでは「閉じる手段が Esc と ✕ の2つであること」と「全幅であること」を固定する。
      const panelBox = await panel.boundingBox();
      expect(panelBox).not.toBeNull();
      expect(Math.round(panelBox!.width)).toBe(width);

      await panel.getByTestId("drawer-close").click();
      await expect(openPanel(page)).toHaveCount(0);
    });

    test("B11: 一覧の先頭カードの y が192px以内（便3の基準を保つ）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const y = await firstCardY(page);
      expect(y).toBeLessThanOrEqual(MAX_TOP_Y);
    });

    test("B12: 横はみ出しが0", async ({ page }) => {
      await gotoViewer(page, { width, height });
      await expectNoPageOverflow(page);
    });
  });
}

test.describe("visual-language: 閲覧ページ choice sheet PC(1280px)", () => {
  test("B13: PCは今のまま（viewer-sort-menu は select のまま・タブが出る・viewer-tab-select は無い）", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    const sortMenu = page.getByTestId("viewer-sort-menu");
    await expect(sortMenu).toHaveCount(1);
    expect(await sortMenu.evaluate((el) => el.tagName)).toBe("SELECT");
    await expect(page.getByRole("tablist")).toBeVisible();
    await expect(page.getByTestId("viewer-tab-select")).toHaveCount(0);
  });
});
