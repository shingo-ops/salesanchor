import type { CSSProperties } from 'react';
import { CheckIcon } from './icons';

export type ProgressVariant = 'linear' | 'striped' | 'circular';

export interface ProgressBarProps {
  /** 0–100. Values are clamped. */
  value: number;
  variant?: ProgressVariant;
  /** Optional label shown above linear/striped bars. */
  label?: string;
}

const clamp = (n: number) => Math.max(0, Math.min(100, Math.round(n)));

/**
 * Determinate progress for time-consuming confirmed operations
 * (CSV import, upload, bulk shipping). Shows success color + check at 100%.
 */
export function ProgressBar({ value, variant = 'linear', label }: ProgressBarProps) {
  const pct = clamp(value);
  const done = pct >= 100;

  if (variant === 'circular') {
    const style = { ['--progress-pct' as string]: pct } as CSSProperties;
    return (
      <div
        className={`sa-progress-circular${done ? ' sa-progress-circular--done' : ''}`}
        style={style}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="sa-progress-circular__inner">
          {done ? <CheckIcon className="sa-progress-circular__icon" /> : <span className="sa-progress-circular__pct">{pct}%</span>}
        </div>
      </div>
    );
  }

  const fillCls = ['sa-progress__fill', variant === 'striped' ? 'sa-progress__fill--striped' : '', done ? 'sa-progress__fill--done' : '']
    .filter(Boolean)
    .join(' ');

  return (
    <div>
      {label && (
        <div className="sa-progress__head">
          <span className="sa-progress__label" data-done={done ? 'true' : undefined}>
            {done ? 'Done' : label}
          </span>
          <span className="sa-progress__pct" data-done={done ? 'true' : undefined}>
            {done ? <CheckIcon className="sa-progress__check" /> : `${pct}%`}
          </span>
        </div>
      )}
      <div className="sa-progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={fillCls} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
