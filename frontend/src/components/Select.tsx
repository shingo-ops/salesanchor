/**
 * Select — 標準セレクト金型（Task 2C）
 *
 * size: sm / md(default) / lg
 * 状態: 通常・focus（CSS）・error・disabled
 *
 * TypeScript の型で規格外 size・options をコンパイルエラーにする。
 * 実画面への展開は Task 2E で行う。
 */

import { forwardRef, useId } from "react";
import type { ReactNode, SelectHTMLAttributes } from "react";
import "./FormField.css";

export type SelectSize = "sm" | "md" | "lg";
export type SelectIndicator = "default" | "none";

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

type SelectControlNativeProps = Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  keyof SelectControlOwnProps | "indicator" | "children"
>;

interface SelectControlOptionsModeProps extends SelectControlOwnProps, SelectControlNativeProps {
  indicator?: SelectIndicator;
  children?: never;
}

interface SelectControlChildrenModeProps
  extends Pick<SelectControlOwnProps, "size" | "fullWidth" | "appearance">,
    SelectControlNativeProps {
  indicator?: SelectIndicator;
  children: ReactNode;
  options?: never;
  placeholder?: never;
}

export type SelectControlProps = SelectControlOptionsModeProps | SelectControlChildrenModeProps;

export const SelectControl = forwardRef<HTMLSelectElement, SelectControlProps>(
  function SelectControl(props, ref) {
    const {
      options,
      children,
      size = "md",
      fullWidth = false,
      placeholder,
      appearance = "bare",
      indicator = "default",
      className,
      ...rest
    } = props;

    const controlClass = [
      appearance === "field" ? "comp-field__select" : "comp-select__control",
      appearance !== "field" && size !== "md" ? `comp-select__control--${size}` : "",
      appearance !== "field" && fullWidth ? "comp-select__control--full" : "",
      indicator === "none" ? "comp-select--no-indicator" : "",
      className ?? "",
    ]
      .filter(Boolean)
      .join(" ");

    if (props.options === undefined) {
      return (
        <select ref={ref} className={controlClass} {...rest}>
          {children}
        </select>
      );
    }

    return (
      <select ref={ref} className={controlClass} {...rest}>
        {placeholder != null && (
          <option value="" disabled={rest.required}>
            {placeholder}
          </option>
        )}
        {props.options.map((opt) => (
          <option key={opt.value} value={opt.value} disabled={opt.disabled}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  },
);
SelectControl.displayName = "SelectControl";

interface SelectOwnProps extends SelectControlOwnProps {
  label?: string;
  helperText?: string;
  error?: string;
}

export type SelectProps = SelectOwnProps &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, keyof SelectOwnProps | "children">;

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
