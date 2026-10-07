/**
 * IconToggleButton — アイコン切替ボタン金型（押下状態でアイコンと色が切り替わる）
 *
 * pressed  : 押下状態（true で iconOn・危険色系、false で iconOff・通常色）
 * iconOff / iconOn : constants/icons.tsx のアイコン（例: 白抜きハート / 塗りハート）
 * count    : 任意。アイコンの右に件数を表示（未指定なら非表示）
 * size     : sm（28px・既定）/ md（36px）
 * variant  : default（既定・押下でアイコンと色が切替）/ badge（常に iconOn・危険色。押下は枠と背景で示す）
 *
 * 業務の意味（いいね・お気に入り等）はこのコンポーネントに埋め込まない。
 * aria-label は必須（アイコンのみのボタンのため）。押下状態は aria-pressed で伝える。
 */
import type { Icon } from '../constants/icons';
import { ICON } from '../constants/iconSizes';
import './IconToggleButton.css';

export type IconToggleButtonSize = 'sm' | 'md';

export type IconToggleButtonVariant = 'default' | 'badge';

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
  /** badge: 常に iconOn・危険色で表示し、pressed は枠と背景で区別（既定 default） */
  variant?: IconToggleButtonVariant;
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
  variant = 'default',
  disabled = false,
  count,
}: IconToggleButtonProps) {
  const isBadge = variant === 'badge';
  const IconComponent = pressed || isBadge ? iconOn : iconOff;
  const cls = [
    'comp-icon-toggle',
    `comp-icon-toggle--${size}`,
    isBadge ? 'comp-icon-toggle--badge' : '',
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
