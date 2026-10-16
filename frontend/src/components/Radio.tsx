/**
 * Radio — 標準ラジオボタン金型（文字と並ぶ欄）（design.md §AY-5、Checkbox と同じ形）
 *
 * .form-group の中では使えない（components.css:11・:19 の規則が勝って崩れる。残件 §2）。
 * props の書き方は TextField.tsx の Omit<..., keyof OwnProps | "size"> 方式に揃える。
 *
 * size: sm / md(default) / lg
 * 状態: 通常・checked・focus（CSS）・error・disabled・description 付き
 */

import { forwardRef, useId } from "react";
import type { InputHTMLAttributes } from "react";
import "./Radio.css";

export type RadioSize = "sm" | "md" | "lg";

export interface RadioOwnProps {
  label: string;          // 表示済みの文字列（呼び出し側で t() 済み）
  size?: RadioSize;       // 既定 "md"
  error?: string;
  description?: string;
}

export type RadioProps = RadioOwnProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, keyof RadioOwnProps | "size" | "type">;

export const Radio = forwardRef<HTMLInputElement, RadioProps>(function Radio(
  { label, size = "md", error, description, className, id, ...rest },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = error != null || description != null ? `${inputId}-hint` : undefined;

  const rootClass = [
    "comp-radio",
    size !== "md" ? `comp-radio--${size}` : "",
    error != null ? "comp-radio--error" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <label className={rootClass} htmlFor={inputId}>
      <input
        ref={ref}
        id={inputId}
        type="radio"
        className="comp-radio__input"
        aria-describedby={hintId}
        aria-invalid={error != null || undefined}
        {...rest}
      />
      <span className="comp-radio__label">
        {label}
        {(error ?? description) != null && (
          <span className="comp-radio__description" id={hintId} role={error != null ? "alert" : undefined}>
            {error ?? description}
          </span>
        )}
      </span>
    </label>
  );
});
Radio.displayName = "Radio";
