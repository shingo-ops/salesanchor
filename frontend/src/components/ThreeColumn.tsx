/**
 * ThreeColumn — 3列に並べる金型（ADR-144・invoice-create-portfolio design-v2 §3-7）
 *
 * gap   : 間隔。デザイントークン段階（--space-N）の N（既定 "3"）
 * align : 縦位置。"start"（既定）/ "center" / "stretch"
 *
 * 子は3つを想定（左・中・右の順）。3列は等幅。幅 1279px 以下（--breakpoint-tablet-max）で縦1列。
 * TwoColumn と同じ作り。色・枠は持たない。
 */
import type { ReactNode } from 'react';
import './ThreeColumn.css';

export type ThreeColumnGap = '2' | '3' | '4' | '6';
export type ThreeColumnAlign = 'start' | 'center' | 'stretch';

export interface ThreeColumnProps {
  /** 間隔（--space-N の N） */
  gap?:       ThreeColumnGap;
  /** 縦位置 */
  align?:     ThreeColumnAlign;
  children?:  ReactNode;
  className?: string;
}

export function ThreeColumn({ gap = '3', align = 'start', children, className = '' }: ThreeColumnProps) {
  const cls = [
    'comp-three-column',
    `comp-three-column--gap-${gap}`,
    `comp-three-column--align-${align}`,
    className,
  ].filter(Boolean).join(' ');
  return <div className={cls}>{children}</div>;
}
