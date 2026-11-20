/**
 * visual-language/inventory-toolbar-mercari.spec.ts
 * — 在庫表（/inventory）スマホの上部操作台を2段にして画面内に入れる便（便1）の合否検査。
 *
 * design: docs/handoff/inventory-toolbar-mercari/design.md 設計④・⑤ Acceptance Criteria D1〜D13。
 * recon: docs/handoff/inventory-toolbar-mercari/recon.md（本番実機の実測。直す前は右端654px・
 * `inventory-reset-sort` / `inventory-fresh-toggle` が上部に存在・`inventory-filter-toggle` の右端も
 * 画面の外＝ recon.md:17,22,23,25）。
 *
 * 幅は spec 側で明示する: 360px・390px の両方（D12 だけ PC=1280px）。
 * gotoInventory（frontend/tests-e2e/visual-language/inventory-helpers.ts）に明示で渡す
 * （project 既定の viewport に頼らない。design.md 4-4 / review-opus.md M2）。
 *
 * D13（空振り防止・design.md ⑤）: この端末では Playwright のブラウザが動かないため、CI 上で
 * D1・D4・D5 が「直す前なら必ず赤になる」ことを、recon.md の実測値（右端654px・画面360px・
 * `inventory-fresh-toggle` と `inventory-reset-sort` が上部に存在）に基づいてここに明記する。
 * 直す前は .content-toolbar__left の子（`inventory-filter-toggle` 等）の右端が画面幅360pxを超え
 * （recon.md:25 の654px）、D1 は必ず赤になる。D4 も同じ理由で赤になる。D5 は直す前は
 * `inventory-reset-sort` / `inventory-fresh-toggle` が上部操作台に実在する（recon.md:22-23）ため
 * 必ず赤になる。
 *
 * 2026-10-29 更新（PO「閲覧用のページと全く同じにしてくれ」）: スマホは `ContentToolbar` を
 * 使わなくなり、閲覧ページと同じ `.inventory-toolbar`（折り返す flex 1枚）を直接描く
 * （design.md 4-2〜4-4）。D1・D2・D9・D10 はこの `.inventory-toolbar` を測る形に更新。
 * D12（PC 不変）は `.content-toolbar` のまま＝PC 分岐は1文字も変えていないため。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoInventory } from "./inventory-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** D12: PC 幅（design.md ⑤。PC は1px も動かさない固定） */
const PC_WIDTH = 1280;

/** D3: お手本（メルカリ）の操作単位 48dp（design.md ③ P4・ADR-140） */
const MIN_TAP_HEIGHT = 48;
/** D7: パネルの中の「24時間以内」の押せる高さ下限（ADR-140） */
const MIN_FRESH_CHECK_HEIGHT = 44;
/** D10: 上部操作台（.inventory-toolbar）の高さ上限（design.md ③ P5＝48＋間隔12＋48＋上下の余白）。
 *  本便（toolbar-series-name-full-width）でシリーズが単独行になり3段168pxになったため180に更新 */
const MAX_TOOLBAR_HEIGHT = 180;
/** D2: 検索欄の幅は .inventory-toolbar の幅の95%以上（design.md ③ P3） */
const SEARCH_WIDTH_RATIO = 0.95;

/**
 * D12: PC が1px も変わっていないことの測り方。
 *
 * この端末では Playwright のブラウザが動かないため「直す前の実測値」を手元で取れない
 * （design.md ⑤ D13）。そこで**絶対値を決め打ちしない**。代わりに、
 *   (a) 幅はページが持っているトークン `--field-w-md` の値をその場で読んで突き合わせる
 *   (b) 高さ・字の大きさは、**本便で1文字も変えていない同じ形のボタン**
 *       （`inventory-reset-sort`＝`size="sm"` ＋ `layoutClassName="field-h-md"`。
 *        `inventory-filter-toggle` の PC 分岐と variant 以外まったく同じ）と**一致すること**を見る
 *   (c) スマホ用の修飾クラス（`comp-btn--tap` / `comp-btn--ghost`）が**付いていない**ことを見る
 * の3点で固定する。決め打ちの数字が無いので、トークンを変えた将来の便でも誤検知しない。
 */

/** `.inventory-toolbar`（スマホ専用の操作台）の content box 幅（padding を引いた内側の幅。design.md ③ P3） */
async function inventoryToolbarContentWidth(page: Page): Promise<number> {
  return page.evaluate(() => {
    const el = document.querySelector(".inventory-toolbar");
    if (!el) throw new Error(".inventory-toolbar not found");
    const cs = getComputedStyle(el);
    return el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  });
}

async function expectNoPageOverflow(page: Page): Promise<void> {
  const data = await page.evaluate(() => {
    const mc = document.querySelector(".mobile-content");
    return {
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      mobileContent: mc ? mc.scrollWidth - mc.clientWidth : 0,
    };
  });
  expect(data.doc).toBeLessThanOrEqual(0);
  expect(data.mobileContent).toBeLessThanOrEqual(0);
}

/** 「詳細フィルタ」を押してパネルを開く（design.md 4-6・パネル本体は inventory-filter-panel） */
async function openFilterPanel(page: Page): Promise<Locator> {
  await page.getByTestId("inventory-filter-toggle").click();
  // 便3（inventory-filter-subscreen）以降、スマホの詳細フィルタは開く前から常にマウントされ、
  // 閉状態は transform だけ（frontend/src/components/Drawer.css:38-45。visibility/display/opacity
  // による非表示は無い）ため toBeVisible() だけでは「開いた」ことの証明にならない（独立審査 r2・H-2）。
  // 本便のパネルだけが持つ mobileInset の外枠に限定して --open を確かめる
  await expect(page.locator(".comp-drawer-panel--mobile-inset.comp-drawer-panel--open")).toHaveCount(1);
  const panel = page.getByTestId("inventory-filter-panel");
  await expect(panel).toBeVisible();
  return panel;
}

for (const width of MOBILE_WIDTHS) {
  const height = 800;
  test.describe(`visual-language: 在庫表 上部操作台をお手本と同じ形に ${width}px`, () => {
    test("D1: .inventory-toolbar のすべての子要素の右端が画面幅以下（直す前は654pxで赤＝recon.md:25）", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const rights = await page.evaluate(() => {
        const el = document.querySelector(".inventory-toolbar");
        if (!el) throw new Error(".inventory-toolbar not found");
        return Array.from(el.children).map((c) => c.getBoundingClientRect().right);
      });
      expect(rights.length).toBeGreaterThan(0);
      for (const right of rights) expect(right).toBeLessThanOrEqual(width + 0.5);
    });

    test("D2: 検索欄の幅が .inventory-toolbar の幅の95%以上", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const contentWidth = await inventoryToolbarContentWidth(page);
      const box = await page.getByTestId("inventory-search").boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeGreaterThanOrEqual(contentWidth * SEARCH_WIDTH_RATIO);
    });

    test("D3: 「並び替え」「詳細フィルタ」の高さが48px以上", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const sortBox = await page.getByTestId("inventory-sort-menu").boundingBox();
      const filterBox = await page.getByTestId("inventory-filter-toggle").boundingBox();
      expect(sortBox).not.toBeNull();
      expect(filterBox).not.toBeNull();
      expect(sortBox!.height).toBeGreaterThanOrEqual(MIN_TAP_HEIGHT);
      expect(filterBox!.height).toBeGreaterThanOrEqual(MIN_TAP_HEIGHT);
    });

    test("D4: 「並び替え」「詳細フィルタ」が両方 viewport の中にある（直す前は詳細フィルタが画面外＝recon.md:25）", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const sortBox = await page.getByTestId("inventory-sort-menu").boundingBox();
      const filterBox = await page.getByTestId("inventory-filter-toggle").boundingBox();
      expect(sortBox).not.toBeNull();
      expect(filterBox).not.toBeNull();
      for (const box of [sortBox!, filterBox!]) {
        expect(box.x).toBeGreaterThanOrEqual(0);
        expect(box.y).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width).toBeLessThanOrEqual(width + 0.5);
        expect(box.y + box.height).toBeLessThanOrEqual(height + 0.5);
      }
    });

    test("D5: 上部操作台に inventory-reset-sort と inventory-fresh-toggle が無い（直す前は両方上部に実在＝recon.md:22-23）", async ({ page }) => {
      await gotoInventory(page, { width, height });

      await expect(page.getByTestId("inventory-reset-sort")).toHaveCount(0);
      await expect(page.getByTestId("inventory-fresh-toggle")).toHaveCount(0);
    });

    test("D6: 「詳細フィルタ」を押すとパネルが開き、中に inventory-fresh-check と inventory-reset-in-panel がある", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const panel = await openFilterPanel(page);
      await expect(panel.getByTestId("inventory-fresh-check")).toBeVisible();
      await expect(panel.getByTestId("inventory-reset-in-panel")).toBeVisible();
    });

    test("D7: パネルの中の inventory-fresh-check の押せる高さが44px以上", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const panel = await openFilterPanel(page);
      const row = panel.getByTestId("inventory-fresh-check").locator("xpath=ancestor::label[1]");
      await expect(row).toBeVisible();
      const box = await row.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBeGreaterThanOrEqual(MIN_FRESH_CHECK_HEIGHT);
    });

    test("D8: 「詳細フィルタ」の文字は常に完全一致し、数字(n)を含まない（PO 決定1。design.md 4-9 (2) で作り替え）", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const toggle = page.getByTestId("inventory-filter-toggle");
      await expect(toggle).toHaveText("詳細フィルタ");

      // 絞り込みを操作しても文字は変わらない（以前はここで数字が減った）
      const panel = await openFilterPanel(page);
      await panel.getByTestId("inventory-fresh-check").click();
      await expect(toggle).toHaveText("詳細フィルタ");
      expect(await toggle.textContent()).not.toMatch(/\(\d+\)/);
    });

    test("D9: スマホでは .content-toolbar が無く .inventory-toolbar が1枚だけある（閲覧ページと同じ作り）", async ({ page }) => {
      await gotoInventory(page, { width, height });

      await expect(page.locator(".content-toolbar")).toHaveCount(0);
      await expect(page.locator(".inventory-toolbar")).toHaveCount(1);
    });

    test("D10: .inventory-toolbar の高さが180px以下（4行に折り返していないこと・P5）", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const box = await page.locator(".inventory-toolbar").boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBeLessThanOrEqual(MAX_TOOLBAR_HEIGHT);
    });

    test("D11: document と .mobile-content の横の超過が0", async ({ page }) => {
      await gotoInventory(page, { width, height });

      await expectNoPageOverflow(page);
    });
  });
}

test.describe("visual-language: 在庫表 PC は上部操作台が今までどおり", () => {
  test(`D12: PC（幅${PC_WIDTH}px）は検索欄の幅・詳細フィルタの min-height / font-size・並びが変わっていない`, async ({ page }) => {
    await gotoInventory(page, { width: PC_WIDTH, height: 800 });

    // PC は今までどおり共通の操作台（2段）。スマホ専用の1枚は描かれない
    await expect(page.locator(".content-toolbar--two-rows")).toHaveCount(1);
    await expect(page.locator(".inventory-toolbar")).toHaveCount(0);

    // (a) 検索欄の幅はトークン --field-w-md のまま（値はページから読む＝決め打ちしない）
    const tokenWidth = await page.evaluate(() =>
      parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--field-w-md")),
    );
    expect(Number.isFinite(tokenWidth)).toBe(true);
    const searchBox = await page.getByTestId("inventory-search").boundingBox();
    expect(searchBox).not.toBeNull();
    expect(Math.round(searchBox!.width)).toBe(Math.round(tokenWidth));

    // (b) 詳細フィルタの高さ・字の大きさは、本便で1文字も変えていない「リセット」と一致する
    const filterToggle = page.getByTestId("inventory-filter-toggle");
    await expect(filterToggle).toBeVisible();
    const readBox = (loc: Locator) =>
      loc.evaluate((el) => {
        const cs = getComputedStyle(el);
        return { minHeight: cs.minHeight, fontSize: cs.fontSize };
      });
    const filterComputed = await readBox(filterToggle);
    const resetComputed = await readBox(page.getByTestId("inventory-reset-sort"));
    expect(filterComputed.minHeight).toBe(resetComputed.minHeight);
    expect(filterComputed.fontSize).toBe(resetComputed.fontSize);

    // (c) スマホ用の修飾クラスが PC に漏れていない
    await expect(filterToggle).not.toHaveClass(/comp-btn--tap/);
    await expect(filterToggle).not.toHaveClass(/comp-btn--ghost/);

    // 子要素の並び（1段目: 検索 → 価格 → 数量 / 2段目左: 並び替え → コンディション → 提供者 → 詳細フィルタ
    // / 2段目右: 24時間以内 → リセット）。PC 分岐の JSX 変数を1文字も変えていないことの裏取り
    const order = await page.evaluate(() => {
      const before = (a: Element, b: Element) =>
        !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      const byTestId = (id: string) => document.querySelector(`[data-testid="${id}"]`);
      const ids = [
        "inventory-search",
        "inventory-price-min",
        "inventory-qty-min",
        "inventory-sort-menu",
        "inventory-condition-filter-button",
        "inventory-supplier-filter-button",
        "inventory-filter-toggle",
        "inventory-fresh-toggle",
        "inventory-reset-sort",
      ];
      const els = ids.map((id) => byTestId(id));
      if (els.some((el) => !el)) return { ok: false, missing: ids.filter((_, i) => !els[i]) };
      for (let i = 0; i < els.length - 1; i++) {
        if (!before(els[i] as Element, els[i + 1] as Element)) {
          return { ok: false, failedAt: ids[i] };
        }
      }
      return { ok: true };
    });
    expect(order).toEqual({ ok: true });
  });
});
