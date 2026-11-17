/**
 * TotalsBox — 色つきの合計枠の金型（ADR-144・invoice-create-portfolio design-v2 §3-7・K8）
 *
 * rows  : 合計の前に並べる行（例: 小計・送料・税または関税）。key は行ごとに別の文字
 * total : 合計の行。値は一番大きい字で出す
 *
 * 文字と値は呼ぶ側が t() と書式の関数で作って渡す。この金型は並べるだけで計算しない。
 * 色・余白・角丸・字の大きさはすべて CSS 変数（ADR-067）。
 */
import type { ReactNode } from 'react';
import './TotalsBox.css';

export interface TotalsBoxRow {
  key:   string;
  label: ReactNode;
  value: ReactNode;
}

export interface TotalsBoxProps {
  rows:       TotalsBoxRow[];
  total:      { label: ReactNode; value: ReactNode };
  className?: string;
}

export function TotalsBox({ rows, total, className = '' }: TotalsBoxProps) {
  const cls = ['comp-totals-box', className].filter(Boolean).join(' ');
  return (
    <dl className={cls}>
      {rows.map((row) => (
        <div key={row.key} className="comp-totals-box__row">
          <dt className="comp-totals-box__label">{row.label}</dt>
          <dd className="comp-totals-box__value">{row.value}</dd>
        </div>
      ))}
      <div className="comp-totals-box__row comp-totals-box__row--total">
        <dt className="comp-totals-box__label">{total.label}</dt>
        <dd className="comp-totals-box__value comp-totals-box__value--total">{total.value}</dd>
      </div>
    </dl>
  );
}
