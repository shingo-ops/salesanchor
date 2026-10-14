/**
 * useLongPress — 汎用の長押し検出 hook（受信箱 第4便・一覧の行の長押しメニュー用）
 *
 * `frontend/src/pages/inbox/useLongPressReveal.ts`（吹き出しのハート表示）と同じ作法
 * （500ms・pointerdown で計時・up/cancel/leave で取り消し・成立時だけ contextmenu を抑止）
 * を踏襲するが、以下 2 点が異なる:
 *
 *   1. pointerType で絞り込まない（既存は touch のみ。それだと自動検査から叩けないため、
 *      指でもマウスでも同じ経路で成立させる）
 *   2. pointerdown の座標から 10px 以上動いたら取り消す（スクロール中に出ないようにする）
 *
 * さらに、長押しが成立したらその後に続く click を無効化する（押しただけで行の既定動作
 * ＝会話を開く、が走らないようにするため）。
 *
 * 既存の useLongPressReveal.ts は改造しない（吹き出しのハートで稼働中のため）。
 */
import { useCallback, useEffect, useRef } from "react";
import type { MouseEvent, PointerEvent } from "react";

export const LONG_PRESS_MS = 500;
/** pointerdown からこの距離（px）以上動いたら長押しを取り消す（スクロール誤爆防止） */
export const LONG_PRESS_MOVE_THRESHOLD_PX = 10;

export interface LongPressAnchor {
  x: number;
  y: number;
}

export interface LongPressHandlers {
  onPointerDown: (e: PointerEvent) => void;
  onPointerMove: (e: PointerEvent) => void;
  onPointerUp: () => void;
  onPointerCancel: () => void;
  onPointerLeave: () => void;
  onContextMenu: (e: MouseEvent) => void;
  onClick: (e: MouseEvent) => void;
}

export interface UseLongPressOptions<T> {
  /** 長押しが成立したときに呼ぶ。anchor は pointerdown 時の画面座標 */
  onLongPress: (target: T, anchor: LongPressAnchor) => void;
}

export function useLongPress<T>({ onLongPress }: UseLongPressOptions<T>) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const firedRef = useRef(false);
  const startRef = useRef<LongPressAnchor | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    startRef.current = null;
  }, []);

  useEffect(() => clearTimer, [clearTimer]);

  const bind = useCallback((target: T): LongPressHandlers => ({
    onPointerDown: (e) => {
      firedRef.current = false;
      clearTimer();
      const anchor: LongPressAnchor = { x: e.clientX, y: e.clientY };
      startRef.current = anchor;
      timerRef.current = setTimeout(() => {
        firedRef.current = true;
        onLongPress(target, anchor);
      }, LONG_PRESS_MS);
    },
    onPointerMove: (e) => {
      const start = startRef.current;
      if (!start) return;
      const dx = e.clientX - start.x;
      const dy = e.clientY - start.y;
      if (Math.sqrt(dx * dx + dy * dy) >= LONG_PRESS_MOVE_THRESHOLD_PX) {
        // 指を滑らせた＝スクロールの意図とみなして取り消す
        clearTimer();
      }
    },
    onPointerUp: clearTimer,
    onPointerCancel: clearTimer,
    onPointerLeave: clearTimer,
    // 長押しが成立したときだけ OS のコンテキストメニューを抑止する
    onContextMenu: (e) => {
      if (firedRef.current) {
        e.preventDefault();
      }
    },
    // 長押しが成立した直後に続く click は無効化する（押しただけで既定動作が走らないように）
    onClick: (e) => {
      if (firedRef.current) {
        e.preventDefault();
        e.stopPropagation();
        firedRef.current = false;
      }
    },
  }), [clearTimer, onLongPress]);

  return { bind };
}
