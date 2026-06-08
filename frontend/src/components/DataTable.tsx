/**
 * DataTable — 汎用データテーブル（Task 4C）
 *
 * 機能:
 *   columns   : 型付き列定義（key / header / width / sortable / renderCell）
 *   data      : 表示行データ
 *   rowKey    : 行識別子ファクトリ（string 返却）
 *   sort      : 制御型ソート（sortKey + sortDir + onSort コールバック）
 *   selectable: 行チェックボックス選択（selectedKeys Set + onSelectChange）
 *   density   : compact / default / relaxed — 行高さを切り替え
 *   emptyState: データ 0 件時のカスタム表示スロット
 *
 * 使用方針:
 *   - ソート・選択は呼び出し側 (controlled) で管理する。
 *   - セル内に日本語ラベルを埋め込まない（columns.header / emptyState を通じて渡す）。
 *   - 水平スクロールはラッパー (.comp-table) が担当。
 */
import type { ReactNode } from 'react';
import { TABLE_ICONS } from '../constants/icons';
import './DataTable.css';

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

export interface DataTableColumn<T = Record<string, unknown>> {
  /** data オブジェクトのキー（renderCell が無い場合に String(row[key]) を表示） */
  key: string;
  /** ヘッダーラベル */
  header: string;
  /** 列幅（CSS width 値。例: "120px", "1fr"） */
  width?: string;
  /** ソートボタンを表示するか */
  sortable?: boolean;
  /** カスタムセルレンダラー */
  renderCell?: (row: T, rowKey: string) => ReactNode;
}

export type SortDir = 'asc' | 'desc';
export type DataTableDensity = 'compact' | 'default' | 'relaxed';

export interface DataTableProps<T = Record<string, unknown>> {
  columns: DataTableColumn<T>[];
  data: T[];
  /** 行識別子を返すファクトリ（一意な string 必須） */
  rowKey: (row: T) => string;
  /** 現在ソート中の列 key */
  sortKey?: string;
  /** ソート方向 */
  sortDir?: SortDir;
  /** ソートクリック時のコールバック */
  onSort?: (key: string, dir: SortDir) => void;
  /** チェックボックス列を表示するか */
  selectable?: boolean;
  /** 選択済み rowKey の集合 */
  selectedKeys?: Set<string>;
  /** 選択状態変更コールバック */
  onSelectChange?: (keys: Set<string>) => void;
  /** 行の高さバリアント */
  density?: DataTableDensity;
  /** データが 0 件の場合に表示するノード */
  emptyState?: ReactNode;
  className?: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// コンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function DataTable<T = Record<string, unknown>>({
  columns,
  data,
  rowKey,
  sortKey,
  sortDir = 'asc',
  onSort,
  selectable = false,
  selectedKeys,
  onSelectChange,
  density = 'default',
  emptyState,
  className = '',
}: DataTableProps<T>) {
  const allKeys = data.map(rowKey);
  const selected = selectedKeys ?? new Set<string>();

  const allSelected = allKeys.length > 0 && allKeys.every((k) => selected.has(k));
  const someSelected = !allSelected && allKeys.some((k) => selected.has(k));

  function toggleAll() {
    if (!onSelectChange) return;
    if (allSelected) {
      onSelectChange(new Set());
    } else {
      onSelectChange(new Set(allKeys));
    }
  }

  function toggleRow(key: string) {
    if (!onSelectChange) return;
    const next = new Set(selected);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    onSelectChange(next);
  }

  function handleSort(key: string) {
    if (!onSort) return;
    const nextDir: SortDir =
      sortKey === key && sortDir === 'asc' ? 'desc' : 'asc';
    onSort(key, nextDir);
  }

  const wrapperCls = [
    'comp-table',
    `comp-table--${density}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={wrapperCls} role="region" aria-label="data table">
      <table className="comp-table__table">
        <thead>
          <tr className="comp-table__head-row">
            {selectable && (
              <th className="comp-table__th comp-table__th--check" aria-label="select all">
                <input
                  type="checkbox"
                  className="comp-table__check"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected;
                  }}
                  onChange={toggleAll}
                  aria-label="select all rows"
                />
              </th>
            )}
            {columns.map((col) => (
              <th
                key={col.key}
                className="comp-table__th"
                style={col.width ? { width: col.width } : undefined}
                aria-sort={
                  col.sortable && sortKey === col.key
                    ? sortDir === 'asc' ? 'ascending' : 'descending'
                    : undefined
                }
              >
                {col.sortable && onSort ? (
                  <button
                    type="button"
                    className={[
                      'comp-table__sort-btn',
                      sortKey === col.key ? 'comp-table__sort-btn--active' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => handleSort(col.key)}
                  >
                    {col.header}
                    <span className="comp-table__sort-icon" aria-hidden="true">
                      {sortKey === col.key ? (
                        sortDir === 'asc'
                          ? <TABLE_ICONS.sortAsc size={12} />
                          : <TABLE_ICONS.sortDesc size={12} />
                      ) : (
                        <TABLE_ICONS.sortAsc size={12} />
                      )}
                    </span>
                  </button>
                ) : (
                  col.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                className="comp-table__empty"
                colSpan={columns.length + (selectable ? 1 : 0)}
              >
                {emptyState ?? 'No data'}
              </td>
            </tr>
          ) : (
            data.map((row) => {
              const key = rowKey(row);
              const isSelected = selected.has(key);
              return (
                <tr
                  key={key}
                  className={[
                    'comp-table__row',
                    isSelected ? 'comp-table__row--selected' : '',
                  ].filter(Boolean).join(' ')}
                >
                  {selectable && (
                    <td className="comp-table__td comp-table__td--check">
                      <input
                        type="checkbox"
                        className="comp-table__check"
                        checked={isSelected}
                        onChange={() => toggleRow(key)}
                        aria-label={`select row ${key}`}
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td key={col.key} className="comp-table__td">
                      {col.renderCell
                        ? col.renderCell(row, key)
                        : String((row as Record<string, unknown>)[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
