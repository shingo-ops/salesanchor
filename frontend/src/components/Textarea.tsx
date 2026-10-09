/**
 * Textarea — 標準テキストエリア金型（Task 2C）
 *
 * size: sm / md(default) / lg
 * 状態: 通常・focus（CSS）・error・disabled
 *
 * TypeScript の型で規格外 size をコンパイルエラーにする。
 * 実画面への展開は Task 2E で行う。
 *
 * TextareaControl: ラベル・包み div を持たない裸の本体（forwardRef、design.md §AX）。
 */

import { forwardRef, useId } from "react";
import type { TextareaHTMLAttributes } from "react";
import "./FormField.css";

export type TextareaSize = "sm" | "md" | "lg";

interface TextareaOwnProps {
  label?: string;
  helperText?: string;
  error?: string;
  size?: TextareaSize;
  fullWidth?: boolean;
}

export type TextareaProps = TextareaOwnProps &
  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, keyof TextareaOwnProps>;

/** 用途別の種類（design.md §AX-2）。standard 以外は現行ページの見た目を写した固定の見た目で、size は受けない。 */
export type TextareaVariant = "standard" | "karte" | "embedded" | "composer" | "schedule";

export type TextareaControlProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "size"> &
  (
    | { variant?: "standard"; size?: TextareaSize }
    | { variant: Exclude<TextareaVariant, "standard">; size?: never }
  );

export const TextareaControl = forwardRef<HTMLTextAreaElement, TextareaControlProps>(
  function TextareaControl({ size = "md", variant = "standard", className, id, ...rest }, ref) {
    const controlClass = [
      "comp-field__textarea",
      size !== "md" ? `comp-field__textarea--${size}` : "",
      variant !== "standard" ? `comp-textarea--${variant}` : "",
      className ?? "",
    ]
      .filter(Boolean)
      .join(" ");

    return <textarea ref={ref} id={id} className={controlClass} {...rest} />;
  },
);
TextareaControl.displayName = "TextareaControl";

export function Textarea({
  label,
  helperText,
  error,
  size = "md",
  fullWidth = false,
  className,
  id,
  ...rest
}: TextareaProps) {
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
      <TextareaControl id={fieldId} {...rest} />
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
