/**
 * Stack — 子要素を縦に積む／横に並べる並べ方の金型（ADR-144）
 *
 * direction : 'column'（縦積み・既定）/ 'row'（横1列。折り返さない）
 * gap : 間隔。デザイントークン段階（--space-N）の N を渡す（既定 "3" = var(--space-3)）
 *
 * 色・枠は持たない。並べ方だけを担う。
 */
import type { ReactNode } from 'react';
import './Stack.css';

export type StackGap = '1' | '2' | '3' | '4' | '5' | '6' | '8';

export type StackDirection = 'column' | 'row';

export interface StackProps {
  /** 並べる向き（既定 'column'） */
  direction?: StackDirection;
  /** 間隔（--space-N の N） */
  gap?:       StackGap;
  children?:  ReactNode;
  className?: string;
}

export function Stack({ direction = 'column', gap = '3', children, className = '' }: StackProps) {
  const cls = ['comp-stack', direction === 'row' ? 'comp-stack--row' : '', `comp-stack--gap-${gap}`, className].filter(Boolean).join(' ');
  return <div className={cls}>{children}</div>;
}
