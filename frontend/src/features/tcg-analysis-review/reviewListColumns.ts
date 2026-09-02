import type { DataListColumn } from './components/DataList';

export type ReviewListColumnId = 'PROVIDER' | 'PRODUCT_NAME' | 'PRODUCT_ID' | 'QUANTITY' | 'PRICE' | 'UNIT' | 'CONDITION' | 'MEMO' | 'REVIEW_STATUS';

export const REVIEW_LIST_COLUMNS: Array<DataListColumn & { id: ReviewListColumnId; renderType: 'text' | 'memo-preview' | 'issue-badges' }> = [
  { id: 'PROVIDER', label: '仕入元', minWidth: '10rem', visible: true, renderType: 'text' },
  { id: 'PRODUCT_NAME', label: '商品名', minWidth: '18rem', visible: true, renderType: 'text' },
  { id: 'PRODUCT_ID', label: '商品ID', minWidth: '9rem', visible: true, renderType: 'text' },
  { id: 'QUANTITY', label: '数量', minWidth: '5rem', visible: true, renderType: 'text' },
  { id: 'PRICE', label: '単価', minWidth: '7rem', visible: true, renderType: 'text' },
  { id: 'UNIT', label: '単位', minWidth: '7rem', visible: true, renderType: 'text' },
  { id: 'CONDITION', label: '状態', minWidth: '7rem', visible: true, renderType: 'text' },
  { id: 'MEMO', label: 'メモ', minWidth: '12rem', visible: true, renderType: 'memo-preview' },
  { id: 'REVIEW_STATUS', label: '判定状態', minWidth: '12rem', visible: true, renderType: 'issue-badges' }
];
