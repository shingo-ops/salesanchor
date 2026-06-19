import type { CSSProperties } from 'react';

export type SkeletonVariant = 'text' | 'table' | 'list' | 'card';

export interface SkeletonProps {
  /** Shape preset. Default 'text'. */
  variant?: SkeletonVariant;
  /** Number of rows for 'table' / 'list'. Default 3. */
  rows?: number;
  /** Width for the 'text' variant (e.g. '60%' or 200). */
  width?: string | number;
}

const bar = (style: CSSProperties) => <span className="sa-skeleton" style={style} />;

/**
 * Shimmer placeholder shown while data is loading. Swap to real content on
 * arrival. Match the variant to the surface (table / list / card).
 */
export function Skeleton({ variant = 'text', rows = 3, width }: SkeletonProps) {
  if (variant === 'text') {
    return bar({ display: 'block', height: 'var(--space-3)', width: width ?? '100%' });
  }

  if (variant === 'table') {
    return (
      <div role="status" aria-label="Loading">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="sa-skeleton__row">
            {bar({ height: 'var(--space-3)' })}
            {bar({ height: 'var(--space-3)' })}
            {bar({
              height: 'var(--space-5)',
              width: 'var(--space-12)',
              borderRadius: 'var(--radius-full)',
            })}
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div role="status" aria-label="Loading" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="sa-skeleton__list-item">
            {bar({
              width: 'calc(var(--space-10) - var(--space-1) / 2)',
              height: 'calc(var(--space-10) - var(--space-1) / 2)',
              borderRadius: 'var(--radius-full)',
              flex: 'none',
            })}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 'calc(var(--space-2) - var(--space-1) / 4)' }}>
              {bar({ height: 'calc(var(--space-3) - var(--space-1) / 4)', width: '60%' })}
              {bar({ height: 'var(--space-2)', width: '85%' })}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // card
  return (
    <div role="status" aria-label="Loading" style={{ display: 'flex', flexDirection: 'column', gap: 'calc(var(--space-3) + var(--space-1))' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'calc(var(--space-3) + var(--space-1))' }}>
        {bar({
          width: 'calc(var(--space-12) + var(--space-1))',
          height: 'calc(var(--space-12) + var(--space-1))',
          borderRadius: 'calc(var(--radius-xl) + var(--radius-xs))',
          flex: 'none',
        })}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {bar({ height: 'var(--space-3)', width: '70%' })}
          {bar({ height: 'var(--space-2)', width: '45%' })}
        </div>
      </div>
      {bar({ height: 'var(--space-2)', width: '100%' })}
      {bar({ height: 'var(--space-2)', width: '90%' })}
      {bar({ height: 'var(--space-2)', width: '75%' })}
    </div>
  );
}
