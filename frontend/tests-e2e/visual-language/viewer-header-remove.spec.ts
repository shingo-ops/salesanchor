/**
 * visual-language/viewer-header-remove.spec.ts
 * — 閲覧ページ（/viewer/）のヘッダーを丸ごと消す（便4）の合否検査
 *
 * design: docs/handoff/viewer-header-remove/design.md 設計④・⑤ Acceptance Criteria C1〜C8（C18 含む）。
 * recon: docs/handoff/viewer-header-remove/recon.md。
 *
 * スマホの上部にある帯（題「在庫一覧」・最終更新・言語）を無くし、最終更新と言語は
 * 絞り込みドロワーの最初の画面（root）の一番下へ移す便の検査。PC は帯を残したまま不変。
 *
 * 幅は spec 側で明示する: 360px・390px の両方（C8 のみ PC=1280px）。
 * 測り方の共通の決まり（design.md ⑤冒頭）: scrollIntoView を使わずに測る（流用すると常に真になる）。
 * 開く前に「無いこと」を確かめてから操作する。開いているパネルは .comp-drawer-panel--open で絞る
 * （便5 の openPanel() と同じ作法。viewer-updated/viewer-lang は Drawer が閉じていても DOM に居る）。
 *
 * playwright.config.ts の testMatch が visual-language/ 配下に限るため、
 * このファイルを tests-e2e/ 直下に置くと CI で1本も走らない（design ⑪の注意と同じ）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** 一覧の先頭カードの y の上限（design.md ③・計算値124・余裕4px） */
// 便10 で検索欄とボタン行が48pxになり計算値132。docs/handoff/viewer-control-tap-size/design.md ⑤
const MAX_TOP_Y = 132;
/** 言語セレクトの高さの下限（design.md ③・ADR-140） */
const MIN_TAP_PX = 44;

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

/** 開いている方のパネル（便5 openPanel() と同じ作り。両方の Drawer が同じ testid を持つため open で絞る） */
function openPanel(page: Page): Locator {
  return page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
}

/** 絞り込みドロワーを開き、スライドが収まるまで待つ（便2・便3 spec と同じ作り） */
async function openFilterDrawer(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-filter-toggle").click();
  const panel = openPanel(page);
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

for (const width of MOBILE_WIDTHS) {
  const height = 844;
  test.describe(`visual-language: 閲覧ページ ヘッダー削除 ${width}px`, () => {
    test("C1: 一覧の先頭カードの y が128px以内", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const y = await firstCardY(page);
      expect(y).toBeLessThanOrEqual(MAX_TOP_Y);
    });

    test("C2: スマホに .viewer-header が0件", async ({ page }) => {
      await gotoViewer(page, { width, height });
      expect(await page.locator(".viewer-header").count()).toBe(0);
    });

    test("C3・C4: 絞り込みを開くと開いているパネルの中に最終更新と言語がある", async ({ page }) => {
      await gotoViewer(page, { width, height });
      // 開く前はパネルが開いていない（空振り検査を避ける）
      expect(await openPanel(page).count()).toBe(0);

      const panel = await openFilterDrawer(page);

      // C3: viewer-updated が開いているパネルの中に見え、文字に時刻（:）が入る
      const updated = panel.getByTestId("viewer-updated");
      await expect(updated).toBeVisible();
      await expect(updated).toContainText(":");

      // C4: viewer-lang が同じ場所にあり、高さ44px以上
      const lang = panel.getByTestId("viewer-lang");
      await expect(lang).toBeVisible();
      const box = await lang.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);
    });

    test("C5: viewer-lang を en にすると画面の文言が英語になる", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page);
      const lang = panel.getByTestId("viewer-lang");
      await lang.selectOption("en");

      // 切り替えた後に画面の文言が実際に英語になることで判定する（design.md ⑥守ること7）
      await expect(page.getByTestId("viewer-filter-toggle")).toContainText("Filter");
    });

    test("C6・C18: ページの h1 は1件・文字は「在庫一覧」・見た目の幅は1px以下", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const h1 = page.locator("h1");
      await expect(h1).toHaveCount(1);
      await expect(h1).toHaveText("在庫一覧");
      const box = await h1.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeLessThanOrEqual(1);
    });

    test("C7: 横はみ出しが0", async ({ page }) => {
      await gotoViewer(page, { width, height });
      await expectNoPageOverflow(page);
    });
  });
}

test.describe("visual-language: 閲覧ページ ヘッダー削除 PC(1280px)", () => {
  test("C8: PCは今のまま（.viewer-header が1件・その中に最終更新と言語が見える）", async ({ page }) => {
    await gotoViewer(page, { width: 1280, height: 900 });

    const header = page.locator(".viewer-header");
    await expect(header).toHaveCount(1);
    await expect(header.getByTestId("viewer-updated")).toBeVisible();
    await expect(header.getByTestId("viewer-lang")).toBeVisible();
  });
});
