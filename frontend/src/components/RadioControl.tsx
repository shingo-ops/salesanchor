/**
 * RadioControl — ラジオボタン金型（単独の欄）（design.md §AY-5、§Z :807/:921）
 *
 * ネイティブ radio 1つを返す（div/label を増やさない）。radio のネイティブ挙動（name で1つだけ選ぶ・矢印キー）はそのまま。
 * native 属性・イベント（checked/onChange/readOnly/disabled/id/name/value/aria-* /data-*）はそのまま同じ要素へ渡す。
 * className・style・type・role・size(native) は受けない（見た目はこの部品が決める）。
 */
import { forwardRef, type InputHTMLAttributes } from "react";
import "./RadioControl.css";

export type RadioControlProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className" | "style" | "size" | "role">;

export const RadioControl = forwardRef<HTMLInputElement, RadioControlProps>(function RadioControl(props, ref) {
  return <input ref={ref} type="radio" className="comp-radio-control" {...props} />;
});
RadioControl.displayName = "RadioControl";
