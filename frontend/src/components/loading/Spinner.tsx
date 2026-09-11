import type { CSSProperties } from 'react';
import '../../loading-animations.css';

export type SpinnerSize = 'sm' | 'md' | 'lg';

export interface SpinnerProps {
  /** token-driven size preset. Default 'md'. */
  size?: SpinnerSize;
  /** Override the active arc color. Pass a token, e.g. 'var(--accent)'. */
  color?: string;
  /** Use on a filled/primary surface (white arc). */
  onAccent?: boolean;
  /** Inherit the foreground color of the containing control. */
  tone?: 'default' | 'inherit';
  /** Hide a redundant indicator from the accessibility tree. */
  decorative?: boolean;
  className?: string;
  /** Accessible label, announced to screen readers. */
  label?: string;
}

/**
 * Circular loading indicator. Use for partial loads: inside modals,
 * while a table refetches, search-result waits.
 */
export function Spinner({ size = 'md', color, onAccent, tone = 'default', decorative = false, className, label = 'Loading' }: SpinnerProps) {
  const style = tone !== 'inherit' && color ? ({ borderTopColor: color } as CSSProperties) : undefined;
  const cls = ['sa-spinner', `sa-spinner--${size}`, onAccent ? 'sa-spinner--on-accent' : '', tone === 'inherit' ? 'sa-spinner--inherit' : '', className]
    .filter(Boolean)
    .join(' ');
  return <span role={decorative ? undefined : "status"} aria-label={decorative ? undefined : label} aria-hidden={decorative || undefined} className={cls} style={style} />;
}
