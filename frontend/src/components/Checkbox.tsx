/**
 * Checkbox — 標準チェックボックス金型（ADR-144:59-64 手順・PO 許可済・design.md §3-6(a)）
 *
 * DOM の形は frontend/src/pages/inbox/SalesFormMultiSelect.tsx:126-143 の手本
 * （label > input[type=checkbox] + span）に合わせる。
 * props の書き方は TextField.tsx の Omit<..., keyof OwnProps | "size"> 方式に揃える。
 *
 * size: sm / md(default) / lg
 * 状態: 通常・checked・focus（CSS）・error・disabled・description 付き
 */

import { forwardRef, useId } from "react";
import type { InputHTMLAttributes } from "react";
import "./Checkbox.css";

export type CheckboxSize = "sm" | "md" | "lg";

export interface CheckboxOwnProps {
  label: string;          // 表示済みの文字列（呼び出し側で t() 済み）
  size?: CheckboxSize;    // 既定 "md"
  error?: string;
  description?: string;
}

export type CheckboxProps = CheckboxOwnProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, keyof CheckboxOwnProps | "size" | "type">;

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, size = "md", error, description, className, id, ...rest },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = error != null || description != null ? `${inputId}-hint` : undefined;

  const rootClass = [
    "comp-checkbox",
    size !== "md" ? `comp-checkbox--${size}` : "",
    error != null ? "comp-checkbox--error" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <label className={rootClass} htmlFor={inputId}>
      <input
        ref={ref}
        id={inputId}
        type="checkbox"
        className="comp-checkbox__input"
        aria-describedby={hintId}
        aria-invalid={error != null || undefined}
        {...rest}
      />
      <span className="comp-checkbox__label">
        {label}
        {(error ?? description) != null && (
          <span className="comp-checkbox__description" id={hintId} role={error != null ? "alert" : undefined}>
            {error ?? description}
          </span>
        )}
      </span>
    </label>
  );
});
Checkbox.displayName = "Checkbox";
