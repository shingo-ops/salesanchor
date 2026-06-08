/**
 * SubMenu — 縦型サイドナビゲーション（Task 6C）
 * ADR-067: 全カラーは CSS 変数参照のみ
 *
 * variant:
 *   grouped — グループ見出し付き縦型（hub-subnav 系・将来統合先）
 *   flat    — フラット縦型（グループ見出しなし）
 */
import type { ReactNode } from "react";
import "./SubMenu.css";

export interface SubMenuItem<K extends string = string> {
  key: K;
  label: string;
  icon?: ReactNode;
  /** 件数バッジ（数字） */
  badge?: number;
  disabled?: boolean;
}

export interface SubMenuGroup<K extends string = string> {
  /** グループ見出し（grouped バリアントのみ表示。undefined = 無見出し） */
  title?: string;
  items: SubMenuItem<K>[];
}

export type SubMenuVariant = "grouped" | "flat";

export interface SubMenuProps<K extends string = string> {
  variant?: SubMenuVariant;
  groups: SubMenuGroup<K>[];
  activeKey: K;
  onChange: (key: K) => void;
  className?: string;
}

export function SubMenu<K extends string = string>({
  variant = "grouped",
  groups,
  activeKey,
  onChange,
  className,
}: SubMenuProps<K>) {
  const showTitles = variant === "grouped";

  return (
    <nav
      className={[
        "comp-subnav",
        `comp-subnav--${variant}`,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {groups.map((group, gi) => (
        <div key={group.title ?? String(gi)} className="comp-subnav__group">
          {showTitles && group.title && (
            <span className="comp-subnav__group-title">{group.title}</span>
          )}
          {group.items.map((item) => {
            const isActive = activeKey === item.key;
            return (
              <button
                key={item.key}
                type="button"
                className={[
                  "comp-subnav__item",
                  isActive       && "comp-subnav__item--active",
                  item.disabled  && "comp-subnav__item--disabled",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => !item.disabled && onChange(item.key)}
                disabled={item.disabled}
                aria-current={isActive ? "page" : undefined}
              >
                {item.icon && (
                  <span className="comp-subnav__icon">{item.icon}</span>
                )}
                <span className="comp-subnav__label">{item.label}</span>
                {item.badge !== undefined && (
                  <span className="comp-subnav__badge">{item.badge}</span>
                )}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
