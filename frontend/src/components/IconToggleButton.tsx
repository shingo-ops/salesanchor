/**
 * IconToggleButton — アイコン切替ボタン金型（押下状態でアイコンと色が切り替わる）
 *
 * pressed  : 押下状態（true で iconOn・危険色系、false で iconOff・通常色）
 * iconOff / iconOn : constants/icons.tsx のアイコン（例: 白抜きハート / 塗りハート）
 * count    : 任意。アイコンの右に件数を表示（未指定なら非表示）
 * size     : sm（28px・既定）/ md（36px）
 *
 * 業務の意味（いいね・お気に入り等）はこのコンポーネントに埋め込まない。
 * aria-label は必須（アイコンのみのボタンのため）。押下状態は aria-pressed で伝える。
 */
import type { Icon } from '../constants/icons';
import { ICON } from '../constants/iconSizes';
import './IconToggleButton.css';

export type IconToggleButtonSize = 'sm' | 'md';

export interface IconToggleButtonProps {
  /** 押下状態 */
  pressed: boolean;
  onClick: () => void;
  /** 未押下時のアイコン */
  iconOff: Icon;
  /** 押下時のアイコン */
  iconOn: Icon;
  /** アクセシブル名（必須） */
  'aria-label': string;
  size?: IconToggleButtonSize;
  disabled?: boolean;
  /** 件数（任意・アイコン右に表示） */
  count?: number;
}

const ICON_SIZE: Record<IconToggleButtonSize, number> = {
  sm: ICON.md,
  md: ICON.base,
};

export function IconToggleButton({
  pressed,
  onClick,
  iconOff,
  iconOn,
  'aria-label': ariaLabel,
  size = 'sm',
  disabled = false,
  count,
}: IconToggleButtonProps) {
  const IconComponent = pressed ? iconOn : iconOff;
  const cls = [
    'comp-icon-toggle',
    `comp-icon-toggle--${size}`,
    pressed ? 'comp-icon-toggle--pressed' : '',
  ].filter(Boolean).join(' ');

  return (
    <button
      type="button"
      className={cls}
      aria-pressed={pressed}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={onClick}
    >
      <IconComponent size={ICON_SIZE[size]} aria-hidden="true" />
      {count !== undefined && <span className="comp-icon-toggle__count">{count}</span>}
    </button>
  );
}
