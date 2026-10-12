/**
 * Callout — 画面に残る注意・案内の枠（ADR-144 金型）
 *
 * variant : warning（注意・role="alert"）/ info（案内・role="status"）
 * title   : 見出し（t() 済みの文字列を渡す）
 * children: 本文
 *
 * 閉じるボタンは持たない。消えずに残る枠で、画面側が表示の有無を決める。
 */
import type { ReactNode } from 'react';
import './Callout.css';

export type CalloutVariant = 'warning' | 'info';

export interface CalloutProps {
  /** 意味的バリアント */
  variant?:   CalloutVariant;
  /** 見出し */
  title:      string;
  /** 本文 */
  children?:  ReactNode;
  className?: string;
}

export function Callout({ variant = 'warning', title, children, className = '' }: CalloutProps) {
  const cls = ['comp-callout', `comp-callout--${variant}`, className].filter(Boolean).join(' ');
  return (
    <div className={cls} role={variant === 'warning' ? 'alert' : 'status'}>
      <p className="comp-callout__title">{title}</p>
      {children != null && <div className="comp-callout__body">{children}</div>}
    </div>
  );
}
