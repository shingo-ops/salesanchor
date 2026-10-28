/**
 * visual-language/viewer-filter-panel-mercari.spec.ts
 * — 閲覧ページ（/viewer/）スマホの絞り込みパネルを、お手本（メルカリ）と同じ寸法にする便（便13a）の合否検査。
 *
 * design: docs/handoff/viewer-filter-choices-mercari/design.md 設計④・⑤ Acceptance Criteria。
 * 本ファイルが持つのは C1〜C10・C12・C13・C14（C11 は既存の viewer-inventory-mobile-filter.spec.ts 側）。
 * recon: docs/handoff/viewer-filter-choices-mercari/recon.md（現物調査）。
 *
 * 独立審査で見つかった欠陥7件の直し（設計担当の裏取り済み）: C13（sticky hoverの検査）・
 * C9拡張とC14（打ち消し幅(bleed)と内部横はみ出しの空振り防止）・C8拡張（check-colの余白を押す）・
 * DRAWER_BODY_PAD_X の直書き廃止（drawerBodyPadX で計算済みpadding-leftを読む）・
 * comp-multiselect__check → comp-multiselect__check-col への改名。
 *
 * 本便は「絞り込みパネルの幅を83%にして左に地を残す」「選択画面のチェック行を61px・印の枠48pxにする」
 * の2点だけを固定する（便11・便12a が既に固定した項目の行(53px)・検索バーなどは触らない）。
 *
 * 幅は spec 側で明示する: 360px・390pxの両方（frontend/tests-e2e/visual-language/viewer-filter-row-mercari.spec.ts
 * と viewer-inventory-mobile-filter.spec.ts と同じ形。project 既定の幅に頼らない）。
 */
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { gotoViewer, waitPanelSlidIn } from "./viewer-helpers";

const MOBILE_WIDTHS = [360, 390] as const;
/** design.md ③P1・P2: パネル幅は画面幅の83%、左端xは画面幅の17% */
const PANEL_WIDTH_RATIO = 0.83;
const PANEL_INSET_RATIO = 0.17;
/** design.md ③P3: 選択画面のチェック行の高さ下限 */
const EXPECTED_ROW_MIN_H = 61;
/** design.md ③P4: チェック行の文字の左端（行の左から） */
const EXPECTED_TEXT_LEFT = 48;
/** design.md ③P5: チェック行の文字の大きさ */
const EXPECTED_FONT_SIZE = "14.4px";
/** C3: オーバーレイの押せる領域の下限（design.md ⑤） */
const MIN_OVERLAY_GAP = 20;
/** 選択画面は必ず縦スクロールするため、ブラウザが場所を取る形のスクロールバーを出す可能性がある。
 *  行の幅をパネル幅と直に比べるとその分だけずれるので、ずれの許容をここに置く
 *  （左端の一致と「見出しとの差＝余白2つ分」の2つは、スクロールバーの有無に左右されない） */
const SCROLLBAR_ALLOWANCE = 20;
/** C12: root の「24時間以内のみ」の行の高さの範囲（4-6 の歯止め。61pxになっていないこと） */
const FRESH_CHECK_MIN_H = 44;
const FRESH_CHECK_MAX_H = 52;
/** C12: その行の文字の左端（行の左から。design.md 4-6） */
const FRESH_CHECK_TEXT_LEFT = 32;

/**
 * 絞り込みボタンを押してドロワーを開き、スライドの transition が収まるまで待つ。
 * mobileInset のため x は 0 にならない（waitPanelSlidIn は右端で判定するため成立する。
 * C1 の幅・左端の判定はこの関数の外、各 test 本体でそのまま行う）。
 * width はこの関数では使わないが、呼び出し側が C1 の判定にも使う値のため引数として残す。
 */
async function openFilterDrawer(page: Page, width: number): Promise<Locator> {
  await page.getByTestId("viewer-filter-toggle").click();
  const panel = page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
  await waitPanelSlidIn(panel, page);
  return panel;
}

/** シリーズ／並び替えパネル（mobileInset を付けていない方）を開き、スライドが収まるまで待つ */
async function openChoicePanel(page: Page): Promise<Locator> {
  await page.getByTestId("viewer-tab-select").click();
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

/** data-testid を持つチェック欄（CheckboxControl）から行全体（<label>）の Locator を取る */
function rowLocatorOf(panel: Locator, testId: string): Locator {
  return panel.getByTestId(testId).locator("xpath=ancestor::label[1]");
}

/** Drawer 本文（.comp-drawer-body）の実際の計算済み padding-left（frontend/src/components/Drawer.css の
 *  --space-6 の二重管理を避けるため、直書きの定数ではなく計算済みスタイルを読む）。
 *  選択画面の一覧はこれを打ち消してパネル全幅になる（design.md 4-3） */
async function drawerBodyPadX(page: Page): Promise<number> {
  return page.evaluate(() => {
    const body = document.querySelector(".comp-drawer-body");
    if (!body) throw new Error(".comp-drawer-body not found");
    return parseFloat(getComputedStyle(body).paddingLeft);
  });
}

/**
 * C12 用: `.viewer-fresh-check` の文字は `.comp-multiselect__option-text` のような span に
 * 包まれていない生のテキストノードのため、Range で直接その文字の bounding box を取る。
 * 戻り値は label 基準（label の x を引いた相対値）。
 */
async function freshCheckTextLeftOffset(label: Locator): Promise<number | null> {
  return label.evaluate((el) => {
    const textNode = Array.from(el.childNodes).find(
      (n) => n.nodeType === Node.TEXT_NODE && (n.textContent ?? "").trim().length > 0,
    );
    if (!textNode) return null;
    const range = document.createRange();
    range.selectNodeContents(textNode);
    const rect = range.getClientRects()[0];
    if (!rect) return null;
    const labelRect = el.getBoundingClientRect();
    return rect.x - labelRect.x;
  });
}

async function expectNoPageOverflow(page: Page): Promise<void> {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
}

for (const width of MOBILE_WIDTHS) {
  const height = 700;
  test.describe(`visual-language: 閲覧ページ 絞り込みパネルの寸法 ${width}px`, () => {
    test("C1: 絞り込みパネルの幅が画面幅の83%±1px、左端xが画面幅の17%±1px", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);

      const box = await panel.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeGreaterThanOrEqual(width * PANEL_WIDTH_RATIO - 1);
      expect(box!.width).toBeLessThanOrEqual(width * PANEL_WIDTH_RATIO + 1);
      expect(box!.x).toBeGreaterThanOrEqual(width * PANEL_INSET_RATIO - 1);
      expect(box!.x).toBeLessThanOrEqual(width * PANEL_INSET_RATIO + 1);
    });

    test("C2: シリーズ／並び替えのパネルは画面幅ちょうど（絞り込みだけ狭めたことの裏取り）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openChoicePanel(page);

      const box = await panel.boundingBox();
      expect(box).not.toBeNull();
      expect(Math.round(box!.width)).toBe(width);
    });

    test("C3: 絞り込みが開いている間、オーバーレイの押せる領域が左に20px以上ある", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);

      const box = await panel.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(MIN_OVERLAY_GAP);

      // パネルの左の地点がパネルなど他の要素に遮られず、本当にオーバーレイ自身であること
      const probeX = Math.round(box!.x / 2);
      const probeY = Math.round(height / 2);
      const hitsOverlay = await page.evaluate(
        ({ x, y }) => !!document.elementFromPoint(x, y)?.closest(".comp-drawer-overlay"),
        { x: probeX, y: probeY },
      );
      expect(hitsOverlay).toBe(true);
    });

    test("C4: オーバーレイを押すと絞り込みパネルが閉じる（K2・今までは押す場所が無かった）", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);

      const box = await panel.boundingBox();
      expect(box).not.toBeNull();
      const probeX = Math.round(box!.x / 2);
      const probeY = Math.round(height / 2);

      await page.locator(".comp-drawer-overlay").click({ position: { x: probeX, y: probeY } });
      await expect(page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open')).toHaveCount(0);
    });

    test("C5: 選択画面のチェック行の高さが61px以上・xがパネル左端と一致・幅がパネル幅と一致（直す前は赤=44px）", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);
      const panelBox = await panel.boundingBox();
      expect(panelBox).not.toBeNull();

      await panel.getByTestId("viewer-provider-row").click();
      const firstOptionId = `viewer-provider-options-option-${fixture.providers[0]}`;
      const row = rowLocatorOf(panel, firstOptionId);
      await expect(row).toBeVisible();

      const rowBox = await row.boundingBox();
      expect(rowBox).not.toBeNull();
      expect(rowBox!.height).toBeGreaterThanOrEqual(EXPECTED_ROW_MIN_H);

      // 左端はパネルの左端と一致（本文の左余白24pxが残っていればここで落ちる）。
      // 縦スクロールバーは右側に出るため、この判定はスクロールバーの有無に左右されない
      expect(Math.abs(rowBox!.x - panelBox!.x)).toBeLessThanOrEqual(1);

      // 幅はパネル幅と同じ（スクロールバーが場所を取る場合はその分だけ狭くなるので許容を置く）
      expect(rowBox!.width).toBeLessThanOrEqual(panelBox!.width + 1);
      expect(rowBox!.width).toBeGreaterThanOrEqual(panelBox!.width - SCROLLBAR_ALLOWANCE);

      // スクロールバーに左右されない厳密な判定: 同じスクロール枠の中にある見出し
      // （本文の余白の内側に残る）との差が、ちょうど左右の余白2つ分であること
      const head = panel.locator(".comp-multiselect__inline-head");
      await expect(head).toBeVisible();
      const headBox = await head.boundingBox();
      expect(headBox).not.toBeNull();
      const padX = await drawerBodyPadX(page);
      expect(Math.abs(rowBox!.width - headBox!.width - padX * 2)).toBeLessThanOrEqual(1);
    });

    test("C6: 行の文字の左端が行の左から48px（直す前は赤=32px）", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);

      await panel.getByTestId("viewer-provider-row").click();
      const firstOptionId = `viewer-provider-options-option-${fixture.providers[0]}`;
      const row = rowLocatorOf(panel, firstOptionId);
      const text = row.locator(".comp-multiselect__option-text");
      await expect(text).toBeVisible();

      const rowBox = await row.boundingBox();
      const textBox = await text.boundingBox();
      expect(rowBox).not.toBeNull();
      expect(textBox).not.toBeNull();
      expect(Math.abs(textBox!.x - rowBox!.x - EXPECTED_TEXT_LEFT)).toBeLessThanOrEqual(1);
    });

    test("C7: 行の文字の大きさが14.4px（直す前は赤=13.6px）", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);

      await panel.getByTestId("viewer-provider-row").click();
      const firstOptionId = `viewer-provider-options-option-${fixture.providers[0]}`;
      const text = rowLocatorOf(panel, firstOptionId).locator(".comp-multiselect__option-text");
      await expect(text).toBeVisible();

      expect(await text.evaluate((el) => getComputedStyle(el).fontSize)).toBe(EXPECTED_FONT_SIZE);
    });

    test("C8: 行はどこを押しても選べる（文字の上・左48pxの枠の余白を押しても選択状態が変わる）", async ({ page }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);

      await panel.getByTestId("viewer-provider-row").click();
      const firstOptionId = `viewer-provider-options-option-${fixture.providers[0]}`;
      const checkbox = panel.getByTestId(firstOptionId);
      await expect(checkbox).toBeVisible();
      await expect(checkbox).not.toBeChecked();

      const text = rowLocatorOf(panel, firstOptionId).locator(".comp-multiselect__option-text");
      await expect(text).toBeVisible();
      await text.click();
      await expect(checkbox).toBeChecked();

      // 左48pxの枠（.comp-multiselect__check-col）はチェックそのものより広い。その余白部分
      // （行の左から8px・行の縦中央）を押してもチェックの外側が選べることを確かめる（別の行で検証）
      const secondOptionId = `viewer-provider-options-option-${fixture.providers[1]}`;
      const secondCheckbox = panel.getByTestId(secondOptionId);
      await expect(secondCheckbox).toBeVisible();
      await expect(secondCheckbox).not.toBeChecked();
      const secondRow = rowLocatorOf(panel, secondOptionId);
      const secondRowBox = await secondRow.boundingBox();
      expect(secondRowBox).not.toBeNull();
      await page.mouse.click(secondRowBox!.x + 8, secondRowBox!.y + secondRowBox!.height / 2);
      await expect(secondCheckbox).toBeChecked();
    });

    test("C9: 空振り防止 — 行を44pxに戻す／打ち消し幅(bleed)を0に戻すとC5の判定が落ちることを同じ検査の中で確かめる", async ({
      page,
    }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);
      const panelBox = await panel.boundingBox();
      expect(panelBox).not.toBeNull();

      await panel.getByTestId("viewer-provider-row").click();
      const firstOptionId = `viewer-provider-options-option-${fixture.providers[0]}`;
      const row = rowLocatorOf(panel, firstOptionId);
      await expect(row).toBeVisible();
      // 直した後は61px以上であること（C5 と同じ判定が今は通ることの前提）
      const before = await row.boundingBox();
      expect(before).not.toBeNull();
      expect(before!.height).toBeGreaterThanOrEqual(EXPECTED_ROW_MIN_H);

      // 直す前の値（44px）に戻すと、同じ判定（61px以上）が落ちることを確かめる
      await page.addStyleTag({ content: ".comp-multiselect__option--inline { min-height: 44px !important; }" });
      const after = await row.boundingBox();
      expect(after).not.toBeNull();
      expect(after!.height).toBeLessThan(EXPECTED_ROW_MIN_H);

      // 高さの空振り防止を確かめた後、打ち消し幅(bleed)を0に戻す（元に戻す必要は無い。
      // 判定の順番に注意: 高さを先に崩し、そのうえで幅の判定を崩す）。
      // C5 の「行の左端＝パネルの左端」と「見出しとの幅の差＝余白2つ分」の両方が、
      // 本文の左右余白が復活したぶんだけ落ちることを確かめる
      const head = panel.locator(".comp-multiselect__inline-head");
      await expect(head).toBeVisible();
      await page.addStyleTag({
        content: ".viewer-filter-options { --comp-multiselect-list-bleed: 0px !important; }",
      });
      const bleedRowBox = await row.boundingBox();
      const bleedHeadBox = await head.boundingBox();
      expect(bleedRowBox).not.toBeNull();
      expect(bleedHeadBox).not.toBeNull();
      const padX = await drawerBodyPadX(page);

      expect(Math.abs(bleedRowBox!.x - panelBox!.x)).toBeGreaterThan(1);
      expect(Math.abs(bleedRowBox!.width - bleedHeadBox!.width - padX * 2)).toBeGreaterThan(1);
    });

    test("C10: ページの横はみ出しが無い", async ({ page }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);
      await panel.getByTestId("viewer-provider-row").click();

      await expectNoPageOverflow(page);
    });

    test("C12: root の「24時間以内のみ」の行が変わっていない（4-6の歯止め・61pxになっていないこと）", async ({
      page,
    }) => {
      await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);

      const check = panel.getByTestId("viewer-fresh-check");
      await expect(check).toBeVisible();
      const row = rowLocatorOf(panel, "viewer-fresh-check");
      const rowBox = await row.boundingBox();
      expect(rowBox).not.toBeNull();
      expect(rowBox!.height).toBeGreaterThanOrEqual(FRESH_CHECK_MIN_H);
      expect(rowBox!.height).toBeLessThanOrEqual(FRESH_CHECK_MAX_H);

      const textLeft = await freshCheckTextLeftOffset(row);
      expect(textLeft).not.toBeNull();
      expect(Math.abs(textLeft! - FRESH_CHECK_TEXT_LEFT)).toBeLessThanOrEqual(1);
    });

    test("C13: .comp-multiselect__option:hover の規則が (hover: hover) の中にある（sticky hover対策・K6）", async ({
      page,
    }) => {
      await gotoViewer(page, { width, height });

      // 実際にホバーを再現するのではなく、読み込み済みスタイルシートを静的に辿って
      // 対象の規則が @media (hover: hover) の中にあることだけを確かめる
      const result = await page.evaluate(() => {
        const target = ".comp-multiselect__option:hover";
        type Hit = { found: true; mediaText: string | null };
        // 目的の規則は @media の「中」にあるので、入れ子を辿らないと必ず見つからない。
        // 見つけた時点で、それを囲っている一番内側の @media の条件を返す
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
      // 圧縮で空白が消えても判定が変わらないよう、空白を落として比べる
      expect((result.mediaText ?? "").replace(/\s+/g, "")).toBe("(hover:hover)");
    });

    test("C14: 絞り込みパネルの本文（.comp-drawer-body）に内部の横はみ出しが無い（root画面・提供者の選択画面の両方）", async ({
      page,
    }) => {
      const fixture = await gotoViewer(page, { width, height });
      const panel = await openFilterDrawer(page, width);
      const body = panel.locator(".comp-drawer-body");
      await expect(body).toBeVisible();

      const bodyFitsNoScroll = () => body.evaluate((el) => el.scrollWidth <= el.clientWidth);

      // root画面（絞り込みを開いた直後）
      expect(await bodyFitsNoScroll()).toBe(true);

      // 提供者の選択画面（パネルが61px狭くなる分、金額・数量の2入力がはみ出す恐れがある）
      await panel.getByTestId("viewer-provider-row").click();
      const firstOptionId = `viewer-provider-options-option-${fixture.providers[0]}`;
      await expect(panel.getByTestId(firstOptionId)).toBeVisible();

      expect(await bodyFitsNoScroll()).toBe(true);
    });
  });
}
