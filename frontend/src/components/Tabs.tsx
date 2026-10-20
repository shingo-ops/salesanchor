/**
 * Tabs — 統一タブ金型（Task 5C）
 *
 * 既存3系統を1コンポーネントでカバーする:
 *   - inbox-full-tab-bar  → variant="pill"  size="md"
 *   - right-panel-tab     → variant="underline" size="sm"
 *   - .tab-bar (DS)       → variant="pill"  size="md"
 *
 * @example
 *   <Tabs
 *     items={[{ key: "all", label: "すべて", count: 12 }, ...]}
 *     activeKey="all"
 *     onChange={setTab}
 *     variant="underline"
 *     size="sm"
 *   />
 */
import { useRef } from "react";
import type { ReactNode } from "react";
import { Badge } from "./Badge";
import "./Tabs.css";

/* ── 型定義 ─────────────────────────────────────────────────────────────── */

export interface TabItem<K extends string = string> {
  key: K;
  label: string;
  /** 件数バッジ。0 を渡しても表示する。undefined のみ非表示 */
  count?: number;
  icon?: ReactNode;
  disabled?: boolean;
}

export type TabsVariant = "underline" | "pill";
export type TabsSize    = "sm" | "md";

export interface TabsProps<K extends string = string> {
  items: TabItem<K>[];
  activeKey: K;
  onChange: (key: K) => void;
  variant?: TabsVariant;
  size?: TabsSize;
  className?: string;
  /** タブの右隣に置く部品（例: 「その他」プルダウン）。タブ行の中に並ぶ */
  extra?: ReactNode;
  /** タブ行の右端に置く部品（例: 注記） */
  end?: ReactNode;
}

/* ── コンポーネント ──────────────────────────────────────────────────────── */

export function Tabs<K extends string = string>({
  items,
  activeKey,
  onChange,
  variant = "underline",
  size = "md",
  className,
  extra,
  end,
}: TabsProps<K>) {
  const listRef = useRef<HTMLDivElement>(null);
  const hasBar = extra != null || end != null;

  const list = (
    <div
      ref={listRef}
      role="tablist"
      className={[
        "comp-tabs",
        `comp-tabs--${variant}`,
        `comp-tabs--${size}`,
        hasBar ? "" : className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {items.map((item) => {
        const isActive = item.key === activeKey;
        return (
          <button
            key={item.key}
            role="tab"
            type="button"
            aria-selected={isActive}
            disabled={item.disabled}
            className={[
              "comp-tabs__tab",
              isActive ? "comp-tabs__tab--active" : "",
              item.disabled ? "comp-tabs__tab--disabled" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              if (!item.disabled) onChange(item.key);
            }}
          >
            {item.icon != null && (
              <span className="comp-tabs__icon" aria-hidden="true">
                {item.icon}
              </span>
            )}
            <span className="comp-tabs__label">{item.label}</span>
            {item.count !== undefined && (
              <Badge variant="neutral" appearance="soft" size="sm">
                {String(item.count)}
              </Badge>
            )}
          </button>
        );
      })}
    </div>
  );

  if (!hasBar) return list;

  return (
    <div
      className={["comp-tabs-bar", `comp-tabs-bar--${variant}`, className]
        .filter(Boolean)
        .join(" ")}
    >
      {list}
      {extra != null && <div className="comp-tabs-bar__extra">{extra}</div>}
      {end != null && <div className="comp-tabs-bar__end">{end}</div>}
    </div>
  );
}
