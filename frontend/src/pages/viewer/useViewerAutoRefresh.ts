/**
 * 閲覧ページの在庫を1分ごとに読み直す（docs/handoff/viewer-auto-refresh/design.md）。
 * - enabled が false の間は何もしない（在庫表を出していない間）
 * - 裏のタブの間は呼ばずに保留し、表に戻ったとき保留があれば 1 回だけ呼ぶ
 */
import { useEffect, useRef } from "react";

export const VIEWER_REFRESH_MS = 60_000;

export function useViewerAutoRefresh(enabled: boolean, refresh: () => void): void {
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  useEffect(() => {
    if (!enabled) return;
    let pending = false;
    const timer = setInterval(() => {
      if (document.hidden) {
        pending = true;
        return;
      }
      refreshRef.current();
    }, VIEWER_REFRESH_MS);
    const onVisible = () => {
      if (!document.hidden && pending) {
        pending = false;
        refreshRef.current();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [enabled]);
}
