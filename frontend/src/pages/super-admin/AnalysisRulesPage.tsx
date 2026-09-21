/**
 * AnalysisRulesPage — 解析管理ページ（/super-admin/analysis-rules）
 *
 * レイアウト: hub-shell（左200px固定サブナビ＋右コンテンツ）
 * 左: AnalysisRulesSidebar（6項目: 解析精度管理、要確認、完売ルール、日付ルール、商品マスタ、仕入元マスタ）
 * 右: 選択に応じたパネル
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: hub-shell.css の金型クラスのみ使用。
 * 設計§5 C90 準拠。
 * 2026-09-19: マスタ管理パネル（商品マスタ・仕入元マスタ）を追加。
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import {
  AnalysisRulesSidebar,
  type AnalysisRulesSidebarKey,
} from "./components/AnalysisRulesSidebar";
import { ProductMasterPanel } from "./components/ProductMasterPanel";
import { ProductCategoriesMasterPanel } from "./components/ProductCategoriesMasterPanel";
import { ProductKindsMasterPanel } from "./components/ProductKindsMasterPanel";
import { StatusMasterPanel } from "./components/StatusMasterPanel";
import { SupplierMasterPanel } from "./components/SupplierMasterPanel";
import { ConditionsMasterPanel } from "./components/ConditionsMasterPanel";
import { UnitMasterPanel } from "./components/UnitMasterPanel";
import { NoteMasterPanel } from "./components/NoteMasterPanel";
import { AnalysisDashboardPanel } from "./components/AnalysisDashboardPanel";
import "./AnalysisRulesPage.css";
import { SupplierQualityList } from "../../features/tcg-analysis-review/SupplierQualityList";
import { SupplierDetailView } from "../../features/tcg-analysis-review/SupplierDetailView";
import { DiagnosticsDrawer } from "../../features/tcg-analysis-review/DiagnosticsDrawer";
import type { SupplierQualitySummary } from "../../features/tcg-analysis-review/supplierQuality";

// ---------------------------------------------------------------------------
// 解析精度管理パネル（TcgSupplierQualityPage の内容を移植）
// ---------------------------------------------------------------------------

function AccuracyManagementPanel() {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<SupplierQualitySummary | null>(null);
  const [diagOpen, setDiagOpen] = useState(false);

  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          padding: "var(--space-3) var(--space-4)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <Button variant="ghost" size="md" onClick={() => setDiagOpen(true)}>
          {t("superAdmin.diagnostics.buttonLabel")}
        </Button>
      </div>
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
    </>
  );
}

function NeedsReviewPanel() {
  const { t } = useTranslation();
  return (
    <div
      style={{
        padding: "var(--space-6)",
        color: "var(--text-muted)",
        fontSize: "var(--font-sm)",
      }}
    >
      <h3
        style={{
          margin: "0 0 var(--space-2)",
          fontSize: "var(--font-lg)",
          fontWeight: "var(--font-weight-bold)",
          color: "var(--text-primary)",
        }}
      >
        {t("analysisRules.needsReview.title")}
      </h3>
      <p>{t("analysisRules.needsReview.comingSoon")}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// メインページ
// ---------------------------------------------------------------------------

export default function AnalysisRulesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();
  const [activeSection, setActiveSection] = useState<AnalysisRulesSidebarKey>("dashboard");

  const handleSectionChange = (key: AnalysisRulesSidebarKey) => {
    if (key === "import") {
      navigate("/super-admin/tcg-line-import");
      return;
    }
    setActiveSection(key);
  };

  if (superAdminLoading) {
    return (
      <PageLayout navKey="nav.superAdminAnalysisRules">
        <p style={{ padding: "var(--space-4)" }}>{t("common.loading")}</p>
      </PageLayout>
    );
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminAnalysisRules">
        <p style={{ padding: "var(--space-4)", color: "var(--color-error)" }}>
          {t("superAdmin.supplierQuality.superAdminOnly")}
        </p>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      navKey="nav.superAdminAnalysisRules"
      subtitleKey="analysisRules.page.subtitle"
      noScroll
    >
      <div className="hub-shell">
        {/* 左サブナビ */}
        <AnalysisRulesSidebar
          activeKey={activeSection}
          onChange={handleSectionChange}
        />

        {/* 右コンテンツ */}
        <div className="hub-content">
          {activeSection === "dashboard" && <AnalysisDashboardPanel onNavigate={setActiveSection} />}
          {activeSection !== "dashboard" && (
            <div className="analysis-panel-content">
              {activeSection === "accuracy-management" && <AccuracyManagementPanel />}
              {activeSection === "needs-review" && <NeedsReviewPanel />}
              {activeSection === "product-master" && <ProductMasterPanel />}
              {activeSection === "product-categories-master" && <ProductCategoriesMasterPanel />}
              {activeSection === "product-kinds-master" && <ProductKindsMasterPanel />}
              {activeSection === "status-master" && <StatusMasterPanel />}
              {activeSection === "supplier-master" && <SupplierMasterPanel />}
              {activeSection === "conditions-master" && <ConditionsMasterPanel />}
              {activeSection === "unit-master" && <UnitMasterPanel />}
              {activeSection === "note-master" && <NoteMasterPanel />}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
