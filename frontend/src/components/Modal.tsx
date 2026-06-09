/**
 * Modal 金型（Task 7C）
 *
 * - size: sm / md / lg
 * - Esc で閉じる
 * - 背景クリックで閉じる（dismissOnOverlay=true 時）
 * - フォーカストラップ（Tab / Shift+Tab がダイアログ内を循環）
 * - 閉じたら元の要素へフォーカス復帰
 * - a11y: role="dialog" / aria-modal / aria-labelledby
 * - ReactDOM.createPortal で document.body にマウント
 *
 * ADR-027: 閉じるラベルは t("common.close") を使用
 */

import { useEffect, useId, useRef, type ReactNode } from "react";
import ReactDOM from "react-dom";
import { useTranslation } from "react-i18next";
import { Button }         from "./Button";
import { X }              from "../constants/icons";
import "./Modal.css";

export type ModalSize = "sm" | "md" | "lg";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  size?: ModalSize;
  /** true: 背景クリックで閉じる（default: true） */
  dismissOnOverlay?: boolean;
  children: ReactNode;
  footer?: ReactNode;
}

export function Modal({
  open,
  onClose,
  title,
  size = "md",
  dismissOnOverlay = true,
  children,
  footer,
}: ModalProps) {
  const { t }     = useTranslation();
  const titleId   = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<Element | null>(null);

  /* フォーカス復帰: open 直前の activeElement を保持 */
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement;
    } else {
      const el = triggerRef.current;
      if (el instanceof HTMLElement) el.focus();
      triggerRef.current = null;
    }
  }, [open]);

  /* ダイアログが開いたら最初のフォーカス可能要素へ移動 */
  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const first = getFirstFocusable(dialog);
    if (first) first.focus();
  }, [open]);

  /* Esc で閉じる */
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

  /* フォーカストラップ */
  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = getFocusableElements(dialog);
      if (focusable.length === 0) { e.preventDefault(); return; }
      const first = focusable[0];
      const last  = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleTab);
    return () => document.removeEventListener("keydown", handleTab);
  }, [open]);

  if (!open) return null;

  return ReactDOM.createPortal(
    <div
      className="comp-modal-overlay"
      onClick={dismissOnOverlay ? onClose : undefined}
    >
      <div
        ref={dialogRef}
        className={`comp-modal-dialog comp-modal-dialog--${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ヘッダ */}
        <div className="comp-modal-header">
          <h2 id={titleId} className="comp-modal-title">{title}</h2>
          <Button
            variant="ghost"
            size="md"
            iconOnly
            aria-label={t("common.close")}
            onClick={onClose}
          >
            <X size={20} />
          </Button>
        </div>

        {/* 本体 */}
        <div className="comp-modal-body">{children}</div>

        {/* フッタ（省略可） */}
        {footer != null && (
          <div className="comp-modal-footer">{footer}</div>
        )}
      </div>
    </div>,
    document.body,
  );
}

/* ----------------------------------------------------------------
   ユーティリティ
   ---------------------------------------------------------------- */

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.closest("[aria-hidden='true']"),
  );
}

function getFirstFocusable(container: HTMLElement): HTMLElement | null {
  return getFocusableElements(container)[0] ?? null;
}
