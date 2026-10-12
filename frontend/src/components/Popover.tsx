/**
 * Popover — ポップオーバーパネル金型
 *
 * - トリガークリックで表示/非表示
 * - 外側クリックで閉じる
 * - document.body への Portal 描画
 * - placement: 'top' | 'bottom' | 'left' | 'right'（デフォルト 'bottom'）
 * - open / onOpenChange による制御式 API
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import "./Popover.css";

export type PopoverPlacement = "top" | "bottom" | "left" | "right";

export interface PopoverProps {
  /** トリガー要素 */
  children: ReactNode;
  /** ポップオーバー内容 */
  content: ReactNode;
  /** 表示位置（デフォルト: 'bottom'） */
  placement?: PopoverPlacement;
  /** 制御式: 開閉状態 */
  open?: boolean;
  /** 制御式: 開閉変更コールバック */
  onOpenChange?: (open: boolean) => void;
  /** ラッパー要素への追加クラス */
  className?: string;
}

function calcPosition(
  triggerRect: DOMRect,
  panelEl: HTMLDivElement,
  placement: PopoverPlacement,
): { top: number; left: number } {
  const panelW = panelEl.offsetWidth;
  const panelH = panelEl.offsetHeight;
  const gap = 6; // px — トリガーとパネルの間隔

  switch (placement) {
    case "top":
      return {
        top: triggerRect.top + window.scrollY - panelH - gap,
        left: triggerRect.left + window.scrollX + triggerRect.width / 2 - panelW / 2,
      };
    case "left":
      return {
        top: triggerRect.top + window.scrollY + triggerRect.height / 2 - panelH / 2,
        left: triggerRect.left + window.scrollX - panelW - gap,
      };
    case "right":
      return {
        top: triggerRect.top + window.scrollY + triggerRect.height / 2 - panelH / 2,
        left: triggerRect.right + window.scrollX + gap,
      };
    case "bottom":
    default:
      return {
        top: triggerRect.bottom + window.scrollY + gap,
        left: triggerRect.left + window.scrollX + triggerRect.width / 2 - panelW / 2,
      };
  }
}

export function Popover({
  children,
  content,
  placement = "bottom",
  open: controlledOpen,
  onOpenChange,
  className = "",
}: PopoverProps) {
  const isControlled = controlledOpen !== undefined;
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = isControlled ? controlledOpen : internalOpen;

  const triggerRef = useRef<HTMLSpanElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const [visible, setVisible] = useState(false);

  const setOpen = useCallback(
    (next: boolean) => {
      if (!isControlled) setInternalOpen(next);
      onOpenChange?.(next);
    },
    [isControlled, onOpenChange],
  );

  // 位置計算 — パネルが DOM に入ってから測る
  useEffect(() => {
    if (isOpen && triggerRef.current && panelRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPos(calcPosition(rect, panelRef.current, placement));
      // 次フレームで visible にしてアニメーションを発火させる
      requestAnimationFrame(() => setVisible(true));
    } else {
      setVisible(false);
    }
  }, [isOpen, placement]);

  // 外側クリックで閉じる
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (
        triggerRef.current?.contains(e.target as Node) ||
        panelRef.current?.contains(e.target as Node)
      ) {
        return;
      }
      setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen, setOpen]);

  const handleTriggerClick = () => setOpen(!isOpen);

  const panelCls = [
    "comp-popover",
    `comp-popover--${placement}`,
    visible ? "comp-popover--open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <span
        ref={triggerRef}
        className={className || undefined}
        style={{ display: "inline-flex" }}
        onClick={handleTriggerClick}
      >
        {children}
      </span>

      {isOpen &&
        createPortal(
          <div
            ref={panelRef}
            className={panelCls}
            role="dialog"
            style={{ top: pos.top, left: pos.left }}
          >
            {content}
          </div>,
          document.body,
        )}
    </>
  );
}
