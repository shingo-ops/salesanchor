/**
 * DataTable — 汎用データテーブル（Task 4C）
 *
 * 機能:
 *   columns     : 型付き列定義（key / header / width / sortable / renderCell）
 *   data        : 表示行データ
 *   rowKey      : 行識別子ファクトリ（string 返却）
 *   sort        : 制御型ソート（sortKey + sortDir + onSort コールバック）
 *   selectable  : 行チェックボックス選択（selectedKeys Set + onSelectChange）
 *   density     : compact / default / relaxed — 行高さを切り替え
 *   emptyState  : データ 0 件時のカスタム表示スロット
 *   onRowClick  : 行クリックコールバック（Enter/Space キー操作可・セル内ボタンで非発火）
 *   pagination  : 制御型ページ送り（page + hasNextPage + onPageChange）
 *   rowTestId / paginationTestIds / paginationDisabled : testid・読込中の口
 *   stickyHeader / 列 stickyLeft : 見出し固定・先頭列固定
 *   fitToWidth  : 表を枠の幅に合わせて縮める（PC のみ）
 *   mobileCards : スマホ（767px 以下）はカード表示
 *   新しい props はすべて省略可。省略時の DOM・クラス名は従来と同じ。
 *
 * 使用方針:
 *   - ソート・選択・ページ送りは呼び出し側 (controlled) で管理する。
 *   - セル内に日本語ラベルを埋め込まない（columns.header / emptyState を通じて渡す）。
 *   - 水平スクロールはラッパー (.comp-table) が担当。
 */
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { ReactNode, KeyboardEvent, MouseEvent } from 'react';
import { TABLE_ICONS } from '../constants/icons-base';
import { useIsMobile } from '../hooks/useIsMobile';
import { useFitTableZoom } from '../hooks/useFitTableZoom';
import './DataTable.css';
import { Button } from "./Button";
import { CheckboxControl } from "./CheckboxControl";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

export interface DataTableColumn<T = Record<string, unknown>> {
  /** data オブジェクトのキー（renderCell が無い場合に String(row[key]) を表示） */
  key: string;
  /** ヘッダーラベル */
  header: string;
  /**
   * 列幅（CSS width 値。例: "120px", "1fr"）。
   * ellipsis 列では max-width としても使う。max-width として無効な値（例: "1fr"）のときは
   * CSS 既定（--comp-table-ellipsis-max-w 200px）になる。
   */
  width?: string;
  /** true で1行に収め、はみ出しは … にする。width があればその幅まで。文字列のセルは title に全文を付ける */
  ellipsis?: boolean;
  /** ソートボタンを表示するか */
  sortable?: boolean;
  /** 文字の寄せ（既定 left）。th と td に comp-table__cell--align-* を付ける */
  align?: 'left' | 'right' | 'center';
  /**
   * true で左に固定（stickyHeader が true のときだけ効く）。
   * 先頭の1列だけに使う（2列以上は対象外）。
   */
  stickyLeft?: boolean;
  /** カード表示（mobileCards）での並び順。小さい順。無い列は後ろに元の順で並ぶ */
  mobileOrder?: number;
  /** カード表示で隠す */
  mobileHidden?: boolean;
  /** カード表示のラベル（無ければ header） */
  mobileLabel?: string;
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
  /**
   * 行クリックコールバック。
   * - 指定時は tr が tabIndex=0 になりキーボード（Enter / Space）でも発火。
   * - セル内の button / a / input / select / textarea / label は二重発火しない。
   */
  onRowClick?: (row: T) => void;
  /** 現在のページ番号（1-indexed）。onPageChange とセットで指定する。 */
  page?: number;
  /** 次のページが存在するか */
  hasNextPage?: boolean;
  /** ページ変更コールバック。指定するとページ送りコントロールが表示される。 */
  onPageChange?: (page: number) => void;
  /** 「前へ」ボタンのラベル（省略時: "‹"） */
  prevPageLabel?: string;
  /** 「次へ」ボタンのラベル（省略時: "›"） */
  nextPageLabel?: string;
  /** ページ番号表示部に挿入する ReactNode（省略時はページ番号のみ表示） */
  pageInfo?: ReactNode;
  /** 行ごとに追加する CSS クラス名を返すファクトリ（例: pending-dedup ハイライト） */
  rowClassName?: (row: T) => string;
  /** 行（tr・カード）に付ける data-testid */
  rowTestId?: (row: T) => string;
  /** ページ送りの data-testid（前へ・次へ・件数表示） */
  paginationTestIds?: { prev: string; next: string; label: string };
  /** true のとき前へ・次へを両方 disabled にする（読込中など） */
  paginationDisabled?: boolean;
  /** 見出しを固定し、表を縦にスクロールさせる */
  stickyHeader?: boolean;
  /** 表を枠の幅に合わせて縮める（PC のみ。767px 以下では効かない） */
  fitToWidth?: boolean;
  /** スマホ（767px 以下）で表をカード表示にする。このとき stickyHeader・stickyLeft・fitToWidth は効かない */
  mobileCards?: boolean;
  /** 表の上をタブ行にくっつける（上の線と上の角丸を消す）。カード表示のときは効かない */
  attachedTop?: boolean;
}

// ──────────────────────────────────────────────────────────────────────────────
// ユーティリティ
// ──────────────────────────────────────────────────────────────────────────────

/** セル内のインタラクティブ要素か判定（行クリックの二重発火防止） */
function isInteractiveTarget(e: MouseEvent | KeyboardEvent): boolean {
  return !!(e.target as HTMLElement).closest(
    'button, a, input, select, textarea, label',
  );
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
  onRowClick,
  page = 1,
  hasNextPage = false,
  onPageChange,
  prevPageLabel = '‹',
  nextPageLabel = '›',
  pageInfo,
  rowClassName,
  rowTestId,
  paginationTestIds,
  paginationDisabled = false,
  stickyHeader = false,
  fitToWidth = false,
  mobileCards = false,
  attachedTop = false,
}: DataTableProps<T>) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const cardMode = mobileCards && isMobile;
  const useFrame = !cardMode && (stickyHeader || fitToWidth);
  const fitEnabled = fitToWidth && !cardMode;
  const frameRef = useRef<HTMLDivElement>(null);
  const fitCardRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  useFitTableZoom(fitEnabled, frameRef, fitCardRef, scrollRef, data);

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
    stickyHeader && useFrame ? 'comp-table--sticky' : '',
    attachedTop && !cardMode ? 'comp-table--attached-top' : '',
    className,
  ].filter(Boolean).join(' ');

  const showPagination = !!onPageChange;

  // 固定列（先頭の stickyLeft 列だけ）
  const stickyKey = columns.find((c) => c.stickyLeft)?.key;
  const hasSticky = stickyKey !== undefined;

  function cellCls(base: string, col: DataTableColumn<T>): string {
    return [
      base,
      col.align && col.align !== 'left' ? `comp-table__cell--align-${col.align}` : '',
      col.key === stickyKey
        ? (selectable ? 'comp-table__cell--sticky-left-after-check' : 'comp-table__cell--sticky-left')
        : '',
    ].filter(Boolean).join(' ');
  }
  const checkStickyCls = selectable && hasSticky ? ' comp-table__cell--sticky-check' : '';

  function rowCls(row: T, isSelected: boolean, clickable: boolean, base: string): string {
    return [
      base,
      isSelected ? 'comp-table__row--selected' : '',
      clickable ? 'comp-table__row--clickable' : '',
      rowClassName ? rowClassName(row) : '',
    ].filter(Boolean).join(' ');
  }

  const pagination = showPagination ? (
    <div className="comp-table__pagination">
      <Button variant="secondary" size="sm"
        type="button"
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={page <= 1 || paginationDisabled}
        aria-label={t('common.dataTable.previousPage')}
        data-testid={paginationTestIds?.prev}
      >
        {prevPageLabel}
      </Button>
      <span className="comp-table__page-info" data-testid={paginationTestIds?.label}>
        {pageInfo ?? page}
      </span>
      <Button variant="secondary" size="sm"
        type="button"
        onClick={() => onPageChange(page + 1)}
        disabled={!hasNextPage || paginationDisabled}
        aria-label={t('common.dataTable.nextPage')}
        data-testid={paginationTestIds?.next}
      >
        {nextPageLabel}
      </Button>
    </div>
  ) : null;

  // ── スマホのカード表示 ──
  if (cardMode) {
    const cardColumns = columns
      .map((col, idx) => ({ col, idx }))
      .filter(({ col }) => !col.mobileHidden)
      .sort((a, b) => {
        const ao = a.col.mobileOrder ?? Number.POSITIVE_INFINITY;
        const bo = b.col.mobileOrder ?? Number.POSITIVE_INFINITY;
        if (ao !== bo) return ao < bo ? -1 : 1;
        return a.idx - b.idx;
      })
      .map(({ col }) => col);
    return (
      <div className={['comp-table-frame', className].filter(Boolean).join(' ')} role="region" aria-label={t('common.dataTable.table')}>
        {data.length === 0 ? (
          <div className="comp-table__empty">{emptyState ?? t('common.noData')}</div>
        ) : (
          <div className="comp-table-cards" role="list">
            {data.map((row) => {
              const key = rowKey(row);
              const isSelected = selected.has(key);
              const clickable = !!onRowClick;
              return (
                <div
                  key={key}
                  role="listitem"
                  className={rowCls(row, isSelected, clickable, 'comp-table__card')}
                  data-testid={rowTestId ? rowTestId(row) : undefined}
                  tabIndex={clickable ? 0 : undefined}
                  onClick={clickable ? (e: MouseEvent<HTMLDivElement>) => {
                    if (isInteractiveTarget(e)) return;
                    onRowClick(row);
                  } : undefined}
                  onKeyDown={clickable ? (e: KeyboardEvent<HTMLDivElement>) => {
                    if (e.key !== 'Enter' && e.key !== ' ') return;
                    if (isInteractiveTarget(e)) return;
                    e.preventDefault();
                    onRowClick(row);
                  } : undefined}
                >
                  {selectable && (
                    <CheckboxControl
                      checked={isSelected}
                      onChange={() => toggleRow(key)}
                      aria-label={t('common.dataTable.selectRow', { key })}
                    />
                  )}
                  {cardColumns.map((col) => {
                    const content = col.renderCell
                      ? col.renderCell(row, key)
                      : String((row as Record<string, unknown>)[col.key] ?? '');
                    return (
                      <div key={col.key} className="comp-table__card-field">
                        <span className="comp-table__card-label">{col.mobileLabel ?? col.header}</span>
                        <span className="comp-table__card-value">{content}</span>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}
        {pagination}
      </div>
    );
  }

  const table = (
    <table className="comp-table__table">
      <thead>
        <tr className="comp-table__head-row">
          {selectable && (
            <th className={`comp-table__th comp-table__th--check${checkStickyCls}`} aria-label={t('common.dataTable.selectAll')}>
              <CheckboxControl
                checked={allSelected}
                indeterminate={someSelected}
                onChange={toggleAll}
                aria-label={t('common.dataTable.selectAllRows')}
              />
            </th>
          )}
          {columns.map((col) => (
            <th
              key={col.key}
              className={cellCls('comp-table__th', col)}
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
              {emptyState ?? t('common.noData')}
            </td>
          </tr>
        ) : (
          data.map((row) => {
            const key = rowKey(row);
            const isSelected = selected.has(key);
            const clickable = !!onRowClick;
            return (
              <tr
                key={key}
                className={rowCls(row, isSelected, clickable, 'comp-table__row')}
                data-testid={rowTestId ? rowTestId(row) : undefined}
                tabIndex={clickable ? 0 : undefined}
                onClick={clickable ? (e: MouseEvent<HTMLTableRowElement>) => {
                  if (isInteractiveTarget(e)) return;
                  onRowClick(row);
                } : undefined}
                onKeyDown={clickable ? (e: KeyboardEvent<HTMLTableRowElement>) => {
                  if (e.key !== 'Enter' && e.key !== ' ') return;
                  if (isInteractiveTarget(e)) return;
                  e.preventDefault();
                  onRowClick(row);
                } : undefined}
              >
                {selectable && (
                  <td className={`comp-table__td comp-table__td--check${checkStickyCls}`}>
                    <CheckboxControl
                      checked={isSelected}
                      onChange={() => toggleRow(key)}
                      aria-label={t('common.dataTable.selectRow', { key })}
                    />
                  </td>
                )}
                {columns.map((col) => {
                  const content = col.renderCell
                    ? col.renderCell(row, key)
                    : String((row as Record<string, unknown>)[col.key] ?? '');
                  if (!col.ellipsis) {
                    return <td key={col.key} className={cellCls('comp-table__td', col)}>{content}</td>;
                  }
                  return (
                    <td key={col.key} className={cellCls('comp-table__td comp-table__td--ellipsis', col)}>
                      <div
                        className="comp-table__cell-ellipsis"
                        style={col.width ? { maxWidth: col.width } : undefined}
                        title={typeof content === 'string' ? content : undefined}
                      >
                        {content}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })
        )}
      </tbody>
    </table>
  );

  // 今までと同じ DOM（見出し固定・縮小なし）
  if (!useFrame) {
    return (
      <div className={wrapperCls} role="region" aria-label={t('common.dataTable.table')}>
        {table}
        {pagination}
      </div>
    );
  }

  // frame > (fit card >) scroll box > table。ページ送りは縮める箱・スクロール箱の外
  const scrollBox = (
    <div ref={scrollRef} className={wrapperCls}>
      {table}
    </div>
  );
  return (
    <div ref={frameRef} className="comp-table-frame" role="region" aria-label={t('common.dataTable.table')}>
      {fitToWidth ? (
        <div ref={fitCardRef} className="comp-table-fit__card">{scrollBox}</div>
      ) : scrollBox}
      {pagination}
    </div>
  );
}
