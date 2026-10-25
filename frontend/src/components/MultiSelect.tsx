/**
 * MultiSelect — 複数選択ドロップダウン金型
 *
 * layout="popover"（既定）: Popover を土台に「ボタン＋メニュー」を描く。メニュー先頭に
 * 「選択をクリア」、その下にチェックの一覧。
 * layout="inline": Popover も開閉ボタンも使わず、その場に見出し・選択の要約・チェックの
 * 一覧をそのまま描く（浮かせられない場所＝Drawer の中で使う。design.md 4-1）。
 *
 * ボタンの表示（popover）: 0件「{label}: {allLabel}」／1件 その選択肢の label／2件以上 countLabel(n)
 * 要約の表示（inline）: 0件 allLabel／1件以上 選んだ label をカンマ+半角スペースでつなぐ（countLabel は使わない）
 * 文言は金型に書かず、呼び出し側が t() で渡す。
 *
 * testid: ボタン `${testId}-button`（inline では出さない）、各選択肢 `${testId}-option-${value}`、クリア `${testId}-clear`
 */
import { useState } from "react";
import { Button } from "./Button";
import { Popover } from "./Popover";
import { CheckboxControl } from "./CheckboxControl";
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
  /** 2件以上のときの文言を返す（layout="inline" では使わない） */
  countLabel: (n: number) => string;
  testId?: string;
  /** 選択肢の出し方。既定 "popover"（ボタンを押すと浮かぶ＝今までどおり）。
   *  "inline" は浮かせず、その場にチェックボックスを並べる（浮かせられない場所＝Drawer の中で使う） */
  layout?: "popover" | "inline";
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
  layout = "popover",
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const tid = (suffix: string): string | undefined => (testId ? `${testId}-${suffix}` : undefined);

  function toggle(value: string) {
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  }

  const menuCls = `comp-multiselect__menu${layout === "popover" ? " comp-multiselect__menu--popover" : ""}`;
  const listCls = `comp-multiselect__list${layout === "popover" ? " comp-multiselect__list--popover" : ""}`;

  const optionRows = options.map((o) => (
    <label
      key={o.value}
      className={`comp-multiselect__option${layout === "inline" ? " comp-multiselect__option--inline" : ""}`}
    >
      <CheckboxControl
        checked={selected.includes(o.value)}
        onChange={() => toggle(o.value)}
        data-testid={tid(`option-${o.value}`)}
      />
      {o.label}
    </label>
  ));

  if (layout === "inline") {
    const selectedLabels = selected.map((v) => options.find((o) => o.value === v)?.label ?? v);
    return (
      <div className={menuCls}>
        <div className="comp-multiselect__inline-head">
          <span className="comp-multiselect__inline-label">{label}</span>
          {selected.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => onChange([])}
              data-testid={tid("clear")}
            >
              {clearLabel}
            </Button>
          )}
        </div>
        <div className="comp-multiselect__inline-summary">
          {selected.length === 0 ? allLabel : selectedLabels.join(", ")}
        </div>
        <div className={listCls}>{optionRows}</div>
      </div>
    );
  }

  let buttonText: string;
  if (selected.length === 0) {
    buttonText = `${label}: ${allLabel}`;
  } else if (selected.length === 1) {
    buttonText = options.find((o) => o.value === selected[0])?.label ?? selected[0];
  } else {
    buttonText = countLabel(selected.length);
  }

  const menu = (
    <div className={menuCls}>
      <Button
        variant="ghost"
        size="sm"
        type="button"
        onClick={() => onChange([])}
        data-testid={tid("clear")}
      >
        {clearLabel}
      </Button>
      <div className={listCls}>{optionRows}</div>
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
