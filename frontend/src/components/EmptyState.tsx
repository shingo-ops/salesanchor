/**
 * EmptyState 金型（Task 8C）
 *
 * データが0件のとき（リストなし・検索結果なし・受信箱空）に表示する標準ウィジェット。
 *
 * - icon: アイコン（任意）推奨サイズ: default=ICON.xl(48px) / compact=ICON.lg(24px)
 * - title: 見出し（必須）
 * - description: 説明文（任意）
 * - action: アクションボタン（任意）— 標準 Button を渡す
 * - size: "default"（全画面・大きめ）/ "compact"（テーブルやカード内）
 */

import type { ReactNode } from "react";
import "./EmptyState.css";

export type EmptyStateSize = "default" | "compact";

interface EmptyStateProps {
  /** アイコン要素（任意）。推奨: default → ICON.xl(48px) / compact → ICON.lg(24px) */
  icon?: ReactNode;
  /** 見出し（必須） */
  title: string;
  /** 説明文（任意） */
  description?: string;
  /** アクション（任意）— `<Button>` を渡す */
  action?: ReactNode;
  /** default: 全画面パディング大 / compact: テーブル・カード内の小さめ表示 */
  size?: EmptyStateSize;
  /** 追加クラス */
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  size = "default",
  className,
}: EmptyStateProps) {
  const classes = [
    "comp-empty",
    size === "compact" ? "comp-empty--compact" : "",
    className ?? "",
  ].filter(Boolean).join(" ");

  return (
    <div className={classes}>
      {icon != null && (
        <div className="comp-empty__icon" aria-hidden="true">{icon}</div>
      )}
      <p className="comp-empty__title">{title}</p>
      {description != null && (
        <p className="comp-empty__desc">{description}</p>
      )}
      {action != null && (
        <div className="comp-empty__action">{action}</div>
      )}
    </div>
  );
}
