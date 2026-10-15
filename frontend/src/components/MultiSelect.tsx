/**
 * MultiSelect — 複数選択ドロップダウン金型
 *
 * Popover を土台に「ボタン＋メニュー」を描く。メニュー先頭に「選択をクリア」、
 * その下にチェックの一覧。
 *
 * ボタンの表示: 0件「{label}: {allLabel}」／1件 その選択肢の label／2件以上 countLabel(n)
 * 文言は金型に書かず、呼び出し側が t() で渡す。
 *
 * testid: ボタン `${testId}-button`、各選択肢 `${testId}-option-${value}`、クリア `${testId}-clear`
 */
import { useState } from "react";
import { Button } from "./Button";
import { Popover } from "./Popover";
import "./MultiSelect.css";

export interface MultiSelectOption {
  value: string;
  label: string;
}

export interface MultiSelectProps {
  /** 項目名（ボタンの「{label}: {allLabel}」に使う） */
  label: string;
  options: MultiSelectOption[];
  /** 選択中の value */
  selected: string[];
  onChange: (next: string[]) => void;
  /** 「選択をクリア」ボタンの文言 */
  clearLabel: string;
  /** 0件のときの文言（例: すべて） */
  allLabel: string;
  /** 2件以上のときの文言を返す */
  countLabel: (n: number) => string;
  testId?: string;
}

export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  clearLabel,
  allLabel,
  countLabel,
  testId,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const tid = (suffix: string): string | undefined => (testId ? `${testId}-${suffix}` : undefined);

  let buttonText: string;
  if (selected.length === 0) {
    buttonText = `${label}: ${allLabel}`;
  } else if (selected.length === 1) {
    buttonText = options.find((o) => o.value === selected[0])?.label ?? selected[0];
  } else {
    buttonText = countLabel(selected.length);
  }

  function toggle(value: string) {
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  }

  const menu = (
    <div className="comp-multiselect__menu">
      <Button
        variant="ghost"
        size="sm"
        type="button"
        onClick={() => onChange([])}
        data-testid={tid("clear")}
      >
        {clearLabel}
      </Button>
      <div className="comp-multiselect__list">
        {options.map((o) => (
          <label key={o.value} className="comp-multiselect__option">
            <input
              type="checkbox"
              className="comp-multiselect__check"
              checked={selected.includes(o.value)}
              onChange={() => toggle(o.value)}
              data-testid={tid(`option-${o.value}`)}
            />
            {o.label}
          </label>
        ))}
      </div>
    </div>
  );

  return (
    <Popover content={menu} open={open} onOpenChange={setOpen}>
      <Button variant="secondary" size="sm" type="button" aria-haspopup="dialog" aria-expanded={open} data-testid={tid("button")}>
        {buttonText}
      </Button>
    </Popover>
  );
}
