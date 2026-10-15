/**
 * Toggle — 切替スイッチ金型（design.md §AY-3b）
 *
 * ネイティブ checkbox に role="switch" を付けた型。状態は持たない（controlled）。
 * className・style は受けない（見た目はこの部品が決める）。
 * 名前は id＋外側の label、または aria-label／aria-labelledby で与える。
 */

import { forwardRef } from "react";
import "./Toggle.css";

export interface ToggleProps {
  checked: boolean;
  onCheckedChange: (next: boolean) => void;
  disabled?: boolean;
  id?: string;
  "aria-label"?: string;
  "aria-labelledby"?: string;
}

export const Toggle = forwardRef<HTMLInputElement, ToggleProps>(function Toggle(
  { checked, onCheckedChange, disabled, id, ...aria },
  ref,
) {
  return (
    <label className={`comp-toggle${disabled ? " comp-toggle--disabled" : ""}`}>
      <input
        ref={ref}
        id={id}
        type="checkbox"
        role="switch"
        className="comp-toggle__input"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onCheckedChange(e.target.checked)}
        {...aria}
      />
      <span className="comp-toggle__track" aria-hidden="true" />
    </label>
  );
});
