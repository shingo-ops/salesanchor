/**
 * Badge — ステータス・ラベルバッジ（Task 3C）
 *
 * variant  : 見た目の意味（neutral / info / success / warning / danger）
 * appearance: soft（既定・淡い背景＋色文字）/ solid（塗り）
 * size     : sm / md
 * dot      : 先頭ドットインジケーター
 * icon     : 先頭アイコン
 *
 * ラベルは children で渡す（業務ステータス名はこのコンポーネントに埋め込まない）。
 * ステータス値 → variant のマッピングは呼び出し側で定義すること。
 */
import type { ReactNode } from 'react';
import './Badge.css';

export type BadgeVariant    = 'neutral' | 'info' | 'success' | 'warning' | 'danger';
export type BadgeAppearance = 'soft' | 'solid';
export type BadgeSize       = 'sm' | 'md';

export interface BadgeProps {
  /** 意味的バリアント（色） */
  variant?:    BadgeVariant;
  /** soft = 淡い背景＋色文字（既定）/ solid = 塗り */
  appearance?: BadgeAppearance;
  /** sm = 20px 最小高 / md = 24px 最小高（既定） */
  size?:       BadgeSize;
  /** 先頭に小さいドットを表示 */
  dot?:        boolean;
  /** 先頭アイコン（任意） */
  icon?:       ReactNode;
  /** ラベル */
  children:    ReactNode;
  className?:  string;
}

export function Badge({
  variant    = 'neutral',
  appearance = 'soft',
  size       = 'md',
  dot        = false,
  icon,
  children,
  className = '',
}: BadgeProps) {
  const cls = [
    'comp-badge',
    `comp-badge--${variant}`,
    `comp-badge--${appearance}`,
    `comp-badge--${size}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <span className={cls}>
      {dot && <span className="comp-badge__dot" aria-hidden="true" />}
      {icon != null && <span className="comp-badge__icon" aria-hidden="true">{icon}</span>}
      {children}
    </span>
  );
}
