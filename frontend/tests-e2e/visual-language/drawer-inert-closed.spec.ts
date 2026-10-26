/**
 * visual-language/drawer-inert-closed.spec.ts
 * — 閉じている `Drawer` の中身を「無い物」として扱う（宿題 D5）の画面検査
 *
 * design: docs/handoff/drawer-inert-when-closed/design.md 設計⑤ Acceptance Criteria B1・B2・B3。
 * recon: docs/handoff/drawer-inert-when-closed/recon.md（現物調査）。
 * 単体テスト（D5-C1〜D5-C4）は frontend/src/hooks/useFocusTrap.test.tsx（このファイルの対象外）。
 * 単体では測れない「本物の Tab がどう動くか」をここで測る（design.md ⑤ 冒頭）。
 *
 * 舞台は閲覧ページ（/viewer/）。スマホ幅で開いた直後、絞り込みドロワー（filterView="root"）と
 * シリーズ・並び替えドロワー（choicePanel="none" のときはシリーズの一覧）の**両方が閉じたまま
 * 同時に DOM に居る**（recon.md §4）。「提供者の選択画面」（viewer-focus-trap.spec.ts と同じ経路）には
 * 入らないので、この2枚の閉じたパネルは**既定の gotoViewer の応答のまま**（viewer-helpers.ts。
 * フィクスチャを作り変える必要は無い）。
 *
 * 「10個以上」の内訳（既定フィクスチャで実測・design.md ⑤「前提を必ず assert する」）:
 *   絞り込みドロワー（閉じている root 画面）＝ ✕ ボタン + 24時間以内チェック + 仕入元の行 +
 *     コンディションの行 + 価格の上下限（2） + 数量の上下限（2） + 言語切替 = 9
 *   シリーズ・並び替えドロワー（閉じている既定のシリーズ一覧。series はフィクスチャで常に
 *     空文字のため tabs が空＝「すべて」の1行のみ）＝ ✕ ボタン + 「すべて」の行 = 2
 *   合計 11（>=10）。2枚のパネルを合わせた数であることに注意（1枚だけでは足りない）。
 *
 * スマホ幅が必要なので project の既定幅に関わらず spec 側で明示的に setViewportSize する
 * （design ⑤「作り方」・frontend/AGENTS.md の作法。viewer-focus-trap.spec.ts と同じ理由）。
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { gotoViewer } from "./viewer-helpers";

/** スマホ幅（絞り込みドロワー・シリーズ/並び替えドロワーは isMobile のときだけ存在する） */
const MOBILE = { width: 390, height: 844 };

/** useFocusTrap.ts の FOCUSABLE_SELECTOR と同じ並び（検査側の写し） */
const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

/** 閉じている `.comp-drawer-panel`（`--open` が付いていないもの） */
function closedPanels(page: Page) {
  return page.locator(".comp-drawer-panel:not(.comp-drawer-panel--open)");
}

/** 開いている `.comp-drawer-panel--open` */
function openPanel(page: Page) {
  return page.locator(".comp-drawer-panel.comp-drawer-panel--open");
}

/** 閉じているパネル（複数）すべての `inert` を読む */
async function closedPanelInertFlags(page: Page): Promise<boolean[]> {
  return page.evaluate(() => {
    const panels = Array.from(
      document.querySelectorAll<HTMLElement>(".comp-drawer-panel:not(.comp-drawer-panel--open)"),
    );
    return panels.map((p) => p.inert);
  });
}

/** 閉じているパネル（複数）の中にあるフォーカスできる要素の総数（design.md ⑤「10個以上」の前提） */
async function countFocusableInClosedPanels(page: Page): Promise<number> {
  return page.evaluate((selector) => {
    const panels = Array.from(
      document.querySelectorAll<HTMLElement>(".comp-drawer-panel:not(.comp-drawer-panel--open)"),
    );
    return panels.reduce((sum, panel) => sum + panel.querySelectorAll(selector).length, 0);
  }, FOCUSABLE_SELECTOR);
}

/**
 * 閉じたパネルの**外**にあるフォーカスできる要素の総数。
 *
 * B2 で Tab を何回押すかをこの数から決める（design.md ⑤）。**固定回数（20回など）にしてはいけない**:
 * 閉じたパネルは `document.body` の末尾へ描かれる（ポータル）ため DOM 順で画面の部品より後ろにあり、
 * 手前の部品が押した回数より多いと**閉じたパネルまで届かないまま「入った回数0」が成立する**＝
 * 直す前でも緑になり得る（便6・便7 と同じ「空振りで緑」）。
 * 「外側の数＋3回」押せば、Tab は DOM 順に進むので**外側を使い切った次の回は必ず閉じたパネルに入る**
 * ＝直す前は赤になることが作りで保証される。
 */
async function countFocusableOutsideClosedPanels(page: Page): Promise<number> {
  return page.evaluate((selector) => {
    const all = Array.from(document.querySelectorAll<HTMLElement>(selector));
    return all.filter((el) => !el.closest(".comp-drawer-panel:not(.comp-drawer-panel--open)")).length;
  }, FOCUSABLE_SELECTOR);
}

/** いま document.activeElement が「閉じたパネルの中」かどうか＋見分けられる印（data-testid優先） */
async function readFocusLocation(page: Page): Promise<{ insideClosedPanel: boolean; signature: string }> {
  return page.evaluate(() => {
    const active = document.activeElement;
    const insideClosedPanel = !!(
      active && active.closest(".comp-drawer-panel:not(.comp-drawer-panel--open)")
    );
    const signature = active
      ? `${active.tagName}:${active.getAttribute("data-testid") ?? ""}`
      : "none";
    return { insideClosedPanel, signature };
  });
}

test.describe("visual-language: 閉じている Drawer の中身を無い物として扱う（宿題 D5）", () => {
  test("B1: 開いた直後、閉じた .comp-drawer-panel が2枚あり、両方の inert が true（前提の固定）", async ({ page }) => {
    await page.setViewportSize(MOBILE);
    await gotoViewer(page);

    // 前提1: 閉じたパネルが2枚（絞り込み・シリーズ/並び替え）
    await expect(closedPanels(page)).toHaveCount(2);
    // 前提2: 開いているパネルは0枚（両方とも閉じて始まる。recon.md §4）
    await expect(openPanel(page)).toHaveCount(0);
    // 前提3: その中にフォーカスできる要素が10個以上ある（ファイル冒頭の内訳を参照。空振り防止）
    const focusableCount = await countFocusableInClosedPanels(page);
    expect(focusableCount).toBeGreaterThanOrEqual(10);

    // 本題: 両方の inert が true
    const flags = await closedPanelInertFlags(page);
    expect(flags).toHaveLength(2);
    expect(flags.every((v) => v === true)).toBe(true);
  });

  test("B2: 外側を使い切るまで Tab を押しても、現在地が閉じたパネルの中に入らない（0回・かつ現在地は実際に動く）", async ({ page }) => {
    await page.setViewportSize(MOBILE);
    await gotoViewer(page);

    // B1 と同じ前提をこのテスト単体でも確かめる（このテストだけ実行しても空振りで緑にならないように）
    await expect(closedPanels(page)).toHaveCount(2);
    const focusableCount = await countFocusableInClosedPanels(page);
    expect(focusableCount).toBeGreaterThanOrEqual(10);

    // 押す回数は「閉じたパネルの外にある数＋3」。固定回数にしない理由は
    // countFocusableOutsideClosedPanels の説明を参照（直す前が赤になることを作りで保証する）
    const outsideCount = await countFocusableOutsideClosedPanels(page);
    const presses = outsideCount + 3;
    // 前提: 回数が現実的な範囲に収まっている（膨れていたら測り方を見直す＝黙って truncate しない）
    expect(outsideCount).toBeGreaterThan(0);
    expect(presses).toBeLessThanOrEqual(200);

    const signatures: string[] = [];
    let enteredClosedPanelCount = 0;
    for (let i = 0; i < presses; i++) {
      await page.keyboard.press("Tab");
      const { insideClosedPanel, signature } = await readFocusLocation(page);
      if (insideClosedPanel) enteredClosedPanelCount++;
      signatures.push(signature);
    }

    // 本題: 閉じたパネルの中に入った回数は0
    expect(enteredClosedPanelCount).toBe(0);
    // 「0回」が、Tab がどこにも動かずに成立した見かけの0回ではないことを確かめる
    // （design.md ⑤「Tab が実際に進んでいること」）: 現在地が複数の場所に動いたこと
    expect(new Set(signatures).size).toBeGreaterThan(1);
  });

  test("B3: 絞り込みを開くと、開いた側の inert は false・その中の要素に Tab で入れる", async ({ page }) => {
    await page.setViewportSize(MOBILE);
    await gotoViewer(page);

    await page.getByTestId("viewer-filter-toggle").click();

    const open = openPanel(page);
    await expect(open).toHaveCount(1);
    const isInert = await open.evaluate((el) => (el as HTMLElement).inert);
    expect(isInert).toBe(false);

    // 開いた直後は既存の仕組み（Drawer.tsx の「開いたら先頭へ」effect）でパネル内に居るはずだが、
    // ここでは「Tab で入れる」こと自体を機械確認するため、まず Tab を押してから現在地を見る
    await page.keyboard.press("Tab");
    const insideOpenPanel = await page.evaluate(() => {
      const active = document.activeElement;
      const openEl = document.querySelector(".comp-drawer-panel.comp-drawer-panel--open");
      return !!(openEl && active && openEl.contains(active));
    });
    expect(insideOpenPanel).toBe(true);
  });
});
