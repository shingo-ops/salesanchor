/**
 * SectionCard — 見出しつきのカード金型（ADR-144・invoice-create-portfolio design-v2 §3-7）
 *
 * title    : 見出し（呼ぶ側が t() で渡す）
 * actions  : 見出しの右に置く操作（任意）
 * children : カードの中身
 *
 * 外枠は Card（variant container）。見出しは h3。region の名前は見出し。
 * 色・余白・字の大きさはすべて CSS 変数（ADR-067）。
 */
import { useId, type ReactNode } from 'react';
import { Card } from './Card';
import './SectionCard.css';

export interface SectionCardProps {
  /** 見出し */
  title:      ReactNode;
  /** 見出しの右に置く操作 */
  actions?:   ReactNode;
  children?:  ReactNode;
  className?: string;
}

export function SectionCard({ title, actions, children, className = '' }: SectionCardProps) {
  const headingId = useId();
  const cls = ['comp-section-card', className].filter(Boolean).join(' ');
  return (
    <Card variant="container" className={cls} role="region" aria-labelledby={headingId}>
      <div className="comp-section-card__header">
        <h3 id={headingId} className="comp-section-card__title">{title}</h3>
        {actions ? <div className="comp-section-card__actions">{actions}</div> : null}
      </div>
      <div className="comp-section-card__body">{children}</div>
    </Card>
  );
}
