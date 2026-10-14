/**
 * ChoiceCardGroup — 質問に答えるカード型の選択肢（ラジオ型）の金型（ADR-144）
 *
 * legend : 質問文（画面に見える。呼び出し側で t() 済み）
 * name   : radio の name
 * options: 選択肢（label / description も呼び出し側で t() 済み）
 * value  : 選ばれている値（未選択は null）
 *
 * 中身は fieldset + legend + radio。radio は見た目だけ隠し、フォーカスと矢印キー操作はブラウザ標準のまま。
 * 縦並び（1列）。幅は親に合わせる。
 */
import './ChoiceCardGroup.css';

export type ChoiceCardOption<V extends string> = {
  value: V;
  label: string;
  description?: string;
  disabled?: boolean;
};

export type ChoiceCardGroupProps<V extends string> = {
  legend: string;
  name: string;
  options: ChoiceCardOption<V>[];
  value: V | null;
  onChange: (value: V) => void;
};

export function ChoiceCardGroup<V extends string>({ legend, name, options, value, onChange }: ChoiceCardGroupProps<V>) {
  return (
    <fieldset className="comp-choice-card-group">
      <legend className="comp-choice-card-group__legend">{legend}</legend>
      {options.map((option) => (
        <label
          key={option.value}
          className={['comp-choice-card', option.disabled ? 'comp-choice-card--disabled' : ''].filter(Boolean).join(' ')}
        >
          <input
            type="radio"
            className="comp-choice-card__input"
            name={name}
            value={option.value}
            checked={value === option.value}
            disabled={option.disabled}
            onChange={() => onChange(option.value)}
          />
          <span className="comp-choice-card__label">{option.label}</span>
          {option.description !== undefined && <span className="comp-choice-card__description">{option.description}</span>}
        </label>
      ))}
    </fieldset>
  );
}
