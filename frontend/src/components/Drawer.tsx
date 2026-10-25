/**
 * Drawer — 右スライドパネル（Notion「サイドピーク」相当）
 *
 * - 右から出るスライドアニメーション（user-drawer パターン踏襲）
 * - Esc で閉じる（onEscape が渡されていればそちら。背景クリック・✕ は常に onClose。design.md 4-4・審査指摘9）
 * - 背景クリックで閉じる
 * - ✕ ボタンで閉じる
 * - フォーカストラップ（Tab / Shift+Tab がパネル内を循環）
 * - 閉じたら元の要素へフォーカス復帰
 * - onOpenFullPage が渡された場合は「フルページで開く↗」ボタンをヘッダに表示
 * - onBack が渡された場合は題の左に「← 戻る」ボタンをヘッダに表示（省略時は今までどおり何も出ない。design.md 4-1）
 * - a11y: role="dialog" / aria-modal / aria-labelledby
 * - ReactDOM.createPortal で document.body にマウント
 * - z-index: --z-drawer (301) — Modal の overlay は --z-modal (400) で前面
 */

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import ReactDOM from "react-dom";
import { useTranslation } from "react-i18next";
import { Button } from "./Button";
import { X, ArrowTopRight, ArrowLeft } from "../constants/icons-base";
import "./Drawer.css";

interface DrawerBaseProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** フルページで開くコールバック。省略時はボタン非表示 */
  onOpenFullPage?: () => void;
  /** Esc を押したときの処理。渡したときだけ onClose の代わりに呼ばれる（省略時は今までどおり onClose）。
   *  背景クリックと ✕ ボタンは常に onClose のまま（design.md 4-4） */
  onEscape?: () => void;
  footer?: ReactNode;
  /** パネル幅。'default'（480px）/ 'wide'（1100px・スマホは全幅） */
  size?: "default" | "wide";
}

/** onBack を渡すときは backLabel（読み上げ名）も必須にする。片方だけでは
 *  aria-label の無いアイコンボタンが作れてしまうため（審査指摘） */
type DrawerBackProps =
  | { onBack: () => void; backLabel: string }
  | { onBack?: undefined; backLabel?: undefined };

type DrawerProps = DrawerBaseProps & DrawerBackProps;

export function Drawer({
  open,
  onClose,
  title,
  children,
  onOpenFullPage,
  onEscape,
  onBack,
  backLabel,
  footer,
  size = "default",
}: DrawerProps) {
  const { t }     = useTranslation();
  const titleId   = useId();
  const panelRef  = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<Element | null>(null);

  /* ポータル対象を useEffect で取得（Storybook/SSR 環境での document アクセス回避） */
  const [portalTarget, setPortalTarget] = useState<HTMLElement | null>(null);
  useEffect(() => { setPortalTarget(document.body); }, []);

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

  /* Esc で閉じる（onEscape が渡されていればそちらを呼ぶ。省略時は今までどおり onClose。design.md 4-4） */
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        (onEscape ?? onClose)();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose, onEscape]);

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

  if (!portalTarget) return null;

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
        className={`comp-drawer-panel${size === "wide" ? " comp-drawer-panel--wide" : ""}${open ? " comp-drawer-panel--open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="supplier-drawer"
      >
        {/* ヘッダ */}
        <div className="comp-drawer-header">
          {onBack && (
            <Button
              variant="ghost"
              size="md"
              iconOnly
              aria-label={backLabel}
              onClick={onBack}
              data-testid="drawer-back"
              layoutClassName="comp-drawer-header-back"
            >
              <ArrowLeft size={20} aria-hidden="true" />
            </Button>
          )}
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
    portalTarget,
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
