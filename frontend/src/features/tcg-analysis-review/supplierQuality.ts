// SupplierQualitySummary — Supplier Quality domain SSOT
//
// Predicate basis (from Phase 1.6 evidence sqr01_phase1.6_evidence.md):
//   analysisCount:              Shadow Items count per SP_ID
//   needsReviewCount:           analysisReviewHasCurrentNeedsReview_ (ShadowReviewV2.js:98)
//   productIdUnresolvedCount:   pid_resolved delegate (ShadowReviewV2.js:92)
//   unitUnresolvedCount:        unit_resolved delegate (ShadowReviewV2.js:93)
//   conditionFallbackCount:     condition_basis 末尾一致で集計（BE: tcg_supplier_quality_svc.py）
//   conditionGiveUpCount:       うち完全お手上げ（R4:単位既定:単位不明）
//   conditionManualReviewedCount: 人が確認済み（MANUAL_CONDITION_REVIEW）
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
  conditionFallbackCount: number | null; // null = 集計準備中（旧 API 互換）
  conditionGiveUpCount: number | null;
  conditionManualReviewedCount: number | null;
};

export type SupplierQualityColumnId =
  | 'SUPPLIER_NAME'
  | 'ANALYSIS_COUNT'
  | 'NEEDS_REVIEW_COUNT'
  | 'PRODUCT_ID_UNRESOLVED_COUNT'
  | 'UNIT_UNRESOLVED_COUNT'
  | 'CONDITION_FALLBACK_COUNT'
  | 'CONDITION_GIVE_UP_COUNT'
  | 'CONDITION_MANUAL_REVIEWED_COUNT';

export function supplierQualityColumns(t: TFunction): Array<DataListColumn & { id: SupplierQualityColumnId }> {
  return [
    { id: 'SUPPLIER_NAME',               label: t("superAdmin.supplierQuality.columns.supplierName"),               minWidth: '12rem', visible: true },
    { id: 'ANALYSIS_COUNT',              label: t("superAdmin.supplierQuality.columns.analysisCount"),              minWidth: '5rem',  visible: true },
    { id: 'NEEDS_REVIEW_COUNT',          label: t("superAdmin.supplierQuality.columns.needsReviewCount"),           minWidth: '5rem',  visible: true },
    { id: 'PRODUCT_ID_UNRESOLVED_COUNT', label: t("superAdmin.supplierQuality.columns.productIdUnresolvedCount"),   minWidth: '8rem',  visible: true },
    { id: 'UNIT_UNRESOLVED_COUNT',       label: t("superAdmin.supplierQuality.columns.unitUnresolvedCount"),        minWidth: '7rem',  visible: true },
    { id: 'CONDITION_FALLBACK_COUNT',    label: t("superAdmin.supplierQuality.columns.conditionFallbackCount"),     minWidth: '9rem',  visible: true },
    { id: 'CONDITION_GIVE_UP_COUNT',          label: t("superAdmin.supplierQuality.columns.conditionGiveUpCount"),          minWidth: '9rem',  visible: true },
    { id: 'CONDITION_MANUAL_REVIEWED_COUNT',  label: t("superAdmin.supplierQuality.columns.conditionManualReviewedCount"),  minWidth: '9rem',  visible: true },
  ];
}
