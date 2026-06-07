/**
 * TextField — 標準テキスト入力金型（Task 2C）
 *
 * type: text / email / number / password / tel / url / search / date
 * size: sm / md(default) / lg
 * 状態: 通常・focus（CSS）・error・disabled
 *
 * TypeScript の型で規格外 size をコンパイルエラーにする。
 * 実画面への展開は Task 2E で行う。
 */

import { useId } from "react";
import type { InputHTMLAttributes } from "react";
import "./FormField.css";

export type TextFieldSize = "sm" | "md" | "lg";

interface TextFieldOwnProps {
  label?: string;
  helperText?: string;
  error?: string;
  size?: TextFieldSize;
  fullWidth?: boolean;
}

export type TextFieldProps = TextFieldOwnProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, keyof TextFieldOwnProps | "size">;

export function TextField({
  label,
  helperText,
  error,
  size = "md",
  fullWidth = false,
  className,
  id,
  ...rest
}: TextFieldProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;

  const containerClass = [
    "comp-field",
    size !== "md" ? `comp-field--${size}` : "",
    fullWidth ? "comp-field--full" : "",
    error ? "comp-field--error" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={containerClass}>
      {label != null && (
        <label htmlFor={fieldId} className="comp-field__label">
          {label}
          {rest.required && (
            <span className="comp-field__required" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      <input id={fieldId} className="comp-field__input" {...rest} />
      {(error != null || helperText != null) && (
        <p
          className={`comp-field__hint${error != null ? " comp-field__hint--error" : ""}`}
          role={error != null ? "alert" : undefined}
        >
          {error ?? helperText}
        </p>
      )}
    </div>
  );
}
