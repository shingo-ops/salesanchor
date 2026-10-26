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
import { useEffect, type RefObject } from "react";

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
 * 後始末は作らない。design.md ⑨「便2・PR #4740 の失敗」）。
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
