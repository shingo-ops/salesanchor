/**
 * TwoColumn — 左右2列に並べる金型（ADR-144）
 *
 * ratio : 列幅の比。"1:2"（既定・左が狭い）/ "1:1"（等幅）
 * gap   : 間隔。デザイントークン段階（--space-N）の N（既定 "3"）
 * align : 縦位置。"start"（既定）/ "center" / "stretch"
 *
 * 子は2つを想定（左・右の順）。色・枠は持たない。
 */
import type { ReactNode } from 'react';
import './TwoColumn.css';

export type TwoColumnRatio = '1:2' | '1:1';
export type TwoColumnGap = '2' | '3' | '4' | '6';
export type TwoColumnAlign = 'start' | 'center' | 'stretch';

export interface TwoColumnProps {
  /** 列幅の比 */
  ratio?:     TwoColumnRatio;
  /** 間隔（--space-N の N） */
  gap?:       TwoColumnGap;
  /** 縦位置 */
  align?:     TwoColumnAlign;
  children?:  ReactNode;
  className?: string;
}

export function TwoColumn({ ratio = '1:2', gap = '3', align = 'start', children, className = '' }: TwoColumnProps) {
  const ratioKey = ratio.replace(':', '-');
  const cls = [
    'comp-two-column',
    `comp-two-column--ratio-${ratioKey}`,
    `comp-two-column--gap-${gap}`,
    `comp-two-column--align-${align}`,
    className,
  ].filter(Boolean).join(' ');
  return <div className={cls}>{children}</div>;
}
