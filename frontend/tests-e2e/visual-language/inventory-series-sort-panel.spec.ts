/**
 * visual-language/inventory-series-sort-panel.spec.ts
 * — 在庫表（/inventory）スマホの種別のタブの行と並び替えのプルダウンを、閲覧ページと同じ
 *   「枠なしの文字ボタン → 押すと右からパネル → 1つ選ぶと即反映して閉じる」形にする便（便2）の合否検査。
 *
 * design: docs/handoff/inventory-series-sort-panel/design.md 設計④・⑤ Acceptance Criteria E1〜E14。
 * 審査: docs/handoff/inventory-series-sort-panel/review-opus.md（r1）。
 *
 * 幅を絞る（審査 H5）: CI の画面検査は1ジョブ・持ち時間10分で、便1 の時点で655件・7.4分まで来ている。
 * 本 spec は幅360を基本にし、E2・E11 だけ390でも測る（PC 判定の E14 は1280）。
 *
 * 種別パネルの件数が意味を持つよう、inventory-helpers.ts の `/products/tcg-types` mock は
 * 3件（MAIN_TCG_CODES 全件）にしてある。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoInventory } from "./inventory-helpers";

const MOBILE_WIDTH = 360;
const SECOND_MOBILE_WIDTH = 390;
/** design.md ⑤: PC 判定（E14）の幅。PC は1px も動かさない固定 */
const PC_WIDTH = 1280;

/** お手本（メルカリ）の操作単位 48dp（design.md ③ P6・ADR-140） */
const MIN_TAP_HEIGHT = 48;
/** パネルの行の押せる高さ下限（design.md ③ P7・ADR-140） */
const MIN_ROW_HEIGHT = 44;
/** .inventory-toolbar の高さ上限（design.md ③ P5）。
 *  本便（toolbar-series-name-full-width）でシリーズが単独行になり3段168pxになったため180に更新 */
const MAX_TOOLBAR_HEIGHT = 180;

/** 種別・並び替えのパネル（design.md 4-3。Drawer は共通で data-testid="supplier-drawer"。
 *  在庫表には設定パネル・行の詳細パネルも同じ testid を持つため、開いている方だけに絞る） */
function openPanel(page: Page): Locator {
  return page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
}

/** パネルのスライドインが収まるまで待つ（閲覧ページ viewer-choice-sheet.spec.ts と同じ作り） */
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

/** 「詳細フィルタ」を押してパネルを開く（design.md 4-5。インラインのパネル本体は inventory-filter-panel） */
async function openFilterPanel(page: Page): Promise<Locator> {
  await page.getByTestId("inventory-filter-toggle").click();
  const panel = page.getByTestId("inventory-filter-panel");
  await expect(panel).toBeVisible();
  return panel;
}

test.describe(`visual-language: 在庫表 種別・並び替えパネル ${MOBILE_WIDTH}px`, () => {
  const width = MOBILE_WIDTH;
  const height = 800;

  test("E1: タブの行（[role=tablist]）が無い／inventory-expiry-warning が詳細フィルタの外に無い", async ({ page }) => {
    await gotoInventory(page, { width, height });
    await expect(page.getByRole("tablist")).toHaveCount(0);
    await expect(page.getByTestId("inventory-expiry-warning")).toHaveCount(0);
  });

  test("E3: inventory-tab-select と inventory-sort-menu の高さが48px以上で、両方 viewport の中にある", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const typeBox = await page.getByTestId("inventory-tab-select").boundingBox();
    const sortBox = await page.getByTestId("inventory-sort-menu").boundingBox();
    expect(typeBox).not.toBeNull();
    expect(sortBox).not.toBeNull();
    for (const box of [typeBox!, sortBox!]) {
      expect(box.height).toBeGreaterThanOrEqual(MIN_TAP_HEIGHT);
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.y).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width + 0.5);
      expect(box.y + box.height).toBeLessThanOrEqual(height + 0.5);
    }
  });

  test("E4: inventory-tab-select の文字がいま選ばれている種別の名前（mock の表示名と一致）", async ({ page }) => {
    await gotoInventory(page, { width, height });
    // 既定の activeTab は pokemon_booster_box。inventory-helpers.ts の mock での表示名は「ポケモン」
    await expect(page.getByTestId("inventory-tab-select")).toContainText("ポケモン");
  });

  test("E5: inventory-tab-select を押すとパネルが開き、行が「すべて」＋種別の数（4件）だけ並ぶ", async ({ page }) => {
    await gotoInventory(page, { width, height });
    expect(await openPanel(page).count()).toBe(0);

    await page.getByTestId("inventory-tab-select").click();
    const panel = openPanel(page);
    await waitPanelSlidIn(panel);
    await expect(panel.locator('[data-testid^="inventory-type-option-"]')).toHaveCount(4);
  });

  test("E6: いま選ばれていない行を押すとパネルが閉じ、inventory-tab-select の文字がその名前に変わる", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const trigger = page.getByTestId("inventory-tab-select");

    await trigger.click();
    const panel = openPanel(page);
    await waitPanelSlidIn(panel);
    await panel.getByTestId("inventory-type-option-one_piece").click();

    await expect(openPanel(page)).toHaveCount(0);
    await expect(trigger).toContainText("ワンピース");
  });

  test("E7: すでに選ばれている行をもう一度押してもパネルが閉じる（K4）", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const trigger = page.getByTestId("inventory-tab-select");

    await trigger.click();
    const panel = openPanel(page);
    await waitPanelSlidIn(panel);
    const current = panel.getByTestId("inventory-type-option-pokemon_booster_box");
    await expect(current).toBeChecked();
    await current.click();

    await expect(openPanel(page)).toHaveCount(0);
  });

  test("E8: inventory-sort-menu を押すとパネルが開き行が4つ。「価格が安い順」を選ぶと閉じ文字が変わり、「既定」を選ぶと「並び替え」に戻る", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const trigger = page.getByTestId("inventory-sort-menu");
    await expect(trigger).toHaveText("並び替え");

    await trigger.click();
    let panel = openPanel(page);
    await waitPanelSlidIn(panel);
    await expect(panel.locator('[data-testid^="inventory-sort-option-"]')).toHaveCount(4);

    await panel.getByTestId("inventory-sort-option-unit_price:asc").click();
    await expect(openPanel(page)).toHaveCount(0);
    await expect(trigger).toHaveText("価格が安い順");

    await trigger.click();
    panel = openPanel(page);
    await waitPanelSlidIn(panel);
    await panel.getByTestId("inventory-sort-option-release_date:desc").click();

    await expect(openPanel(page)).toHaveCount(0);
    await expect(trigger).toHaveText("並び替え");
  });

  test("E9: パネルの行の押せる高さが44px以上", async ({ page }) => {
    await gotoInventory(page, { width, height });
    await page.getByTestId("inventory-tab-select").click();
    const panel = openPanel(page);
    await waitPanelSlidIn(panel);

    const row = panel.getByTestId("inventory-type-option-all").locator("xpath=ancestor::label[1]");
    await expect(row).toBeVisible();
    const box = await row.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(MIN_ROW_HEIGHT);
  });

  test("E10: 「詳細フィルタ」を開くと、その中に inventory-expiry-warning があり、幅がパネルの内側に収まっている（折り返している）", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const panel = await openFilterPanel(page);
    const notice = panel.getByTestId("inventory-expiry-warning");
    await expect(notice).toBeVisible();

    const panelBox = await panel.boundingBox();
    const noticeBox = await notice.boundingBox();
    expect(panelBox).not.toBeNull();
    expect(noticeBox).not.toBeNull();
    expect(noticeBox!.x + noticeBox!.width).toBeLessThanOrEqual(panelBox!.x + panelBox!.width + 0.5);

    // white-space: nowrap を外したこと（審査 H2）の直接の裏取り
    const whiteSpace = await notice.evaluate((el) => getComputedStyle(el).whiteSpace);
    expect(whiteSpace).not.toBe("nowrap");
  });

  test("E12: document と .mobile-content の横の超過が0", async ({ page }) => {
    await gotoInventory(page, { width, height });
    await expectNoPageOverflow(page);
  });

  test("E13: .inventory-choice-row:hover の規則が @media (hover: hover) の中にある（sticky hover対策・K9）", async ({ page }) => {
    await gotoInventory(page, { width, height });

    // 実際にホバーを再現するのではなく、読み込み済みスタイルシートを静的に辿って
    // 対象の規則が @media (hover: hover) の中にあることだけを確かめる
    // （先例: frontend/tests-e2e/visual-language/viewer-filter-panel-mercari.spec.ts C13）
    const result = await page.evaluate(() => {
      const target = ".inventory-choice-row:hover";
      type Hit = { found: true; mediaText: string | null };
      function walk(rules: CSSRuleList, media: string | null): Hit | null {
        for (const rule of Array.from(rules)) {
          if (rule instanceof CSSStyleRule && rule.selectorText === target) {
            return { found: true, mediaText: media };
          }
          if (rule instanceof CSSMediaRule) {
            const hit = walk(rule.cssRules, rule.media.mediaText);
            if (hit) return hit;
          } else if (rule instanceof CSSGroupingRule) {
            const hit = walk(rule.cssRules, media);
            if (hit) return hit;
          }
        }
        return null;
      }
      for (const sheet of Array.from(document.styleSheets)) {
        let rules: CSSRuleList;
        try {
          rules = sheet.cssRules;
        } catch {
          continue;
        }
        const hit = walk(rules, null);
        if (hit) return hit as { found: boolean; mediaText: string | null };
      }
      return { found: false, mediaText: null as string | null };
    });

    expect(result.found).toBe(true);
    expect((result.mediaText ?? "").replace(/\s+/g, "")).toBe("(hover:hover)");
  });

  // F1〜F5: docs/handoff/toolbar-series-name-full-width/design.md ⑤5-1。
  // 測る対象は inventory-tab-select の配下の .inventory-toolbar__label に限定する
  // （並び替え側にも同じクラスがあるが flex: 0 0 auto で構造上絶対に切れないため、
  // .first() 等で拾うと常に緑の空振りになる＝審査 M2）。幅360のみ。

  test("F1: inventory-tab-select の中の種別の名前が切れていない（scrollWidth <= clientWidth）", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const label = page.getByTestId("inventory-tab-select").locator(".inventory-toolbar__label");
    await expect(label).toBeVisible();
    const { scrollWidth, clientWidth } = await label.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  });

  // F2 は「ラベルの clientWidth」では測れない。ラベルは flex item で中身なりに縮むため、
  // 1行を独り占めしていても「ポケモン」なら 52px にしかならない（本番実機で実測）。
  // 名前に使える余地は「ボタンの内側 − 左右の余白 − 山形 − すき間」で求める（実機で262px）。
  test("F2: inventory-tab-select の中で種別の名前に使える余地が240px以上", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const trigger = page.getByTestId("inventory-tab-select");
    await expect(trigger).toBeVisible();
    const room = await trigger.evaluate((btn) => {
      const cs = getComputedStyle(btn);
      const caret = btn.querySelector(".inventory-toolbar__caret");
      const gap = parseFloat(cs.columnGap) || 0;
      return (
        btn.clientWidth -
        parseFloat(cs.paddingLeft) -
        parseFloat(cs.paddingRight) -
        (caret ? caret.getBoundingClientRect().width : 0) -
        gap
      );
    });
    expect(room).toBeGreaterThanOrEqual(240);
  });

  test("F3: 並び替えに「価格が安い順」を選んだ状態でも種別の名前が切れない", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const sortTrigger = page.getByTestId("inventory-sort-menu");
    await sortTrigger.click();
    const panel = openPanel(page);
    await waitPanelSlidIn(panel);
    await panel.getByTestId("inventory-sort-option-unit_price:asc").click();
    await expect(openPanel(page)).toHaveCount(0);
    await expect(sortTrigger).toHaveText("価格が安い順");

    const label = page.getByTestId("inventory-tab-select").locator(".inventory-toolbar__label");
    await expect(label).toBeVisible();
    const { scrollWidth, clientWidth } = await label.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  });

  test("F4: inventory-tab-select が1行を独り占めしている（y が inventory-sort-menu と異なる／幅が .inventory-toolbar と同じ／ラベルの左端が並び替えと揃う）", async ({ page }) => {
    await gotoInventory(page, { width, height });
    const typeTrigger = page.getByTestId("inventory-tab-select");
    const sortTrigger = page.getByTestId("inventory-sort-menu");
    await expect(typeTrigger).toBeVisible();
    await expect(sortTrigger).toBeVisible();

    const [typeBox, sortBox, toolbarWidth] = await Promise.all([
      typeTrigger.boundingBox(),
      sortTrigger.boundingBox(),
      page.locator(".inventory-toolbar").evaluate((el) => el.clientWidth),
    ]);
    expect(typeBox).not.toBeNull();
    expect(sortBox).not.toBeNull();
    expect(typeBox!.y).not.toBe(sortBox!.y);
    expect(Math.round(typeBox!.width)).toBe(toolbarWidth);

    const [typeLabelBox, sortLabelBox] = await Promise.all([
      typeTrigger.locator(".inventory-toolbar__label").boundingBox(),
      sortTrigger.locator(".inventory-toolbar__label").boundingBox(),
    ]);
    expect(typeLabelBox).not.toBeNull();
    expect(sortLabelBox).not.toBeNull();
    expect(Math.round(typeLabelBox!.x)).toBe(Math.round(sortLabelBox!.x));
  });

  test("F5: 空振り防止。flex を 1 1 0 に戻すと種別の名前が切れる（scrollWidth > clientWidth）", async ({ page }) => {
    await gotoInventory(page, { width, height });
    await page.addStyleTag({
      content: ".inventory-toolbar > .inventory-toolbar__series { flex: 1 1 0 !important; }",
    });

    const label = page.getByTestId("inventory-tab-select").locator(".inventory-toolbar__label");
    await expect(label).toBeVisible();
    const { scrollWidth, clientWidth } = await label.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(scrollWidth).toBeGreaterThan(clientWidth);
  });
});

// E2・E11: 審査 H5 に基づき、このペアだけ360/390の両方を測る。
for (const width of [MOBILE_WIDTH, SECOND_MOBILE_WIDTH]) {
  const height = 800;
  test.describe(`visual-language: 在庫表 種別・並び替えパネル（操作台の寸法） ${width}px`, () => {
    test("E2: .inventory-toolbar の子が4つで、全部の右端が画面幅以下", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const rights = await page.evaluate(() => {
        const el = document.querySelector(".inventory-toolbar");
        if (!el) throw new Error(".inventory-toolbar not found");
        return Array.from(el.children).map((c) => c.getBoundingClientRect().right);
      });
      expect(rights.length).toBe(4);
      for (const right of rights) expect(right).toBeLessThanOrEqual(width + 0.5);
    });

    test("E11: .inventory-toolbar の高さが180px以下（4行に折り返していないこと）", async ({ page }) => {
      await gotoInventory(page, { width, height });

      const box = await page.locator(".inventory-toolbar").boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBeLessThanOrEqual(MAX_TOOLBAR_HEIGHT);
    });
  });
}

test.describe("visual-language: 在庫表 種別・並び替えパネル PC は変わらない", () => {
  test(`E14: PC（幅${PC_WIDTH}px）はタブの行がある／inventory-sort-menu は select 要素／inventory-tab-select は無い／注記は .comp-tabs-bar__end の中にある`, async ({ page }) => {
    await gotoInventory(page, { width: PC_WIDTH, height: 800 });

    await expect(page.getByRole("tablist")).toBeVisible();

    const sortMenu = page.getByTestId("inventory-sort-menu");
    await expect(sortMenu).toHaveCount(1);
    expect(await sortMenu.evaluate((el) => el.tagName)).toBe("SELECT");

    await expect(page.getByTestId("inventory-tab-select")).toHaveCount(0);

    const notice = page.getByTestId("inventory-expiry-warning");
    await expect(notice).toHaveCount(1);
    const inEnd = await notice.evaluate((el) => !!el.closest(".comp-tabs-bar__end"));
    expect(inEnd).toBe(true);
  });
});
