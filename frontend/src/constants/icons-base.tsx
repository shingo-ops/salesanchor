/**
 * 閲覧ページ（JS 上限300KB）が使う最小のアイコン。定義はここだけ。
 * icons.tsx が再 export する（design inventory-name-hover-card §3-8）
 */

import { forwardRef } from "react";
import type { ComponentType, SVGProps, ForwardRefExoticComponent, RefAttributes } from "react";
import { ArrowUpIcon, ArrowDownIcon, XMarkIcon, ArrowTopRightOnSquareIcon, ArrowLeftIcon, ChevronRightIcon } from "@heroicons/react/24/solid";

/** アイコンコンポーネントが受け取る props */
export type IconProps = {
  size?: number | string;
  weight?: string;  // Heroicons では無視（solid 固定）
  className?: string;
} & Pick<SVGProps<SVGSVGElement>, "aria-hidden" | "aria-label" | "aria-labelledby" | "aria-describedby" | "role" | "focusable">;

/** アイコンコンポーネント型 — 全 ICON_* 定数の値型 */
export type Icon = ForwardRefExoticComponent<IconProps & RefAttributes<SVGSVGElement>>;

// 後方互換エイリアス（RolesPage.tsx 等が LucideIcon 型を参照しているため）
export type LucideIcon = Icon;

/**
 * Heroicons コンポーネントを Icon API（size/weight/ARIA props）に変換するアダプター。
 * weight は受け取るが無視（solid 固定）。
 */
export function hi(HeroIcon: ComponentType<SVGProps<SVGSVGElement>>): Icon {
  const Wrapped = forwardRef<SVGSVGElement, IconProps>(
    ({ size = 24, className, "aria-hidden": ariaHidden = true, "aria-label": ariaLabel,
      "aria-labelledby": ariaLabelledBy, "aria-describedby": ariaDescribedBy, role, focusable }, ref) => (
      <HeroIcon
        ref={ref}
        width={size}
        height={size}
        className={className}
        aria-hidden={ariaHidden}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        aria-describedby={ariaDescribedBy}
        role={role}
        focusable={focusable}
      />
    )
  );
  return Wrapped as unknown as Icon;
}

export const ArrowUp = hi(ArrowUpIcon);
export const ArrowDown = hi(ArrowDownIcon);
export const X = hi(XMarkIcon);
export const ArrowTopRight = hi(ArrowTopRightOnSquareIcon);
/** Drawer の「← 戻る」用（design.md 4-1・4-3） */
export const ArrowLeft = hi(ArrowLeftIcon);
/** MultiSelect layout="row" の右端「>」用（design.md 4-2・4-3） */
export const ChevronRight = hi(ChevronRightIcon);
export const TABLE_ICONS = {
  sortAsc:  ArrowUp,
  sortDesc: ArrowDown,
} satisfies Record<string, Icon>;
