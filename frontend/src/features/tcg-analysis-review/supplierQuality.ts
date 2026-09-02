// SupplierQualitySummary — Supplier Quality domain SSOT
//
// Predicate basis (from Phase 1.6 evidence sqr01_phase1.6_evidence.md):
//   analysisCount:              Shadow Items count per SP_ID
//   needsReviewCount:           analysisReviewHasCurrentNeedsReview_ (ShadowReviewV2.js:98)
//   productIdUnresolvedCount:   pid_resolved delegate (ShadowReviewV2.js:92)
//   unitUnresolvedCount:        unit_resolved delegate (ShadowReviewV2.js:93)
//   conditionFallbackCount:     Q8=実測不能 — null（集計準備中）
//                               condition_basis の完全一致文字列が既存 clasp 関数で
//                               実測不能のため未実装。別タスクで確定後に number に変更する。
//
// Field NOT included (Phase 1.6 Gate G1 decisions):
//   extractionCount — omitted: Q6=抽出ロスは実在するが落ちた件数を取り出す既存手段がない

import type { TFunction } from 'i18next';
import type { DataListColumn } from './components/DataList';

export type SupplierQualitySummary = {
  supplierId: string;
  supplierName: string;
  analysisCount: number;
  needsReviewCount: number;
  productIdUnresolvedCount: number;
  unitUnresolvedCount: number;
  conditionFallbackCount: number | null; // null = 集計準備中（Q8 実測不能）
};

export type SupplierQualityColumnId =
  | 'SUPPLIER_NAME'
  | 'ANALYSIS_COUNT'
  | 'NEEDS_REVIEW_COUNT'
  | 'PRODUCT_ID_UNRESOLVED_COUNT'
  | 'UNIT_UNRESOLVED_COUNT'
  | 'CONDITION_FALLBACK_COUNT';

export function supplierQualityColumns(t: TFunction): Array<DataListColumn & { id: SupplierQualityColumnId }> {
  return [
    { id: 'SUPPLIER_NAME',               label: t("superAdmin.supplierQuality.columns.supplierName"),               minWidth: '12rem', visible: true },
    { id: 'ANALYSIS_COUNT',              label: t("superAdmin.supplierQuality.columns.analysisCount"),              minWidth: '5rem',  visible: true },
    { id: 'NEEDS_REVIEW_COUNT',          label: t("superAdmin.supplierQuality.columns.needsReviewCount"),           minWidth: '5rem',  visible: true },
    { id: 'PRODUCT_ID_UNRESOLVED_COUNT', label: t("superAdmin.supplierQuality.columns.productIdUnresolvedCount"),   minWidth: '8rem',  visible: true },
    { id: 'UNIT_UNRESOLVED_COUNT',       label: t("superAdmin.supplierQuality.columns.unitUnresolvedCount"),        minWidth: '7rem',  visible: true },
    { id: 'CONDITION_FALLBACK_COUNT',    label: t("superAdmin.supplierQuality.columns.conditionFallbackCount"),     minWidth: '9rem',  visible: true },
  ];
}
