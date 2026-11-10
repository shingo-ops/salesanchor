/**
 * FullScreenDialog 金型（窓いっぱいの入れ物・ADR-144・PO 2026-11-11 許可）
 *
 * - 一番上の帯: 左に ×・真ん中に title（中身は呼ぶ側）・右に actions
 * - Esc で閉じる（document で受けて stopPropagation。変換中の Esc は何もしない）
 * - フォーカストラップ（useFocusTrap）・開いた時は initialFocusRef（無ければ最初の押せる物）へ
 * - 閉じたら開く前の要素がまだ画面に在ればそこへ戻す
 * - role="dialog" / aria-modal / aria-label・document.body へ portal
 */
import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import ReactDOM from "react-dom";
import { Button } from "./Button";
import { X } from "../constants/icons-base";
import { useFocusTrap, getFirstFocusable } from "../hooks/useFocusTrap";
import "./FullScreenDialog.css";

interface FullScreenDialogProps {
  open: boolean;
  onClose: () => void;
  /** 読み上げの名前（t() の文字） */
  ariaLabel: string;
  /** × の読み上げ（t() の文字） */
  closeLabel: string;
  /** 一番上の帯の真ん中に置く中身 */
  title?: ReactNode;
  /** 一番上の帯の右に置く中身（保存のボタンなど） */
  actions?: ReactNode;
  /** 開いた時に最初にフォーカスする要素 */
  initialFocusRef?: RefObject<HTMLElement | null>;
  children: ReactNode;
}

export function FullScreenDialog({
  open,
  onClose,
  ariaLabel,
  closeLabel,
  title,
  actions,
  initialFocusRef,
  children,
}: FullScreenDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<Element | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  /* フォーカス: 開く直前の要素を覚え、閉じたらまだ画面に在る時だけ戻す */
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement;
      return;
    }
    const el = triggerRef.current;
    triggerRef.current = null;
    if (el instanceof HTMLElement && el.isConnected) el.focus();
  }, [open]);

  /* 開いたら initialFocusRef（無ければ最初の押せる物）へ */
  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const target = initialFocusRef?.current ?? getFirstFocusable(dialog);
    target?.focus();
  }, [open, initialFocusRef]);

  /* Esc で閉じる。変換中（isComposing・keyCode 229）は何もしない */
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (event.isComposing || event.keyCode === 229) return;
      event.stopPropagation();
      onCloseRef.current();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  useFocusTrap(open, dialogRef);

  if (!open) return null;

  return ReactDOM.createPortal(
    <div
      ref={dialogRef}
      className="comp-fullscreen-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
    >
      <div className="comp-fullscreen-dialog__header">
        <Button variant="ghost" size="md" iconOnly aria-label={closeLabel} onClick={onClose}>
          <X size={20} />
        </Button>
        <div className="comp-fullscreen-dialog__title">{title}</div>
        {actions != null && <div className="comp-fullscreen-dialog__actions">{actions}</div>}
      </div>
      <div className="comp-fullscreen-dialog__body">
        <div className="comp-fullscreen-dialog__content">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
