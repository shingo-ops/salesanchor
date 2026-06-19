import type { CSSProperties } from 'react';

export type SpinnerSize = 'sm' | 'md' | 'lg';

export interface SpinnerProps {
  /** token-driven size preset. Default 'md'. */
  size?: SpinnerSize;
  /** Override the active arc color. Pass a token, e.g. 'var(--accent)'. */
  color?: string;
  /** Use on a filled/primary surface (white arc). */
  onAccent?: boolean;
  className?: string;
  /** Accessible label, announced to screen readers. */
  label?: string;
}

/**
 * Circular loading indicator. Use for partial loads: inside modals,
 * while a table refetches, search-result waits.
 */
export function Spinner({ size = 'md', color, onAccent, className, label = 'Loading' }: SpinnerProps) {
  const style = color ? ({ borderTopColor: color } as CSSProperties) : undefined;
  const cls = ['sa-spinner', `sa-spinner--${size}`, onAccent ? 'sa-spinner--on-accent' : '', className]
    .filter(Boolean)
    .join(' ');
  return <span role="status" aria-label={label} className={cls} style={style} />;
}
