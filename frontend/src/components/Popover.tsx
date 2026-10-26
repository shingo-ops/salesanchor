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
  const margin = 8; // px — 画面端との最低間隔（ContextMenu.tsx:82 と同値・--space-2 と同値）

  // パネルは position: fixed、triggerRect は getBoundingClientRect() ＝どちらも画面基準。
  // scrollY/scrollX は足さない（design.md 4-1・recon §1）。
  let top: number;
  let left: number;
  switch (placement) {
    case "top":
      top = triggerRect.top - panelH - gap;
      left = triggerRect.left + triggerRect.width / 2 - panelW / 2;
      break;
    case "left":
      top = triggerRect.top + triggerRect.height / 2 - panelH / 2;
      left = triggerRect.left - panelW - gap;
      break;
    case "right":
      top = triggerRect.top + triggerRect.height / 2 - panelH / 2;
      left = triggerRect.right + gap;
      break;
    case "bottom":
    default:
      top = triggerRect.bottom + gap;
      left = triggerRect.left + triggerRect.width / 2 - panelW / 2;
      break;
  }

  // 画面の中へ収める（ContextMenu.tsx:76-95 と同じ考え方。placement の自動反転はしない。design.md 4-2）
  if (left + panelW + margin > window.innerWidth) {
    left = window.innerWidth - panelW - margin;
  }
  if (top + panelH + margin > window.innerHeight) {
    top = window.innerHeight - panelH - margin;
  }
  left = Math.max(margin, left);
  top = Math.max(margin, top);

  return { top, left };
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

  // 位置計算 — パネルが DOM に入ってから測る。開いている間は resize/scroll でも測り直す（design.md 4-4）
  useEffect(() => {
    if (!isOpen || !triggerRef.current || !panelRef.current) {
      setVisible(false);
      return;
    }
    const measure = () => {
      if (!triggerRef.current || !panelRef.current) return;
      const rect = triggerRef.current.getBoundingClientRect();
      setPos(calcPosition(rect, panelRef.current, placement));
    };
    measure();
    // 次フレームで visible にしてアニメーションを発火させる
    requestAnimationFrame(() => setVisible(true));

    // 開いている間だけ測り直す。中のスクロール箱でも拾えるよう capture + passive。
    // 時間に頼る後始末は作らない（便2 の教訓＝280ms タイマーの罠）。
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, { capture: true, passive: true });
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, { capture: true });
    };
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
