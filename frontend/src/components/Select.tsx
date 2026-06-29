/**
 * Select — 標準セレクト金型（Task 2C）
 *
 * size: sm / md(default) / lg
 * 状態: 通常・focus（CSS）・error・disabled
 *
 * TypeScript の型で規格外 size・options をコンパイルエラーにする。
 * 実画面への展開は Task 2E で行う。
 */

import { useId } from "react";
import type { SelectHTMLAttributes } from "react";
import "./FormField.css";

export type SelectSize = "sm" | "md" | "lg";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectControlOwnProps {
  options: SelectOption[];
  size?: SelectSize;
  fullWidth?: boolean;
  placeholder?: string;
  appearance?: "field" | "bare";
}

export type SelectControlProps = SelectControlOwnProps &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, keyof SelectControlOwnProps>;

export function SelectControl({
  options,
  size = "md",
  fullWidth = false,
  placeholder,
  appearance = "bare",
  className,
  ...rest
}: SelectControlProps) {
  const controlClass = [
    appearance === "field" ? "comp-field__select" : "comp-select__control",
    appearance !== "field" && size !== "md" ? `comp-select__control--${size}` : "",
    appearance !== "field" && fullWidth ? "comp-select__control--full" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <select className={controlClass} {...rest}>
      {placeholder != null && (
        <option value="" disabled={rest.required}>
          {placeholder}
        </option>
      )}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} disabled={opt.disabled}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

interface SelectOwnProps extends SelectControlOwnProps {
  label?: string;
  helperText?: string;
  error?: string;
}

export type SelectProps = SelectOwnProps &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, keyof SelectOwnProps>;

export function Select({
  options,
  label,
  helperText,
  error,
  size = "md",
  fullWidth = false,
  placeholder,
  className,
  id,
  ...rest
}: SelectProps) {
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
      <SelectControl
        id={fieldId}
        options={options}
        size={size}
        fullWidth={fullWidth}
        placeholder={placeholder}
        appearance="field"
        {...rest}
      />
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
