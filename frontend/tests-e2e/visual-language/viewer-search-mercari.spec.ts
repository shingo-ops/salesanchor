/**
 * visual-language/viewer-search-mercari.spec.ts
 * — 閲覧ページ（/viewer/）スマホの検索をお手本（メルカリ）と同じ作りにする（便12a）の合否検査
 *
 * design: docs/handoff/viewer-search-mercari/design.md 設計⑤ Acceptance Criteria B1〜B9。
 * recon: docs/handoff/viewer-search-mercari/recon.md（お手本の実測値・現物調査）。
 *
 * 「押すと検索の画面に移る → 確定してはじめて一覧が絞られる → 語は札で残る → 最近使った語が出る」を
 * お手本と同じ動きで固定する。打っている最中の候補は別便（便12b）。PC は1px も動かさない（B9）。
 *
 * 幅は spec 側で明示する: 360px・390px の両方（B9 だけ PC=1280px）。gotoViewer に明示で渡す
 * （design ⑤「3つの project がこの spec を収集するため」）。
 *
 * playwright.config.ts の testMatch が visual-language/ 配下に限るため、
 * このファイルを tests-e2e/ 直下に置くと CI で1本も走らない（design ⑤の注意と同じ）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** B9: PC 幅（design.md ⑤。PC は1px も動かさない固定） */
const PC_WIDTH = 1280;
/** B1・B4: お手本（メルカリ）の操作単位 48dp（design.md ③ P1） */
const TAP_HEIGHT_PX = 48;
/** B1: 角丸はピル（design.md ③ P2）。24px 以上あればピルとみなす */
const MIN_PILL_RADIUS_PX = 24;
/** ✕ の押せる範囲（ADR-140） */
const MIN_TAP_PX = 44;
/** B8: 「最近使った語」の行（design.md ③ P4） */
const SEARCH_ROW_H_PX = 69;
const SEARCH_ROW_TEXT_LEFT_PX = 64;
/** fixture（gotoViewer 既定・viewer-helpers.ts makeViewerFixture）の中で一意に1件だけ当たる語 */
const UNIQUE_TERM = "item-005";

/** viewer.filter.pageOf（例:「1 / 2 ページ（全 60 件）」）から件数を取り出す（既存 spec と同じ方式） */
function extractRowCount(text: string | null): number {
  // eslint-disable-next-line local/no-japanese-literal -- tests-e2e は ESLint 対象外。画面文言の正規表現
  const m = (text ?? "").match(/([\d,]+)\s*(?:件|items)/);
  if (!m) throw new Error(`row count not found in pagination label: "${text}"`);
  return Number(m[1].replace(/,/g, ""));
}

async function rowCount(page: Page): Promise<number> {
  const label = page.getByTestId("viewer-pagination-label");
  await expect(label).toBeVisible();
  return extractRowCount(await label.textContent());
}

/** すでにトリガーした開く操作のスライドインが収まるまで待つ（便2 spec と同じ作り） */
async function waitSearchScreenOpen(page: Page): Promise<Locator> {
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

/** 検索画面（Drawer）を開き、スライドインが収まるまで待つ */
async function openSearchScreen(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-search-open").click();
  return waitSearchScreenOpen(page);
}

function noOpenPanel(page: Page): Locator {
  return page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
}

for (const width of MOBILE_WIDTHS) {
  const height = 844;
  test.describe(`visual-language: 閲覧ページ 検索をお手本と同じ作りに ${width}px`, () => {
    test("B1: 検索バーが48px・角丸24px以上・虫眼鏡が1つ", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const bar = page.getByTestId("viewer-search");
      await expect(bar).toBeVisible();
      const box = await bar.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBe(TAP_HEIGHT_PX);

      const radius = await bar.evaluate((el) => parseFloat(getComputedStyle(el).borderRadius));
      expect(radius).toBeGreaterThanOrEqual(MIN_PILL_RADIUS_PX);

      await expect(bar.locator("svg")).toHaveCount(1);
    });

    test("B2: 検索欄を押すと検索画面が開き、入力欄にフォーカスがある", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openSearchScreen(page);
      const input = panel.getByTestId("viewer-search-input");
      await expect(input).toBeVisible();
      await expect(input).toBeFocused();
    });

    test("B3: 検索画面で文字を打っても、一覧の件数が変わらない", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const before = await rowCount(page);
      const panel = await openSearchScreen(page);
      await panel.getByTestId("viewer-search-input").fill(UNIQUE_TERM);
      expect(await rowCount(page)).toBe(before);
    });

    test("B4: 確定すると画面が閉じ、一覧の件数が変わる（キーボードの検索キー＝Enter）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const before = await rowCount(page);
      const panel = await openSearchScreen(page);
      const input = panel.getByTestId("viewer-search-input");
      await input.fill(UNIQUE_TERM);
      await input.press("Enter");
      await expect(noOpenPanel(page)).toHaveCount(0);
      const after = await rowCount(page);
      expect(after).toBe(1);
      expect(after).not.toBe(before);
    });

    test("B5: 確定後、検索欄に「語」の札と✕が出る（✕は44px以上）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openSearchScreen(page);
      // 確定はキーボードの検索キー（Enter）で行う。確定ボタン viewer-search-submit は
      // 読み上げ専用（sr-only）で画面上の大きさが 1px しかなく、Playwright の click が
      // 当たらず18秒待って落ちるため（2026-10-28 の CI で実測）。実機の確定もこの道
      await panel.getByTestId("viewer-search-input").fill(UNIQUE_TERM);
      await panel.getByTestId("viewer-search-input").press("Enter");

      const chip = page.getByTestId("viewer-search-chip");
      await expect(chip).toBeVisible();
      await expect(chip).toHaveText(UNIQUE_TERM);

      const clear = page.getByTestId("viewer-search-clear");
      await expect(clear).toBeVisible();
      const clearBox = await clear.boundingBox();
      expect(clearBox).not.toBeNull();
      expect(clearBox!.width).toBeGreaterThanOrEqual(MIN_TAP_PX);
      expect(clearBox!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);
    });

    // お手本の実測（2026-10-28・design.md 4-3 更新）: 結果画面の✕は語を消して入力待ちに
    // するだけで、一覧は前のまま（全件には戻らない）。PO 決定でお手本と同じ動きに直した。
    test("B6: 札の✕を押すと検索画面が開き、入力欄が空になり、件数は変わらない", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openSearchScreen(page);
      // 確定はキーボードの検索キー（Enter）で行う。確定ボタン viewer-search-submit は
      // 読み上げ専用（sr-only）で画面上の大きさが 1px しかなく、Playwright の click が
      // 当たらず18秒待って落ちるため（2026-10-28 の CI で実測）。実機の確定もこの道
      await panel.getByTestId("viewer-search-input").fill(UNIQUE_TERM);
      await panel.getByTestId("viewer-search-input").press("Enter");
      const afterConfirm = await rowCount(page);
      expect(afterConfirm).toBe(1);

      await page.getByTestId("viewer-search-clear").click();
      const reopened = await waitSearchScreenOpen(page);
      await expect(reopened.getByTestId("viewer-search-input")).toHaveValue("");
      // 一覧（ドロワーの外）は前のまま。件数は動かさない
      expect(await rowCount(page)).toBe(afterConfirm);
    });

    test("B7: 開き直すと「最近使った語」にその語がある。押すとその語で絞られる", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openSearchScreen(page);
      // 確定はキーボードの検索キー（Enter）で行う。確定ボタン viewer-search-submit は
      // 読み上げ専用（sr-only）で画面上の大きさが 1px しかなく、Playwright の click が
      // 当たらず18秒待って落ちるため（2026-10-28 の CI で実測）。実機の確定もこの道
      await panel.getByTestId("viewer-search-input").fill(UNIQUE_TERM);
      await panel.getByTestId("viewer-search-input").press("Enter");

      // ✕ を押すと検索画面が開き直る（一覧は前のまま。design.md 4-3 更新）
      await page.getByTestId("viewer-search-clear").click();
      const reopened = await waitSearchScreenOpen(page);
      await expect(reopened.getByTestId("viewer-recent-title")).toBeVisible();
      const row = reopened.getByTestId(`viewer-recent-row-${UNIQUE_TERM}`);
      await expect(row).toBeVisible();
      await row.click();

      await expect(noOpenPanel(page)).toHaveCount(0);
      expect(await rowCount(page)).toBe(1);
      await expect(page.getByTestId("viewer-search-chip")).toHaveText(UNIQUE_TERM);
    });

    test("B8: 「最近使った語」の行が69px・文字の左端が64px・行の中に印が1つ", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openSearchScreen(page);
      // 確定はキーボードの検索キー（Enter）で行う。確定ボタン viewer-search-submit は
      // 読み上げ専用（sr-only）で画面上の大きさが 1px しかなく、Playwright の click が
      // 当たらず18秒待って落ちるため（2026-10-28 の CI で実測）。実機の確定もこの道
      await panel.getByTestId("viewer-search-input").fill(UNIQUE_TERM);
      await panel.getByTestId("viewer-search-input").press("Enter");

      // 開き直す道は✕（札）を使う。便12b 以降、語が入った状態（viewer-search-open）で
      // 開き直すと候補が出るため。お手本の実測（2026-10-28）どおり
      await page.getByTestId("viewer-search-clear").click();
      const reopened = await waitSearchScreenOpen(page);
      const row = reopened.getByTestId(`viewer-recent-row-${UNIQUE_TERM}`);
      await expect(row).toBeVisible();
      const box = await row.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBe(SEARCH_ROW_H_PX);

      const paddingLeft = await row.evaluate((el) => parseFloat(getComputedStyle(el).paddingLeft));
      expect(paddingLeft).toBe(SEARCH_ROW_TEXT_LEFT_PX);

      // お手本の実測（2026-10-28）: 履歴の行の左48dpに時計の印が入る（design.md 4-5 更新）
      await expect(row.locator("svg")).toHaveCount(1);
    });

    test("「すべて消す」で履歴が空になり、次に開いても最近使った語が出ない", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openSearchScreen(page);
      // 確定はキーボードの検索キー（Enter）で行う。確定ボタン viewer-search-submit は
      // 読み上げ専用（sr-only）で画面上の大きさが 1px しかなく、Playwright の click が
      // 当たらず18秒待って落ちるため（2026-10-28 の CI で実測）。実機の確定もこの道
      await panel.getByTestId("viewer-search-input").fill(UNIQUE_TERM);
      await panel.getByTestId("viewer-search-input").press("Enter");

      // ✕ を押すと検索画面が開き直る（design.md 4-3 更新）。そのまま「すべて消す」を押す
      await page.getByTestId("viewer-search-clear").click();
      const reopened = await waitSearchScreenOpen(page);
      await reopened.getByTestId("viewer-recent-clear").click();
      await expect(reopened.getByTestId(`viewer-recent-row-${UNIQUE_TERM}`)).toHaveCount(0);
      await expect(reopened.getByTestId("viewer-recent-clear")).toHaveCount(0);
    });
  });
}

test.describe("visual-language: 閲覧ページ PC は検索が今までどおり", () => {
  test(`B9: PC幅（${PC_WIDTH}px）は打つたびに件数が変わり、検索画面は開かない`, async ({ page }) => {
    await gotoViewer(page, { width: PC_WIDTH, height: 800 });
    const before = await rowCount(page);
    expect(before).toBeGreaterThan(1);

    // PC には「押すと検索画面が開くボタン」自体が無い（検索欄は今までどおりの入力欄）
    await expect(page.getByTestId("viewer-search-open")).toHaveCount(0);

    await page.getByTestId("viewer-search").fill(UNIQUE_TERM);
    expect(await rowCount(page)).toBe(1);
    await expect(noOpenPanel(page)).toHaveCount(0);
  });
});
