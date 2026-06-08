/**
 * Button — 標準ボタン金型（Task 1C）
 *
 * 既存の btn-* クラスを variant に対応させた薄いラッパー。
 * TypeScript の型で規格外 variant / size をコンパイルエラーにする。
 *
 * - variant: primary / secondary / ghost / danger
 * - size:    sm / md / lg
 * - options: fullWidth / loading / iconOnly(aria-label必須)
 *
 * 実画面への展開は Task 1E で行う。このコンポーネント自体は Preview 画面でのみ使用。
 */

import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Button.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonOwnProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
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
};

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  iconOnly = false,
  children,
  className,
  disabled,
  "aria-label": ariaLabel,
  ...rest
}: ButtonProps) {
  const classes = [
    VARIANT_CLASS[variant],
    size === "sm" ? "comp-btn--sm" : size === "lg" ? "comp-btn--lg" : "",
    fullWidth  ? "comp-btn--full"      : "",
    loading    ? "comp-btn--loading"   : "",
    iconOnly   ? "comp-btn--icon-only" : "",
    className ?? "",
  ].filter(Boolean).join(" ");

  return (
    <button
      className={classes}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      aria-label={ariaLabel}
      {...rest}
    >
      {loading && <span className="comp-btn__spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}
