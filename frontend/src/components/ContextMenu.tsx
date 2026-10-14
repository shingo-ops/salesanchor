/**
 * ContextMenu — 押した場所の近くに出る小さなメニュー金型
 *
 * 受信箱 第4便（一覧の行を長押しするとメニューを出す）で新設（ADR-144 §4・PO 許可取得済み）。
 * 見た目は既存の `.dropdown-menu` / `.dropdown-item`（ADR-069・components.css:673-698）と
 * 同じトークンに揃えている。異なるのは表示位置の決め方だけ：
 * `.dropdown-menu` はトリガー要素に対して相対配置だが、本コンポーネントは
 * 長押しした座標（画面座標 x, y）を基準に、画面の端で切れないよう内側に収めて出す。
 *
 * - 開閉は制御式（open / onClose）
 * - 表示位置は anchor（画面座標 x, y）。画面の右端・下端に寄ったときは内側に収める
 * - align（既定 "point"）で置き方を選べる。"point" は上記の従来どおり
 *   （指で押した x 座標がそのまま左端）。"left" は画面左端から --space-3 の
 *   余白を取った位置に左端を固定する（受信箱 第5便・PO 指摘＝右側だと押しづらい）。
 *   縦位置（top）の決め方は align に関わらず同じ
 * - role="menu" / role="menuitem"、Esc で閉じる、外側を押すと閉じる
 * - 開いたら最初の項目へ自動でフォーカス
 * - 押す場所は 44px 以上（--size-icon-btn-lg と同じ基準）
 * - document.body への Portal 描画（Popover.tsx と同じ作法）
 */

import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import "./ContextMenu.css";

/** 長押しした画面座標。要素の矩形を渡す場合は左上の座標を使う */
export interface ContextMenuAnchor {
  x: number;
  y: number;
}

export interface ContextMenuItem {
  key: string;
  label: string;
  icon?: ReactNode;
  onSelect: () => void;
  /** 削除など取り消せない操作に付ける（--danger トークンで表示） */
  danger?: boolean;
}

export interface ContextMenuProps {
  open: boolean;
  onClose: () => void;
  /** 表示位置の基準。null のときは何も描画しない */
  anchor: ContextMenuAnchor | null;
  items: ContextMenuItem[];
  /** role="menu" の読み上げ用ラベル */
  ariaLabel?: string;
  /**
   * 置き方。既定は "point"（指で押した座標がそのまま左端＝従来どおり）。
   * "left" は画面左端から --space-3 の余白を取った位置に左端を固定する。
   */
  align?: "point" | "left";
}

/** align="left" のときに使う既定値。--space-3 が読めないときの安全なフォールバック */
const DEFAULT_LEFT_ALIGN_MARGIN = 12; // px — --space-3（tokens.css）と同じ値

/** --space-3 トークンの値（px）を読む。読めないときは DEFAULT_LEFT_ALIGN_MARGIN を使う */
function getLeftAlignMargin(): number {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return DEFAULT_LEFT_ALIGN_MARGIN;
  }
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--space-3").trim();
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : DEFAULT_LEFT_ALIGN_MARGIN;
}

/** 画面の端で切れないよう、anchor を内側に収めた位置を計算する */
function clampPosition(
  anchor: ContextMenuAnchor,
  panelWidth: number,
  panelHeight: number,
  align: "point" | "left" = "point",
): { top: number; left: number } {
  const margin = 8; // px — 画面端との最低間隔
  let left = align === "left" ? getLeftAlignMargin() : anchor.x;
  let top = anchor.y;

  if (align !== "left" && left + panelWidth + margin > window.innerWidth) {
    left = window.innerWidth - panelWidth - margin;
  }
  if (top + panelHeight + margin > window.innerHeight) {
    top = window.innerHeight - panelHeight - margin;
  }
  left = Math.max(margin, left);
  top = Math.max(margin, top);
  return { top, left };
}

export function ContextMenu({ open, onClose, anchor, items, ariaLabel, align = "point" }: ContextMenuProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const firstItemRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  // 位置計算 — パネルが DOM に入ってから測り、画面端で切れないよう内側に収める。
  // useLayoutEffect で paint 前に確定させ、anchor 座標のままで一瞬表示される
  // ちらつきを防ぐ（Popover.tsx と同じ考え方）。
  useLayoutEffect(() => {
    if (!open || !anchor || !panelRef.current) {
      setPos(null);
      return;
    }
    const rect = panelRef.current.getBoundingClientRect();
    setPos(clampPosition(anchor, rect.width, rect.height, align));
  }, [open, anchor, items, align]);

  // 開いたら最初の項目にフォーカス
  useEffect(() => {
    if (!open) return;
    const id = requestAnimationFrame(() => firstItemRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open]);

  // Esc で閉じる
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // 外側を押すと閉じる
  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (e: MouseEvent) => {
      if (panelRef.current?.contains(e.target as Node)) return;
      onClose();
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open, onClose]);

  if (!open || !anchor) return null;

  return createPortal(
    <div
      ref={panelRef}
      role="menu"
      aria-label={ariaLabel}
      className="comp-context-menu"
      style={
        pos
          ? { top: `${pos.top}px`, left: `${pos.left}px` }
          // 初回測定前（1 フレームだけ）は座標を隠して描画し、ちらつきを防ぐ
          : { top: `${anchor.y}px`, left: `${anchor.x}px`, visibility: "hidden" }
      }
    >
      {items.map((item, i) => (
        <button
          key={item.key}
          ref={i === 0 ? firstItemRef : undefined}
          type="button"
          role="menuitem"
          className={`comp-context-menu__item${item.danger ? " comp-context-menu__item--danger" : ""}`}
          onClick={() => {
            item.onSelect();
            onClose();
          }}
        >
          {item.icon && (
            <span className="comp-context-menu__icon" aria-hidden="true">
              {item.icon}
            </span>
          )}
          <span className="comp-context-menu__label">{item.label}</span>
        </button>
      ))}
    </div>,
    document.body,
  );
}
