/**
 * useFocusTrap — かぶせて出すパネル（Drawer / Modal / Sheet）共通の出口封じ
 *
 * 宿題 C8（docs/handoff/viewer-filter-subscreen/design.md:318・便2の2回目審査 N1・非ブロック）の直し。
 * 3つの金型に一字一句同じコードが複製されていた（docs/handoff/viewer-focus-trap/recon.md §2）ため、
 * この1か所にまとめる（docs/handoff/viewer-focus-trap/design.md 4-1・4-2）。
 *
 * `FOCUSABLE_SELECTOR` / `getFocusableElements` / `getFirstFocusable` は
 * 旧 Drawer.tsx:212-228 の中身をそのまま移植（値・順序・[aria-hidden='true'] 除外も一字一句同じ）。
 */
import { useEffect, useLayoutEffect, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.closest("[aria-hidden='true']"),
  );
}

export function getFirstFocusable(container: HTMLElement): HTMLElement | null {
  return getFocusableElements(container)[0] ?? null;
}

/**
 * パネルの外へ Tab で出て行かせない（出口封じ）。
 *
 * 旧 Drawer.tsx:101-129 の `useEffect` を移植し、design.md 4-2 の枝を1本だけ足した:
 * 現在地が「どこでもない」（行が DOM から外れて `document.activeElement` が `<body>` 等へ
 * 落ちた状態。docs/handoff/viewer-focus-trap/recon.md §3・§4）とき、Tab を押した瞬間に
 * パネルの中へ連れ戻す（Tab なら先頭・Shift+Tab なら末尾＝進行方向に合わせる。design.md ⑨・PO決定）。
 *
 * 一方、現在地がパネルの外の「別の要素」（Popover・Modal など、document.body 直下へ
 * 別に描かれる他のポータル）に在るときは**何もしない**。ここを区別しないと、パネルの中から
 * 浮かぶ選択肢や確認窓を開いた画面でフォーカスを奪い返してしまい、直していない所を壊す
 * （design.md 4-2・T1）。
 *
 * `open` が true の間だけ購読する。後片付けは `removeEventListener` のみ（時間に頼る
 * 後始末は作らない。design.md ⑨「便2・PR (#4740) の失敗」）。
 * ※ PR 番号は (#...) の形で書く。括弧の無い番号は関所 guard-hex-increase が色コードと誤認する
 */
export function useFocusTrap(open: boolean, containerRef: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    if (!open) return;
    const panel = containerRef.current;
    if (!panel) return;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = getFocusableElements(panel);
      if (focusable.length === 0) { e.preventDefault(); return; }
      const first = focusable[0];
      const last  = focusable[focusable.length - 1];

      const active = document.activeElement;
      const inPanel = active instanceof Node && panel.contains(active);
      if (!inPanel) {
        // 現在地が「どこでもない」（行が消えて居場所が無い）ときだけ連れ戻す。
        // 別の要素（他のポータル）に居るときは何もしない（design.md 4-2・P2）。
        const nowhere = !active || active === document.body || active === document.documentElement;
        if (nowhere) {
          e.preventDefault();
          (e.shiftKey ? last : first).focus();
        }
        return;
      }

      if (e.shiftKey) {
        if (active === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleTab);
    return () => document.removeEventListener("keydown", handleTab);
  }, [open, containerRef]);
}

/**
 * 閉じている間だけ要素を無効化する（宿題 D5「閉じているパネルを『無い物』として扱う」の直し。
 * docs/handoff/drawer-inert-when-closed/design.md 4-2）。
 *
 * `open` の裏返しを `inert`（その枝をまるごと無効にする DOM の性質。Tab の通り道・読み上げ・クリックの
 * 3つを1つの指定でまとめて無効化する）として `containerRef` の要素に入れる。CSS には一切触れない
 * （design.md 4-1）ので、アニメーション（`transform` だけに掛かる `transition`）には影響しない。
 *
 * `ready`（＝描き先が決まったかどうか。呼び出し側は `portalTarget` を渡す）を引数に取り、
 * 依存配列にも入れる理由: `Drawer`／`Sheet` は描き先（`portalTarget`）を `useEffect` で後から決める
 * 2段構えのマウントのため、`open` だけを依存配列にすると「最初から閉じている回」（＝まさに今回
 * 直したい状態）で1度も実行されない（便7 の ⑫ E5 と同根の罠。design.md 4-2）。`ready` を依存配列に
 * 含めることで、描き先が決まった直後にもう一度実行させる。
 *
 * **`useLayoutEffect` を使う理由（独立審査 B-1 の直し。これを `useEffect` にしてはいけない）**:
 * 無効化の解除（`inert = false`）は、金型が持つ「開いたらパネル内の先頭へフォーカスを移す」処理より
 * **必ず先**に走らなければならない。React は同じ種類の effect を**書いた順**に流すため、`useEffect` だと
 * 閉→開の回に「先頭へフォーカス」→「無効化を解除」の順になり、**まだ無効な枝へ focus しようとして
 * 不発に終わる**（HTML 標準では inert な枝はフォーカス可能領域ではなく `focus()` は何もしない）。
 * 結果、カーソルが開いたパネルの外に取り残され、キーボードだけで使う人がパネルに入れなくなる。
 * `useLayoutEffect` は画面に反映される前・通常の effect より先に走るので、**呼び出し側で何行目に書いても
 * この順序が保たれる**（先例: `frontend/src/components/CheckboxControl.tsx:35`）。
 * この順序は `frontend/src/hooks/useFocusTrap.test.tsx` の D5-C5（本物のブラウザの決まりを模した検査）で固定している。
 */
export function useInertWhenClosed(
  open: boolean,
  containerRef: RefObject<HTMLElement | null>,
  ready: unknown,
): void {
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.inert = !open;
  }, [open, containerRef, ready]);
}
