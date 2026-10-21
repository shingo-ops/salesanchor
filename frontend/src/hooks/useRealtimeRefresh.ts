/**
 * ADR-1016: 合図を受けたら reload を呼ぶ。
 * - 自分が起こした変更（origin が自分の clientId）は無視
 * - 既定 1.5 秒（呼び出し元で変えられる）の間に来た合図は 1 回にまとめる
 * - 裏のタブ（document.hidden）の間は保留し、表に戻ったとき保留があれば 1 回だけ呼ぶ
 * - 再接続の通知が来たら 1 回呼ぶ
 * - Provider の外では何もしない
 */
import { useContext, useEffect, useRef } from "react";

import { RealtimeContext, type RealtimeEvent } from "../lib/realtime/context";

export const REALTIME_DEBOUNCE_MS = 1_500;

export function useRealtimeRefresh(
  topics: readonly string[],
  reload: () => void,
  options?: { debounceMs?: number },
): void {
  const debounceMs = options?.debounceMs ?? REALTIME_DEBOUNCE_MS;
  const rt = useContext(RealtimeContext);
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  const topicsKey = topics.join("|");

  useEffect(() => {
    if (!rt) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let pending = false;

    const fire = () => {
      timer = null;
      if (document.hidden) {
        pending = true;
        return;
      }
      pending = false;
      reloadRef.current();
    };
    const schedule = () => {
      if (timer) return;
      timer = setTimeout(fire, debounceMs);
    };
    const onVisible = () => {
      if (!document.hidden && pending) {
        pending = false;
        reloadRef.current();
      }
    };

    const unsubscribe = rt.subscribe(topicsKey ? topicsKey.split("|") : [], (ev: RealtimeEvent) => {
      if ("reconnected" in ev) {
        schedule();
        return;
      }
      if (ev.origin !== null && ev.origin === rt.clientId) return;
      schedule();
    });
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      unsubscribe();
      document.removeEventListener("visibilitychange", onVisible);
      if (timer) clearTimeout(timer);
    };
  }, [rt, topicsKey, debounceMs]);
}
