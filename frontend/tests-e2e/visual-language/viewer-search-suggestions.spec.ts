/**
 * visual-language/viewer-search-suggestions.spec.ts
 * — 閲覧ページ（/viewer/）スマホの検索画面で、打っている間だけ候補を並べる（便12b）の合否検査
 *
 * design: docs/handoff/viewer-search-suggestions/design.md 設計⑤ Acceptance Criteria B1〜B6。
 * recon: docs/handoff/viewer-search-suggestions/recon.md（お手本の実測値・現物調査）。
 *
 * 「draft が空なら最近使った語／1文字以上なら候補（当たらなければ何も出さない）」を固定する。
 * B7・B8（最近使った語の退行）は既存 viewer-search-mercari.spec.ts が見る（design ⑤）。
 * B6（確定後に開き直したときの退行防止・お手本の実測 2026-10-28）はこの spec で見る。
 *
 * 幅は spec 側で明示する: 360px・390px（PC は対象外。検索画面そのものがスマホだけ）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** B4: 候補の行（design.md ③ P2。最近使った語と同じ形） */
const SUGGESTION_ROW_H_PX = 69;
const SUGGESTION_ROW_TEXT_LEFT_PX = 64;

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

/** すでにトリガーした開く操作のスライドインが収まるまで待つ（viewer-search-mercari.spec.ts と同じ作り） */
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
  test.describe(`visual-language: 閲覧ページ 打つと出る候補 ${width}px`, () => {
    test("B1+B4: 文字を打つと候補が出て最近使った語は消える。行は69px・左64px・印1つ", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      // fixture の行から一意に1件だけ当たる語を取る（design「固定文字列を決め打ちしない」）。
      // 候補を押すと表示名（空白を含む「商品 N」）がそのまま確定の語になるため、1桁の N は
      // 他の行（「商品 15」「商品 45」等）にも AND の第2語として当たってしまう。2桁の N
      // （rows[39] = 40 番目の行）ならどの行にも部分一致しないため一意になる
      const target = fixture.response.rows[39];
      const panel = await openSearchScreen(page);
      await panel.getByTestId("viewer-search-input").fill(target.english_title);

      // 最近使った語は消える（候補に切り替わる）
      await expect(panel.getByTestId("viewer-recent-title")).toHaveCount(0);

      const row = panel.getByTestId(`viewer-suggestion-row-${target.japanese_title}`);
      await expect(row).toBeVisible();
      const box = await row.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBe(SUGGESTION_ROW_H_PX);

      const paddingLeft = await row.evaluate((el) => parseFloat(getComputedStyle(el).paddingLeft));
      expect(paddingLeft).toBe(SUGGESTION_ROW_TEXT_LEFT_PX);

      await expect(row.locator("svg")).toHaveCount(1);
    });

    test("B2: 候補を押すと検索画面が閉じ、件数が変わり、札にその語が出る", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const target = fixture.response.rows[39];
      const before = await rowCount(page);
      const panel = await openSearchScreen(page);
      await panel.getByTestId("viewer-search-input").fill(target.english_title);

      const row = panel.getByTestId(`viewer-suggestion-row-${target.japanese_title}`);
      await expect(row).toBeVisible();
      await row.click();

      await expect(noOpenPanel(page)).toHaveCount(0);
      const after = await rowCount(page);
      expect(after).toBe(1);
      expect(after).not.toBe(before);
      await expect(page.getByTestId("viewer-search-chip")).toHaveText(target.japanese_title);
    });

    test("B3: 入力を空に戻すと候補が消えて最近使った語が戻る", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const target = fixture.response.rows[39];
      const panel = await openSearchScreen(page);
      const input = panel.getByTestId("viewer-search-input");
      await input.fill(target.english_title);
      await expect(panel.getByTestId(`viewer-suggestion-row-${target.japanese_title}`)).toBeVisible();

      await input.fill("");
      await expect(panel.getByTestId("viewer-recent-title")).toBeVisible();
      await expect(panel.locator(".viewer-suggestion-row")).toHaveCount(0);
    });

    test("B5: 当たらない語を打つと候補も最近使った語も出ない", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openSearchScreen(page);
      await panel.getByTestId("viewer-search-input").fill("zzz-no-match-999");

      await expect(panel.locator(".viewer-suggestion-row")).toHaveCount(0);
      await expect(panel.getByTestId("viewer-recent-title")).toHaveCount(0);
      await expect(panel.locator(".viewer-recent-row")).toHaveCount(0);
    });

    // お手本の実機実測（2026-10-28・recon §1 F8）に合わせた形。✕ の道（便12a B6/B7）は
    // draft が空になるので最近使った語が出る
    test("B6: 確定した語がある状態で検索欄を押して開き直すと、入力に語が入ったまま候補が出る（最近使った語は出ない）", async ({
      page,
    }) => {
      const fixture = await gotoViewer(page, { width, height });
      const target = fixture.response.rows[39];
      const panel = await openSearchScreen(page);
      await panel.getByTestId("viewer-search-input").fill(target.english_title);
      // 確定はキーボードの検索キー（Enter）で行う。確定ボタン viewer-search-submit は
      // 読み上げ専用（sr-only）で画面上の大きさが 1px しかなく、Playwright の click が
      // 当たらず18秒待って落ちるため（既存 spec と同じ理由）
      await panel.getByTestId("viewer-search-input").press("Enter");
      await expect(noOpenPanel(page)).toHaveCount(0);

      const reopened = await openSearchScreen(page);
      await expect(reopened.getByTestId("viewer-search-input")).toHaveValue(target.english_title);
      await expect(reopened.getByTestId("viewer-recent-title")).toHaveCount(0);
      await expect(reopened.getByTestId(`viewer-suggestion-row-${target.japanese_title}`)).toBeVisible();
    });
  });
}
