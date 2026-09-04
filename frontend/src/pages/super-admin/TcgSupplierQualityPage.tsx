/**
 * /super-admin/tcg-supplier-quality — 仕入元品質サマリー
 *
 * PARITY-03 第2段階:
 *   GAS api_getSupplierQualitySummaries → GET /api/v1/tcg/supplier-quality-summaries
 *   GAS api_getSupplierSource           → GET /api/v1/tcg/suppliers/{id}/source
 *   is_super_admin=false なら 403 メッセージを表示
 *
 * Phase 2 制限:
 *   - ProductMasterDrawer（修正ドロワー）は Phase 3 以降
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { SupplierQualityList } from "../../features/tcg-analysis-review/SupplierQualityList";
import { SupplierDetailView } from "../../features/tcg-analysis-review/SupplierDetailView";
import { DiagnosticsDrawer } from "../../features/tcg-analysis-review/DiagnosticsDrawer";
import type { SupplierQualitySummary } from "../../features/tcg-analysis-review/supplierQuality";

export default function TcgSupplierQualityPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();
  const [selected, setSelected] = useState<SupplierQualitySummary | null>(null);
  const [diagOpen, setDiagOpen] = useState(false);

  if (superAdminLoading) {
    return <PageLayout navKey="nav.superAdminTcgSupplierQuality">{t("common.loading")}</PageLayout>;
  }
  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminTcgSupplierQuality">
        <p style={{ color: "var(--color-error)" }}>{t("superAdmin.supplierQuality.superAdminOnly")}</p>
      </PageLayout>
    );
  }

  const headerAction = (
    <Button variant="ghost" size="md" onClick={() => setDiagOpen(true)}>
      {t("superAdmin.diagnostics.buttonLabel")}
    </Button>
  );

  return (
    <PageLayout navKey="nav.superAdminTcgSupplierQuality" headerAction={headerAction}>
      {selected ? (
        <SupplierDetailView
          supplierId={selected.supplierId}
          supplierName={selected.supplierName}
          onBack={() => setSelected(null)}
        />
      ) : (
        <SupplierQualityList onSelectSupplier={setSelected} />
      )}
      <DiagnosticsDrawer open={diagOpen} onClose={() => setDiagOpen(false)} />
    </PageLayout>
  );
}
