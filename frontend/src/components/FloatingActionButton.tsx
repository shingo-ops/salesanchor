/**
 * FloatingActionButton — 画面の右下に浮かぶ丸い印の金型（ADR-144・ADR-067）
 *
 * 金型 Button は使わない。理由: Button の丸い形はログイン画面だけに決められている
 * （buttonShapeUsage.test.ts が強制）ため、全画面に浮かぶこの印には使えない。
 * 色の変数（主ボタンと同じもの）だけを借りる。「primary は 1 画面に 1 個」は
 * Button の variant の決まりで、この印は別の金型なので数に入れない。
 *
 * 画面の言葉は持たない。label は呼ぶ側が t() で渡す（ADR-027）。
 */

import type { ReactNode } from "react";
import "./FloatingActionButton.css";

export interface FloatingActionButtonProps {
  icon: ReactNode;
  /** aria-label と title に使う。呼ぶ側が t() で渡す */
  label: string;
  onClick?: () => void;
  /** 0 や未指定なら出さない */
  badge?: number;
  /** スマホの殻で true にすると、下のタブの帯に重ならない位置になる */
  aboveTabbar?: boolean;
  className?: string;
}

export function FloatingActionButton({
  icon,
  label,
  onClick,
  badge,
  aboveTabbar = false,
  className,
}: FloatingActionButtonProps) {
  const classes = ["comp-fab", aboveTabbar ? "comp-fab--above-tabbar" : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <button type="button" className={classes} aria-label={label} title={label} onClick={onClick}>
      <span className="comp-fab__icon" aria-hidden="true">{icon}</span>
      {badge ? <span className="comp-fab__badge">{badge}</span> : null}
    </button>
  );
}
