/**
 * ADR-1016 改訂 2026-10-19: 行が時間の枠から外れる時刻に 1 回読み直す。
 * - seconds が null なら何もしない
 * - 待ち時間 = clamp(seconds, 60, 86_400) 秒 + 0〜3 秒のずれ（最短 60 秒で連続読み直しを防ぐ・setTimeout の上限内）
 * - 裏のタブの間は保留し、表に戻ったとき保留があれば 1 回だけ呼ぶ（useRealtimeRefresh と同じ）
 * - seconds か resetKey が変わる（＝読み直した）たびに張り直す
 */
import { useEffect, useRef } from "react";

export const EXPIRY_MIN_S = 60;
export const EXPIRY_MAX_S = 86_400;

export function useExpiryRefresh(
  seconds: number | null,
  reload: () => void,
  jitterMs: number,
  resetKey: number,
): void {
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  useEffect(() => {
    if (seconds === null) return;
    let pending = false;
    const waitMs = Math.min(Math.max(seconds, EXPIRY_MIN_S), EXPIRY_MAX_S) * 1_000 + jitterMs;

    const timer = setTimeout(() => {
      if (document.hidden) {
        pending = true;
        return;
      }
      reloadRef.current();
    }, waitMs);
    const onVisible = () => {
      if (!document.hidden && pending) {
        pending = false;
        reloadRef.current();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [seconds, jitterMs, resetKey]);
}
