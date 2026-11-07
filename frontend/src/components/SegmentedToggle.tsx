/**
 * SegmentedToggle — 2〜3 個のアイコンボタンから 1 つを選ぶ切替金型（Discord の権限画面の ✕ ／ ✓ の形）
 *
 * value=null はどれも選ばれていない状態。状態は持たない（controlled）。
 * 業務の意味（許可・非表示など）は持たせない。名前は呼び出し側が t() 済みで渡す。
 * 各ボタンはアイコンだけなので aria-label に label を入れる。
 */
import type { Icon } from '../constants/icons';
import { ICON } from '../constants/iconSizes';
import './SegmentedToggle.css';

export type SegmentedTone = 'danger' | 'neutral' | 'success';

export interface SegmentedOption<V extends string> {
  value: V;
  icon: Icon;
  /** 読み上げ用の名前（t() 済み） */
  label: string;
  tone: SegmentedTone;
  disabled?: boolean;
}

export interface SegmentedToggleProps<V extends string> {
  /** 2〜3 個 */
  options: SegmentedOption<V>[];
  /** null = どれも選ばれていない */
  value: V | null;
  onChange: (value: V) => void;
  /** 行の名前 */
  'aria-label': string;
  disabled?: boolean;
}

export function SegmentedToggle<V extends string>({
  options,
  value,
  onChange,
  'aria-label': ariaLabel,
  disabled = false,
}: SegmentedToggleProps<V>) {
  return (
    <div
      className={`comp-segmented${disabled ? ' comp-segmented--disabled' : ''}`}
      role="radiogroup"
      aria-label={ariaLabel}
    >
      {options.map((opt) => {
        const checked = opt.value === value;
        const off = disabled || opt.disabled === true;
        const IconComponent = opt.icon;
        const cls = [
          'comp-segmented__btn',
          `comp-segmented__btn--${opt.tone}`,
          checked ? 'comp-segmented__btn--checked' : '',
        ].filter(Boolean).join(' ');
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={checked}
            aria-label={opt.label}
            title={opt.label}
            className={cls}
            disabled={off}
            onClick={() => onChange(opt.value)}
          >
            <IconComponent size={ICON.sm} aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}
