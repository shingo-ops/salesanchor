import React, { useMemo } from 'react';
import { DataList } from './components/DataList';
import { StatusBadge } from './components/StatusBadge';
import type { AnalysisReviewItem } from './ItemComparison';
import { REVIEW_LIST_COLUMNS, type ReviewListColumnId } from './reviewListColumns';
import { buildReviewListRow } from './reviewListViewModel';

export function ReviewListPanel({ items, notes, onSelect }: { items: AnalysisReviewItem[]; notes: Record<string, string>; onSelect: (id: string) => void }) {
  const rows = useMemo(() => items.map((item) => buildReviewListRow(item, notes[item.extraction_item_id] || '')), [items, notes]);
  return <section aria-label="レビュー一覧"><DataList columns={REVIEW_LIST_COLUMNS} rows={rows} getRowKey={(row) => row.extraction_item_id} onRowSelect={(row) => onSelect(row.extraction_item_id)} renderCell={(row, column) => column.id === 'REVIEW_STATUS' ? <span className="inline-badges">{row.issueBadges.map((badge) => <StatusBadge key={badge.id} label={badge.label} tone={badge.tone} />)}</span> : row.values[column.id as Exclude<ReviewListColumnId, 'REVIEW_STATUS'>]} />{rows.length === 0 && <p className="empty">条件に一致する解析結果はありません。</p>}</section>;
}
