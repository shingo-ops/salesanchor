/**
 * ReadOnlyField — 読むだけの欄の金型（ADR-144・invoice-create-portfolio design-v2 §3-7）
 *
 * label : ラベル（呼ぶ側が t() で渡す）
 * value : 値。null・undefined・false・空白だけの文字列は「未登録」（common.unregistered）を薄い字で出す。数の 0 は空ではない
 *
 * 入力の部品（input・textarea）を持たない。改行はそのまま出す。
 * 色・余白・角丸・字の大きさはすべて CSS 変数（ADR-067）。
 */
import { useId, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import './ReadOnlyField.css';

export interface ReadOnlyFieldProps {
  /** ラベル */
  label:      ReactNode;
  /** 値 */
  value?:     ReactNode;
  className?: string;
}

function isEmptyValue(value: ReactNode): boolean {
  if (value === null || value === undefined || value === false) return true;
  return typeof value === 'string' && value.trim() === '';
}

export function ReadOnlyField({ label, value, className = '' }: ReadOnlyFieldProps) {
  const { t } = useTranslation();
  const labelId = useId();
  const empty = isEmptyValue(value);
  const cls = ['comp-readonly-field', className].filter(Boolean).join(' ');
  const valueCls = ['comp-readonly-field__value', empty ? 'comp-readonly-field__value--empty' : ''].filter(Boolean).join(' ');
  return (
    <div className={cls} role="group" aria-labelledby={labelId}>
      <span id={labelId} className="comp-readonly-field__label">{label}</span>
      <div className={valueCls}>{empty ? t('common.unregistered') : value}</div>
    </div>
  );
}
