/**
 * MultiSelect — 複数選択ドロップダウン金型
 *
 * layout="popover"（既定）: Popover を土台に「ボタン＋メニュー」を描く。メニュー先頭に
 * 「選択をクリア」、その下にチェックの一覧。
 * layout="inline": Popover も開閉ボタンも使わず、その場に見出し・選択の要約・チェックの
 * 一覧をそのまま描く（浮かせられない場所＝Drawer の中で使う。design.md 4-1）。
 * layout="row"（便2・design.md 4-2）: 押せる1行。左にラベル／右に現在値／右端に「>」。
 * 選択はこの layout では行わない。押すと onOpen を呼ぶだけ（選択画面への入口）。
 *
 * ボタンの表示（popover）: 0件「{label}: {allLabel}」／1件 その選択肢の label／2件以上 countLabel(n)
 * 要約の表示（inline・row の現在値）: 0件 allLabel／1件以上 選んだ label をカンマ+半角スペースでつなぐ
 * （countLabel は使わない）。名前の解決は常に `allOptions ?? options` から行う（検索で options を
 * 絞っても選択済みの名前が生の値に化けないため。design.md 4-2・審査指摘6）。
 * options が空のときは一覧の代わりに emptyLabel を描く（design.md 4-2・審査指摘7）。
 * 文言は金型に書かず、呼び出し側が t() で渡す。
 *
 * testid: ボタン `${testId}-button`（inline/row では出さない）、行 `${testId}-row`（layout="row" のみ）、
 * 各選択肢 `${testId}-option-${value}`、クリア `${testId}-clear`
 */
import { useState } from "react";
import { Button } from "./Button";
import { Popover } from "./Popover";
import { CheckboxControl } from "./CheckboxControl";
import { ChevronRight } from "../constants/icons-base";
import "./MultiSelect.css";

export interface MultiSelectOption {
  value: string;
  label: string;
}

export interface MultiSelectProps {
  /** 項目名（ボタンの「{label}: {allLabel}」・row の左側ラベルに使う） */
  label: string;
  options: MultiSelectOption[];
  /** 選んだ名前を引くための全件。省略時は options。検索で options を絞っても
   *  選択済みの名前を正しく解決するために使う（design.md 4-2・審査指摘6） */
  allOptions?: MultiSelectOption[];
  /** 選択中の value */
  selected: string[];
  onChange: (next: string[]) => void;
  /** 「選択をクリア」ボタンの文言 */
  clearLabel: string;
  /** 0件のときの文言（例: すべて） */
  allLabel: string;
  /** 2件以上のときの文言を返す（layout="inline"・"row" では使わない） */
  countLabel: (n: number) => string;
  /** options が空のときに一覧の代わりに出す文言（design.md 4-2・審査指摘7） */
  emptyLabel?: string;
  testId?: string;
  /** 選択肢の出し方。既定 "popover"（ボタンを押すと浮かぶ＝今までどおり）。
   *  "inline" は浮かせず、その場にチェックボックスを並べる（浮かせられない場所＝Drawer の中で使う）。
   *  "row" は押せる1行（選択画面への入口。design.md 4-2） */
  layout?: "popover" | "inline" | "row";
  /** layout="row" で行を押したときに呼ばれる */
  onOpen?: () => void;
}

export function MultiSelect({
  label,
  options,
  allOptions,
  selected,
  onChange,
  clearLabel,
  allLabel,
  countLabel,
  emptyLabel,
  testId,
  layout = "popover",
  onOpen,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const tid = (suffix: string): string | undefined => (testId ? `${testId}-${suffix}` : undefined);
  const namesByValue = allOptions ?? options;
  const resolveLabel = (v: string): string => namesByValue.find((o) => o.value === v)?.label ?? v;
  const selectedSummary = selected.length === 0 ? allLabel : selected.map(resolveLabel).join(", ");

  function toggle(value: string) {
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  }

  const menuCls = `comp-multiselect__menu${layout === "popover" ? " comp-multiselect__menu--popover" : ""}`;
  const listCls = `comp-multiselect__list${layout === "popover" ? " comp-multiselect__list--popover" : ""}`;

  const optionRows = options.length === 0 ? (
    <div className="comp-multiselect__empty">{emptyLabel}</div>
  ) : options.map((o) => (
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

  if (layout === "row") {
    return (
      <button
        type="button"
        className="comp-multiselect__row"
        onClick={onOpen}
        data-testid={tid("row")}
      >
        <span className="comp-multiselect__row-label">{label}</span>
        <span className="comp-multiselect__row-value">{selectedSummary}</span>
        <ChevronRight size={18} aria-hidden="true" className="comp-multiselect__row-chevron" />
      </button>
    );
  }

  if (layout === "inline") {
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
          {selectedSummary}
        </div>
        <div className={listCls}>{optionRows}</div>
      </div>
    );
  }

  let buttonText: string;
  if (selected.length === 0) {
    buttonText = `${label}: ${allLabel}`;
  } else if (selected.length === 1) {
    buttonText = resolveLabel(selected[0]);
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
