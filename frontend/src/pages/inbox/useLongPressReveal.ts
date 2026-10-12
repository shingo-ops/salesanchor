/** タッチ端末: 吹き出しの長押しで、そのメッセージのハートを表示する（WhatsApp 公式の操作に準拠）。 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEvent, PointerEvent } from "react";

export const LONG_PRESS_MS = 500;

export interface LongPressHandlers {
  onPointerDown: (e: PointerEvent) => void;
  onPointerUp: () => void;
  onPointerCancel: () => void;
  onPointerLeave: () => void;
  onContextMenu: (e: MouseEvent) => void;
}

export function useLongPressReveal() {
  const [revealedId, setRevealedId] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const firedRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => clearTimer, [clearTimer]);

  const hide = useCallback(() => setRevealedId(null), []);

  const bind = useCallback((id: number): LongPressHandlers => ({
    onPointerDown: (e) => {
      if (e.pointerType !== "touch") return;
      firedRef.current = false;
      clearTimer();
      timerRef.current = setTimeout(() => {
        firedRef.current = true;
        setRevealedId(id);
      }, LONG_PRESS_MS);
    },
    onPointerUp: clearTimer,
    onPointerCancel: clearTimer,
    onPointerLeave: clearTimer,
    // 長押しが成立したときだけ OS のコンテキストメニューを抑止する
    onContextMenu: (e) => {
      if (firedRef.current) {
        e.preventDefault();
        firedRef.current = false;
      }
    },
  }), [clearTimer]);

  return { revealedId, hide, bind };
}
