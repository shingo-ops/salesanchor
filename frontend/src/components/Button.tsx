/**
 * Button — 標準ボタン金型（Task 1C）
 *
 * 既存の btn-* クラスを variant に対応させた薄いラッパー。
 * TypeScript の型で規格外 variant / size をコンパイルエラーにする。
 *
 * - variant: primary / secondary / ghost / danger / outline / tab
 * - size:    sm / md / lg
 * - options: fullWidth / loading / iconOnly(aria-label必須) / active(tab用)
 *
 * 実画面への展開は Task 1E で行う。このコンポーネント自体は Preview 画面でのみ使用。
 *
 * variant規格: primary=本文主操作(1画面1個)・secondary=補助・ghost=設定系(ヘッダー可)・tab=切替(選択中のみネイビー)。ヘッダー内でprimary禁止。フォルム上書き・インラインstyle禁止。正本: docs/specs/design-system/component-ssot/page-header-v2/design.md §2
 */

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
}

export type ButtonProps = ButtonOwnProps & Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof ButtonOwnProps>;

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:   "btn-primary",
  secondary: "btn-secondary",
  ghost:     "btn-ghost",
  danger:    "btn-danger",
  outline:   "btn-outline",
  tab:       "btn-tab",
};

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  loadingText,
  active = false,
  iconOnly = false,
  children,
  className,
  disabled,
  "aria-label": ariaLabel,
  ...rest
}: ButtonProps) {
  const isTab = variant === "tab";
  const classes = [
    VARIANT_CLASS[variant],
    isTab ? "" : (size === "sm" ? "comp-btn--sm" : size === "lg" ? "comp-btn--lg" : ""),
    isTab && active ? "comp-btn--active" : "",
    fullWidth  ? "comp-btn--full"      : "",
    loading    ? "comp-btn--loading"   : "",
    iconOnly   ? "comp-btn--icon-only" : "",
    className ?? "",
  ].filter(Boolean).join(" ");

  return (
    <button
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-pressed={isTab ? active : undefined}
      aria-label={ariaLabel}
      {...rest}
    >
      {loading && <Spinner size="sm" onAccent={variant === "primary"} />}
      {loading ? (loadingText ?? children) : children}
    </button>
  );
}
