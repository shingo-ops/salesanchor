/**
 * EditorPage 金型（予定の編集などの窓いっぱいの編集画面・ADR-144・ADR-1074）
 *
 * - 上の段: 左の列に ×・題名の欄（title）・右に丸い保存
 * - lead: 札の上・題名と同じ左端に置く中身（日時の段など）
 * - 札: cardTitle を頭に置き、中に EditorPageRow を並べる（絵の列は金型が持つ）
 * - Esc で閉じる（document で受けて stopPropagation。変換中の Esc は何もしない）
 * - フォーカストラップ・開いた時は initialFocusRef（無ければ最初の押せる物）へ・閉じたら元の要素へ
 * - role="dialog" / aria-modal / aria-label・document.body へ portal
 */
import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import ReactDOM from "react-dom";
import { Button } from "./Button";
import { X } from "../constants/icons-base";
import { useFocusTrap, getFirstFocusable } from "../hooks/useFocusTrap";
import "./EditorPage.css";

interface EditorPageProps {
  open: boolean;
  onClose: () => void;
  /** 読み上げの名前（t() の文字） */
  ariaLabel: string;
  /** × の読み上げ（t() の文字） */
  closeLabel: string;
  /** 上の段の題名の欄（金型 TextFieldControl variant="editor-title"） */
  title: ReactNode;
  /** 保存のボタンの文字（t() の文字） */
  saveLabel: string;
  onSave: () => void;
  saveDisabled?: boolean;
  /** 開いた時に最初にフォーカスする要素 */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** 札の上に置く中身 */
  lead?: ReactNode;
  /** 札の頭の文字（t() の文字） */
  cardTitle: string;
  /** 札の中の行（EditorPageRow） */
  children: ReactNode;
}

export function EditorPage({ open, onClose, ariaLabel, closeLabel, title, saveLabel, onSave, saveDisabled = false, initialFocusRef, lead, cardTitle, children }: EditorPageProps) {
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
    <div ref={dialogRef} className="comp-editor-page gcal-colors" role="dialog" aria-modal="true" aria-label={ariaLabel}>
      <div className="comp-editor-page__header">
        <div className="comp-editor-page__rail">
          <Button variant="ghost" size="md" iconOnly aria-label={closeLabel} onClick={onClose}>
            <X size={20} />
          </Button>
        </div>
        <div className="comp-editor-page__title">{title}</div>
        <Button variant="primary" size="md" shape="pill" onClick={onSave} disabled={saveDisabled}>
          {saveLabel}
        </Button>
      </div>
      <div className="comp-editor-page__body">
        {lead != null && <div className="comp-editor-page__lead">{lead}</div>}
        <section className="comp-editor-page__card" aria-label={cardTitle}>
          <div className="comp-editor-page__card-head">
            <span className="comp-editor-page__card-title">{cardTitle}</span>
          </div>
          <div className="comp-editor-page__rows">{children}</div>
        </section>
      </div>
    </div>,
    document.body,
  );
}

/** 札の中の 1 行（1 列目: 絵・2 列目: 中身） */
export function EditorPageRow({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <div className="comp-editor-page__row">
      <span className="comp-editor-page__row-icon">{icon}</span>
      <div className="comp-editor-page__row-body">{children}</div>
    </div>
  );
}
