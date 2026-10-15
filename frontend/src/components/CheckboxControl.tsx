/**
 * CheckboxControl — チェック欄金型（design.md §AY-4a、§Z :807/:921）
 *
 * ネイティブ checkbox 1つを返す（div/label を増やさない）。
 * native 属性・イベント（checked/onChange/disabled/id/name/value/aria-* /data-*）はそのまま同じ要素へ渡す。
 * className・style・type・role・size(native) は受けない（見た目はこの部品が決める）。
 * indeterminate は prop で受け、DOM プロパティへ反映する。
 */
import { forwardRef, useCallback, useLayoutEffect, useRef, type InputHTMLAttributes } from "react";
import "./CheckboxControl.css";

export interface CheckboxControlProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className" | "style" | "size" | "role"> {
  size?: "md" | "sm";
  indeterminate?: boolean;
}

export const CheckboxControl = forwardRef<HTMLInputElement, CheckboxControlProps>(function CheckboxControl(
  { size = "md", indeterminate, ...rest },
  ref,
) {
  const innerRef = useRef<HTMLInputElement | null>(null);
  const setRef = useCallback(
    (el: HTMLInputElement | null) => {
      innerRef.current = el;
      if (typeof ref === "function") ref(el);
      else if (ref) ref.current = el;
    },
    [ref],
  );
  // 毎回の描画で反映する（旧 DataTable の ref コールバックと同じ頻度。クリックでブラウザが外した後も prop に戻す）
  useLayoutEffect(() => {
    if (innerRef.current) innerRef.current.indeterminate = !!indeterminate;
  });
  return (
    <input
      ref={setRef}
      type="checkbox"
      className={`comp-checkbox-control${size === "sm" ? " comp-checkbox-control--sm" : ""}`}
      {...rest}
    />
  );
});
CheckboxControl.displayName = "CheckboxControl";
