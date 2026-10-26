/**
 * visual-language/viewer-focus-trap.spec.ts
 * — かぶせて出すパネルの出口封じを1か所にまとめ、行が消えても外へ出さない（宿題 C8）の画面検査
 *
 * design: docs/handoff/viewer-focus-trap/design.md 設計⑤ Acceptance Criteria B1・B2。
 * recon: docs/handoff/viewer-focus-trap/recon.md §3・§4（「行が消える」経路の現物調査）。
 * 単体テスト（C1〜C11）は frontend/src/hooks/useFocusTrap.test.tsx（このファイルの対象外）。
 *
 * シナリオ（design.md ⑤「B1・B2 の作り方（確定事項）」）:
 *   閲覧ページ → 絞り込み → 提供者の選択画面 → 候補の1つにフォーカス →
 *   自動読み直し（60秒間隔・frontend/src/pages/viewer/useViewerAutoRefresh.ts:8）で
 *   その候補が在庫から消える → document.activeElement が <body> に落ちる（B1・前提の固定）→
 *   その直後に Tab を押すとパネル内の**先頭**（戻るボタン）、Shift+Tab なら**末尾**（決定するボタン）へ
 *   連れ戻される（B2・B2'・本題。直す前は赤）。
 *
 * 「パネルの中に居る」だけを見てはいけない（独立審査 B-1）: 本物のブラウザは消えた要素の位置を
 * 順次フォーカス移動の起点として覚えているため、素の Tab でも**消えた候補の次の候補**（＝パネルの中）へ
 * 入り得る＝直す前でも緑になり得る。先頭／末尾そのものを assert すれば、素の移動では到達できないので
 * 「連れ戻した」ときだけ緑になる（readPanelFocusState の説明を参照）。
 *
 * 60秒は既定のテスト制限時間（30秒）を超えるため実時間では待たない。page.clock で仮想時計を進める
 * （package-lock.json 固定の 1.59.1 に clock.install / fastForward が実在することを設計時に確認済み）。
 * 対象の提供者を途中から欠落させるため、tests-e2e/utils/api-mock.ts の MockEntry が
 * 関数（(route) => ...）を受け付けることを使う（design.md ⑤「作り方」）。
 * **切り替えは「取得回数」ではなく検査側の旗で行う**（画面を開くだけで在庫取得が2回走るため。
 * openProviderScreenWithFocusedCandidate の説明を参照＝CI 1往復目で実測した事実）。
 *
 * 提供者の選択画面（絞り込みドロワー）は frontend/src/pages/viewer/InventoryView.tsx の
 * `{isMobile && (<Drawer ...>)}` の中にしかない（isMobile は frontend/src/hooks/useIsMobile.ts が
 * BREAKPOINTS.MOBILE_MAX=767px で判定）。tablet(768px)・desktop(1280px) の project では
 * この Drawer 自体が存在しないため、3 project のどこで走っても同じ経路を検査できるよう
 * spec 側で明示的にスマホ幅（390×844）へ setViewportSize する（design ⑤冒頭・守ること6「幅に
 * 依存する分岐が必要なら spec 側で page.setViewportSize を書く」の適用。project の既定幅は使わない）。
 *
 * 開いている方のパネルの特定は既存 spec（viewer-choice-sheet.spec.ts）と同じ作法で
 * `.comp-drawer-panel--open` に絞る（閉じた Drawer も DOM に常在するため、
 * `getByTestId("supplier-drawer")` だけでは strict mode violation になる）。
 */
import { expect, test } from "@playwright/test";
import type { Page, Route } from "@playwright/test";
import { mockApi } from "../utils/api-mock";
import {
  installViewerToken,
  makeConditionValues,
  makeProviderNames,
  makeViewerRows,
} from "./viewer-helpers";
import type { ViewerInventoryResponse } from "../../src/pages/viewer/types";

/** スマホ幅（提供者の選択画面＝絞り込みドロワーは isMobile のときだけ存在する。ファイル冒頭の説明参照） */
const MOBILE = { width: 390, height: 844 };

/** 開いている方のパネル（絞り込みドロワーは data-testid="supplier-drawer" を持ち DOM に常にマウントされるため、
 *  .comp-drawer-panel--open で絞る。frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts と同じ作り） */
function openPanel(page: Page) {
  return page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
}

/**
 * 閲覧ページを開き、絞り込み→提供者の選択画面まで進め、候補の1つ（targetOptionTestId）へ
 * フォーカスを当てた状態で返す。返り値の `dropTarget()` を呼ぶと、**それ以降の**在庫取得だけ
 * その候補の提供者を欠落させる（design.md ⑤「2回目の応答だけ候補を減らす」）。
 *
 * **「2回目の応答」を取得回数で数えてはいけない（CI 1往復目で実測）**: 画面を開くだけで
 * 在庫取得が**2回**走る（frontend/src/pages/viewer/main.tsx:13 の `React.StrictMode` が
 * 開発サーバで effect を2回流すため。画面検査は開発サーバ相手に走る）。CI の失敗時の画面には
 * 最初から Provider01 が居らず、**2回目の応答が初期表示に使われていた**＝回数で切り替えると
 * 前提が崩れた状態から始まる。検査が「いつ消えてほしいか」を自分で決める形（この旗）にすれば、
 * 初期取得が何回でも成り立つ。
 */
async function openProviderScreenWithFocusedCandidate(
  page: Page,
): Promise<{ targetOptionTestId: string; dropTarget: () => void }> {
  const providers = makeProviderNames(6);
  const conditions = makeConditionValues(2);
  // providers はゼロ埋め済みで辞書順＝distinctValues の並びと一致するため、先頭 = providers[0]
  const target = providers[0];
  const initialRows = makeViewerRows(providers.length * 2, providers, conditions);
  const rowsWithoutTarget = initialRows.filter((r) => r.provider !== target);

  await page.setViewportSize(MOBILE);

  // viewer はアプリ本体の Firebase Auth を使わず localStorage のトークンだけで判定する。
  // 値の重複を作らないため viewer-helpers の共通処理をそのまま使う（審査 N-4）
  await installViewerToken(page);

  let dropped = false;
  await mockApi(page, {
    "GET /viewer/inventory": async (route: Route) => {
      const body: ViewerInventoryResponse = {
        updated_at: new Date().toISOString(),
        fresh_window_hours: 24,
        rows: dropped ? rowsWithoutTarget : initialRows,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    },
  });

  // 60秒間隔の自動読み直し（useViewerAutoRefresh.ts:8）をテストの制限時間内で動かすため、
  // ページ遷移前に仮想時計を入れる（design.md ⑤「作り方」）
  await page.clock.install({ time: Date.now() });

  await page.goto("/viewer/");

  const filterToggle = page.getByTestId("viewer-filter-toggle");
  await expect(filterToggle).toBeVisible();
  await filterToggle.click();

  const panel = openPanel(page);
  await expect(panel).toHaveCount(1);

  await panel.getByTestId("viewer-provider-row").click();

  const targetOptionTestId = `viewer-provider-options-option-${target}`;
  const option = panel.getByTestId(targetOptionTestId);
  await expect(option).toBeVisible();

  await option.focus();
  const isFocused = await option.evaluate((el) => el === document.activeElement);
  expect(isFocused).toBe(true);

  return {
    targetOptionTestId,
    dropTarget: () => {
      dropped = true;
    },
  };
}

/** document.activeElement が「どこでもない」（<body>・<html>・null）になっていること */
async function expectActiveElementIsNowhere(page: Page): Promise<void> {
  const tag = await page.evaluate(() => document.activeElement?.tagName ?? null);
  expect(tag === null || tag === "BODY" || tag === "HTML").toBe(true);
}

/**
 * いま開いているパネルの中の「現在地」を、**どの要素か分かる形**で測る（審査 B-1 の直し）。
 *
 * `panel.contains(activeElement)` だけでは不足する: 本物のブラウザは消えた要素の位置を
 * 順次フォーカス移動の起点として覚えており、素の Tab でも**消えた候補の次の候補**（＝パネルの中）へ
 * 入り得る。つまり直す前でも緑になり得て、何も確かめていないことになる。
 * そこで「パネル内の先頭／末尾そのもの」に入ったことを assert する:
 *   - 先頭（`drawer-back`）は消えた候補より DOM 順で**前**＝素の Tab では到達できない
 *   - 末尾（`viewer-filter-apply`）は消えた候補より**後ろの最後**＝素の Shift+Tab では到達できない
 * どちらも「連れ戻した」ときだけ成立するので、直す前は必ず赤になる。
 */
async function readPanelFocusState(page: Page): Promise<{
  activeTestId: string | null;
  firstTestId: string | null;
  lastTestId: string | null;
  isFirst: boolean;
  isLast: boolean;
}> {
  return page.evaluate(() => {
    // useFocusTrap.ts の FOCUSABLE_SELECTOR と同じ並び（検査側の写し）
    const SELECTOR = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      "[tabindex]:not([tabindex='-1'])",
    ].join(",");
    const panel = document.querySelector<HTMLElement>(
      '[data-testid="supplier-drawer"].comp-drawer-panel--open',
    );
    if (!panel) return { activeTestId: null, firstTestId: null, lastTestId: null, isFirst: false, isLast: false };
    const focusable = Array.from(panel.querySelectorAll<HTMLElement>(SELECTOR)).filter(
      (el) => !el.closest("[aria-hidden='true']"),
    );
    const first = focusable[0] ?? null;
    const last = focusable[focusable.length - 1] ?? null;
    const active = document.activeElement;
    const tid = (el: Element | null) => el?.getAttribute("data-testid") ?? null;
    return {
      activeTestId: tid(active),
      firstTestId: tid(first),
      lastTestId: tid(last),
      isFirst: !!first && active === first,
      isLast: !!last && active === last,
    };
  });
}

test.describe("visual-language: 閲覧ページ フォーカストラップ（宿題 C8）", () => {
  test("B1: 候補にフォーカス→自動読み直しで消える→activeElement が <body> になる（前提の固定）", async ({ page }) => {
    const { targetOptionTestId, dropTarget } = await openProviderScreenWithFocusedCandidate(page);

    dropTarget();
    await page.clock.fastForward(60_000);

    // 前提1: 候補が実際に DOM から消えた（空振り防止・守ること4）
    await expect(page.getByTestId(targetOptionTestId)).toHaveCount(0);
    // 前提2: フォーカスが「どこでもない」状態に落ちた
    await expectActiveElementIsNowhere(page);
  });

  test("B2: B1 の直後に Tab を押すと、パネル内の先頭（戻るボタン）へ連れ戻される（本題）", async ({ page }) => {
    const { targetOptionTestId, dropTarget } = await openProviderScreenWithFocusedCandidate(page);

    dropTarget();
    await page.clock.fastForward(60_000);

    // B1 と同じ前提をこのテスト単体でも確かめる（このテストだけ実行しても空振りで緑にならないように）
    await expect(page.getByTestId(targetOptionTestId)).toHaveCount(0);
    await expectActiveElementIsNowhere(page);

    await page.keyboard.press("Tab");

    const state = await readPanelFocusState(page);
    // 前提3: パネル内の先頭が「戻るボタン」であること（DOM 順が変わったら黙って緑にならないよう固定）
    expect(state.firstTestId).toBe("drawer-back");
    // 本題: 先頭そのものに入った（素の Tab は前へ戻れないので、連れ戻したときだけ成立する）
    expect(state.activeTestId).toBe("drawer-back");
    expect(state.isFirst).toBe(true);
  });

  test("B2': B1 の直後に Shift+Tab を押すと、パネル内の末尾（決定するボタン）へ連れ戻される", async ({ page }) => {
    const { targetOptionTestId, dropTarget } = await openProviderScreenWithFocusedCandidate(page);

    dropTarget();
    await page.clock.fastForward(60_000);

    await expect(page.getByTestId(targetOptionTestId)).toHaveCount(0);
    await expectActiveElementIsNowhere(page);

    await page.keyboard.press("Shift+Tab");

    const state = await readPanelFocusState(page);
    // 前提3': パネル内の末尾が footer の「決定する」であること
    expect(state.lastTestId).toBe("viewer-filter-apply");
    // 本題: 末尾そのものに入った（素の Shift+Tab は後ろへ飛べないので、連れ戻したときだけ成立する）
    expect(state.activeTestId).toBe("viewer-filter-apply");
    expect(state.isLast).toBe(true);
  });
});
