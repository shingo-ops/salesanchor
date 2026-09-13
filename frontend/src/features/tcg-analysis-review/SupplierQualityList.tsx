import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../lib/api';
import { DataList } from './components/DataList';
import { supplierQualityColumns, type SupplierQualitySummary } from './supplierQuality';

interface ApiSummary {
  supplier_id: string;
  supplier_name: string;
  analysis_count: number;
  needs_review_count: number;
  product_id_unresolved_count: number;
  unit_unresolved_count: number;
  condition_fallback_count: number | null;
}

interface ApiResponse {
  summaries: ApiSummary[];
}

function mapSummary(raw: ApiSummary): SupplierQualitySummary {
  return {
    supplierId: raw.supplier_id,
    supplierName: raw.supplier_name,
    analysisCount: raw.analysis_count,
    needsReviewCount: raw.needs_review_count,
    productIdUnresolvedCount: raw.product_id_unresolved_count,
    unitUnresolvedCount: raw.unit_unresolved_count,
    conditionFallbackCount: raw.condition_fallback_count,
  };
}

export function SupplierQualityList({ onSelectSupplier }: { onSelectSupplier: (summary: SupplierQualitySummary) => void }) {
  const { t } = useTranslation();
  const [summaries, setSummaries] = useState<SupplierQualitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<ApiResponse>('/tcg/supplier-quality-summaries')
      .then((res) => { setSummaries(res.summaries.map(mapSummary)); })
      .catch((e: unknown) => { setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { setLoading(false); });
  }, []);

  if (loading) return <p>{t("common.loading")}</p>;
  if (error) return <p style={{ color: 'var(--color-error)' }}>{error}</p>;

  return (
    <DataList
      columns={supplierQualityColumns(t)}
      rows={summaries}
      getRowKey={(row) => row.supplierId}
      onRowSelect={onSelectSupplier}
      renderCell={(row, column) => {
        switch (column.id) {
          case 'SUPPLIER_NAME':               return row.supplierName;
          case 'ANALYSIS_COUNT':              return row.analysisCount;
          case 'NEEDS_REVIEW_COUNT':          return row.needsReviewCount;
          case 'PRODUCT_ID_UNRESOLVED_COUNT': return row.productIdUnresolvedCount;
          case 'UNIT_UNRESOLVED_COUNT':       return row.unitUnresolvedCount;
          case 'CONDITION_FALLBACK_COUNT':
            return row.conditionFallbackCount !== null ? row.conditionFallbackCount : t("superAdmin.supplierQuality.conditionPending");
          default: return null;
        }
      }}
    />
  );
}
