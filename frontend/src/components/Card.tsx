/**
 * Card — 標準カード金型（Task 1C）
 *
 * TypeScript の型で規格外 variant / density をコンパイルエラーにする。
 *
 * - variant: container / interactive / metric
 * - density: default(24px) / compact(16px)
 *   モバイル（≤767px）では default も compact 相当に縮小（CSS 自動）
 *
 * 実画面への展開は Task 1E で行う。このコンポーネント自体は Preview 画面でのみ使用。
 */

import type { HTMLAttributes, ReactNode } from "react";
import "./Card.css";

export type CardVariant = "container" | "interactive" | "metric";
export type CardDensity  = "default" | "compact";

interface CardOwnProps {
  variant?: CardVariant;
  density?: CardDensity;
  children?: ReactNode;
}

export type CardProps = CardOwnProps & Omit<HTMLAttributes<HTMLDivElement>, keyof CardOwnProps>;

export function Card({
  variant = "container",
  density = "default",
  children,
  className,
  ...rest
}: CardProps) {
  const classes = [
    "comp-card",
    `comp-card--${variant}`,
    density === "compact" ? "comp-card--compact" : "",
    className ?? "",
  ].filter(Boolean).join(" ");

  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}
