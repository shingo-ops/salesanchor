/**
 * ColorSwatchPicker — 色見本から 1 つ選ぶ金型（ADR-1081・ADR-144）
 *
 * 開くボタンを押すと下に丸の一覧が開く。中は本物のラジオ（RadioControl）で、同じ name なので矢印キーで動ける。
 * 予定のことは知らない。選択肢（名・地の色）は呼ぶ側が渡す。体の外へ移さない（Portal・Popover を使わない）。
 */
import { useState } from "react";
import { Button } from "./Button";
import { RadioControl } from "./RadioControl";
import "./ColorSwatchPicker.css";

export interface ColorSwatchOption {
  /** null はデフォルト */
  value: string | null;
  /** 読み上げと見出しに使う名（呼ぶ側が t() で渡す） */
  label: string;
  /** 丸の地。var(--...) の文字か、呼ぶ側の色の値をそのまま */
  color: string;
}

export interface ColorSwatchPickerProps {
  /** 欄の名（radiogroup と開くボタンの読み上げ） */
  label: string;
  options: ColorSwatchOption[];
  value: string | null;
  onChange: (value: string | null) => void;
  /** ラジオの name（同じ画面に 2 つ出ても混ざらない名を呼ぶ側が渡す） */
  name: string;
  /** 外側配置専用のクラス（Button の layoutClassName と同じ考え） */
  layoutClassName?: string;
}

export function ColorSwatchPicker({ label, options, value, onChange, name, layoutClassName }: ColorSwatchPickerProps) {
  const [open, setOpen] = useState(false);
  const current = options.find((option) => option.value === value) ?? options[0];
  const rootClass = ["comp-color-swatch-picker", layoutClassName].filter(Boolean).join(" ");

  return (
    <div className={rootClass}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-expanded={open}
        aria-label={`${label}: ${current?.label ?? ""}`}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="comp-color-swatch-picker__dot" style={{ background: current?.color }} aria-hidden="true" />
        {current?.label}
      </Button>
      {open && (
        <div className="comp-color-swatch-picker__grid" role="radiogroup" aria-label={label}>
          {options.map((option) => {
            const selected = option.value === value;
            return (
              <label
                key={option.value ?? "__default"}
                className={
                  "comp-color-swatch-picker__swatch" + (selected ? " comp-color-swatch-picker__swatch--selected" : "")
                }
                style={{ background: option.color }}
                title={option.label}
              >
                <RadioControl
                  name={name}
                  value={option.value ?? ""}
                  checked={selected}
                  onChange={() => onChange(option.value)}
                  aria-label={option.label}
                />
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
