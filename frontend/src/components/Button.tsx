/**
 * Button — 標準ボタン金型（Task 1C）
 *
 * Button.css を外観の正本とする native button。
 * TypeScript の型で規格外 variant / size をコンパイルエラーにする。
 *
 * - variant: primary / secondary / ghost / danger / outline / tab
 * - size:    sm / md / lg
 * - options: fullWidth / loading / iconOnly(aria-label必須) / active(tab用)
 *
 *
 * variant規格: primary=本文主操作(1画面1個)・secondary=補助・ghost=設定系(ヘッダー可)・tab=切替(選択中のみネイビー)。ヘッダー内でprimary禁止。フォルム上書き・インラインstyle禁止。正本: docs/specs/design-system/component-ssot/page-header-v2/design.md §2
 */

import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "./loading";
import "./Button.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline" | "tab";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonOwnProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  loadingText?: string;
  /** tab variant でのみ選択状態を表す */
  active?: boolean;
  /** true にする場合は aria-label 必須 */
  iconOnly?: boolean;
  children?: ReactNode;
  /** 同じbutton要素への外側配置専用クラス */
  layoutClassName?: string;
}

export type ButtonProps = ButtonOwnProps & Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof ButtonOwnProps | "className" | "style">;

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:   "comp-btn--primary",
  secondary: "comp-btn--secondary",
  ghost:     "comp-btn--ghost",
  danger:    "comp-btn--danger",
  outline:   "comp-btn--outline",
  tab:       "comp-btn--tab",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  loadingText,
  active = false,
  iconOnly = false,
  children,
  layoutClassName,
  disabled,
  "aria-label": ariaLabel,
  ...rest
}, ref) {
  const isTab = variant === "tab";
  const classes = [
    "comp-btn",
    VARIANT_CLASS[variant],
    isTab ? "" : (size === "sm" ? "comp-btn--sm" : size === "lg" ? "comp-btn--lg" : ""),
    isTab && active ? "comp-btn--active" : "",
    fullWidth  ? "comp-btn--full"      : "",
    loading    ? "comp-btn--loading"   : "",
    iconOnly   ? "comp-btn--icon-only" : "",
    layoutClassName ?? "",
  ].filter(Boolean).join(" ");

  return (
    <button
      ref={ref}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-pressed={isTab ? active : undefined}
      aria-label={ariaLabel}
      {...rest}
    >
      {loading && <Spinner size="sm" tone="inherit" decorative />}
      {loading ? (loadingText ?? children) : children}
    </button>
  );
});
