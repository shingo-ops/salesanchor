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
}

/* ── コンポーネント ──────────────────────────────────────────────────────── */

export function Tabs<K extends string = string>({
  items,
  activeKey,
  onChange,
  variant = "underline",
  size = "md",
  className,
}: TabsProps<K>) {
  const listRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={listRef}
      role="tablist"
      className={[
        "comp-tabs",
        `comp-tabs--${variant}`,
        `comp-tabs--${size}`,
        className,
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
}
