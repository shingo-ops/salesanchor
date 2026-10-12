/**
 * Tooltip — ホバー時のツールチップ金型
 *
 * - children をラップし、ホバーで content（テキスト）を表示
 * - delay (ms) 後に表示、マウスアウトで即非表示
 * - document.body への Portal 描画
 * - placement: 'top' | 'bottom'（デフォルト 'top'）
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import "./Tooltip.css";

export type TooltipPlacement = "top" | "bottom";

export interface TooltipProps {
  /** ラップ対象要素 */
  children: ReactNode;
  /** ツールチップに表示するテキスト */
  content: string;
  /** 表示位置（デフォルト: 'top'） */
  placement?: TooltipPlacement;
  /** 表示までの遅延 ms（デフォルト: 150） */
  delay?: number;
}

const GAP = 4; // px — トリガーとツールチップの間隔

function calcTooltipPos(
  triggerRect: DOMRect,
  tipEl: HTMLDivElement,
  placement: TooltipPlacement,
): { top: number; left: number } {
  const tipW = tipEl.offsetWidth;
  const tipH = tipEl.offsetHeight;
  const left = triggerRect.left + window.scrollX + triggerRect.width / 2 - tipW / 2;

  if (placement === "bottom") {
    return {
      top: triggerRect.bottom + window.scrollY + GAP,
      left,
    };
  }
  // top (default)
  return {
    top: triggerRect.top + window.scrollY - tipH - GAP,
    left,
  };
}

export function Tooltip({
  children,
  content,
  placement = "top",
  delay = 150,
}: TooltipProps) {
  const [show, setShow] = useState(false);
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });

  const wrapperRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const handleMouseEnter = useCallback(() => {
    clearTimer();
    timerRef.current = setTimeout(() => setShow(true), delay);
  }, [clearTimer, delay]);

  const handleMouseLeave = useCallback(() => {
    clearTimer();
    setVisible(false);
    // visible → false のアニメーション後に DOM を消す
    setTimeout(() => setShow(false), 150);
  }, [clearTimer]);

  // 位置計算 & visible アニメーション
  useEffect(() => {
    if (show && wrapperRef.current && tipRef.current) {
      const rect = wrapperRef.current.getBoundingClientRect();
      setPos(calcTooltipPos(rect, tipRef.current, placement));
      requestAnimationFrame(() => setVisible(true));
    } else {
      setVisible(false);
    }
  }, [show, placement]);

  // アンマウント時にタイマー解除
  useEffect(() => () => clearTimer(), [clearTimer]);

  const tipCls = [
    "comp-tooltip",
    `comp-tooltip--${placement}`,
    visible ? "comp-tooltip--open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <span
        ref={wrapperRef}
        style={{ display: "inline-flex" }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {children}
      </span>

      {show &&
        createPortal(
          <div
            ref={tipRef}
            className={tipCls}
            role="tooltip"
            style={{ top: pos.top, left: pos.left }}
          >
            {content}
          </div>,
          document.body,
        )}
    </>
  );
}
