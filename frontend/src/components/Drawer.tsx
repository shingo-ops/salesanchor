/**
 * Drawer — 右スライドパネル（Notion「サイドピーク」相当）
 *
 * - 右から出るスライドアニメーション（user-drawer パターン踏襲）
 * - Esc で閉じる
 * - 背景クリックで閉じる
 * - フォーカストラップ（Tab / Shift+Tab がパネル内を循環）
 * - 閉じたら元の要素へフォーカス復帰
 * - onOpenFullPage が渡された場合は「フルページで開く↗」ボタンをヘッダに表示
 * - a11y: role="dialog" / aria-modal / aria-labelledby
 * - ReactDOM.createPortal で document.body にマウント
 * - z-index: --z-drawer (299) — Modal (400) より下
 */

import { useEffect, useId, useRef, type ReactNode } from "react";
import ReactDOM from "react-dom";
import { useTranslation } from "react-i18next";
import { Button } from "./Button";
import { X, ArrowTopRight } from "../constants/icons";
import "./Drawer.css";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** フルページで開くコールバック。省略時はボタン非表示 */
  onOpenFullPage?: () => void;
  footer?: ReactNode;
}

export function Drawer({
  open,
  onClose,
  title,
  children,
  onOpenFullPage,
  footer,
}: DrawerProps) {
  const { t }     = useTranslation();
  const titleId   = useId();
  const panelRef  = useRef<HTMLDivElement>(null);
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

  /* パネルが開いたら最初のフォーカス可能要素へ移動 */
  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    if (!panel) return;
    const first = getFirstFocusable(panel);
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
    const panel = panelRef.current;
    if (!panel) return;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = getFocusableElements(panel);
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

  return ReactDOM.createPortal(
    <>
      {/* オーバーレイ */}
      {open && (
        <div
          className="comp-drawer-overlay"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* パネル本体 — DOM は常にマウント、CSS クラスでアニメーション */}
      <div
        ref={panelRef}
        className={`comp-drawer-panel${open ? " comp-drawer-panel--open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="supplier-drawer"
      >
        {/* ヘッダ */}
        <div className="comp-drawer-header">
          <h2 id={titleId} className="comp-drawer-title">{title}</h2>
          <div className="comp-drawer-header-actions">
            {onOpenFullPage && (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                aria-label={t("suppliers.openFullPage")}
                onClick={onOpenFullPage}
                data-testid="drawer-open-fullpage"
              >
                <ArrowTopRight size={18} aria-hidden="true" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="md"
              iconOnly
              aria-label={t("common.close")}
              onClick={onClose}
              data-testid="drawer-close"
            >
              <X size={20} aria-hidden="true" />
            </Button>
          </div>
        </div>

        {/* 本体 */}
        <div className="comp-drawer-body">{children}</div>

        {/* フッタ（省略可） */}
        {footer != null && (
          <div className="comp-drawer-footer">{footer}</div>
        )}
      </div>
    </>,
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
