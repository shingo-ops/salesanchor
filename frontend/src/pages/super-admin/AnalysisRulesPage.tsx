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
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import {
  AnalysisRulesSidebar,
  type AnalysisRulesSidebarKey,
} from "./components/AnalysisRulesSidebar";
import NeedsReviewTabsPanel from "./components/NeedsReviewTabsPanel";
import { ConditionsMasterPanel } from "./components/ConditionsMasterPanel";
import { UnitMasterPanel } from "./components/UnitMasterPanel";
import { UnitIgnorePhrasesPanel } from "./components/UnitIgnorePhrasesPanel";
import { RuleManagementPanel } from "./components/RuleManagementPanel";
import { AnalysisDashboardPanel } from "./components/AnalysisDashboardPanel";
import { ExtractionErrorLogPanel } from "./components/ExtractionErrorLogPanel";
import { SoldOutResultsPanel } from "./components/SoldOutResultsPanel";
import SupplierExtractionRulesPage from "./SupplierExtractionRulesPage";
import ExtractionPromptConfigTab from "./ExtractionPromptConfigTab";
import KnowledgeAliasesTab from "./KnowledgeAliasesTab";
import { isSettingsMasterKey, settingsMasterPath } from "./settings/settingsNav";
import "./AnalysisRulesPage.css";
import { SupplierQualityList } from "../../features/tcg-analysis-review/SupplierQualityList";
import { SupplierDetailView } from "../../features/tcg-analysis-review/SupplierDetailView";
import { DiagnosticsDrawer } from "../../features/tcg-analysis-review/DiagnosticsDrawer";
import type { SupplierQualitySummary } from "../../features/tcg-analysis-review/supplierQuality";
import { DistributionSettingsDrawer } from "./components/DistributionSettingsDrawer";
import { DbViewerPanel } from "./components/DbViewerPanel";
import { PipelineMapPanel } from "./components/PipelineMapPanel";
import { LineWorkflowGuidePanel } from "./components/LineWorkflowGuidePanel";
import { LoadingBlock } from "../../components/loading";

// ---------------------------------------------------------------------------
// 解析精度管理パネル（旧スタンドアロンページ（AY-2g で削除）の内容を移植）
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

// ---------------------------------------------------------------------------
// メインページ
// ---------------------------------------------------------------------------

export default function AnalysisRulesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();
  const initialSection =
    (searchParams.get("section") as AnalysisRulesSidebarKey) || "dashboard";
  const [activeSection, setActiveSection] =
    useState<AnalysisRulesSidebarKey>(initialSection);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleSectionChange = (key: string) => {
    if (key === "import") {
      navigate("/super-admin/tcg-line-import");
      return;
    }
    if (isSettingsMasterKey(key)) {
      // マスタ11件は全体設定へ移動した
      navigate(settingsMasterPath(key));
      return;
    }
    setActiveSection(key);
    setSearchParams({ section: key }, { replace: true });
  };

  // 旧 URL（?section=<マスタ>）は全体設定の同じマスタへ置き換えで転送する
  const requestedSection = searchParams.get("section");
  if (isSettingsMasterKey(requestedSection)) {
    return <Navigate to={settingsMasterPath(requestedSection)} replace />;
  }

  if (superAdminLoading) {
    return (
      <PageLayout navKey="nav.superAdminAnalysisRules">
        <LoadingBlock />
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

  const headerAction = activeSection === "dashboard" ? (
    <Button variant="ghost" size="md" onClick={() => setSettingsOpen(true)}>
      {t("distributionSettings.buttonLabel")}
    </Button>
  ) : undefined;

  return (
    <PageLayout
      navKey="nav.superAdminAnalysisRules"
      subtitleKey="analysisRules.page.subtitle"
      noScroll
      headerAction={headerAction}
    >
      <DistributionSettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
      <div className="hub-shell">
        {/* 左サブナビ */}
        <AnalysisRulesSidebar
          activeKey={activeSection}
          onChange={handleSectionChange}
        />

        {/* 右コンテンツ */}
        <div className="hub-content">
          {activeSection === "dashboard" && <AnalysisDashboardPanel onNavigate={handleSectionChange} />}
          {activeSection !== "dashboard" && (
            <div className="analysis-panel-content">
              {activeSection === "accuracy-management" && <AccuracyManagementPanel />}
              {activeSection === "needs-review" && <NeedsReviewTabsPanel />}
              {activeSection === "error-log" && <ExtractionErrorLogPanel />}
              {activeSection === "sold-out-results" && <SoldOutResultsPanel />}
              {activeSection === "conditions-master" && <ConditionsMasterPanel />}
              {activeSection === "unit-master" && (
                <>
                  <UnitMasterPanel />
                  <UnitIgnorePhrasesPanel />
                </>
              )}
              {activeSection === "rule-management" && <RuleManagementPanel />}
              {activeSection === "extraction-rules" && <SupplierExtractionRulesPage embedded />}
              {activeSection === "knowledge-aliases" && <KnowledgeAliasesTab />}
              {activeSection === "prompt-config" && <ExtractionPromptConfigTab />}
              {activeSection === "pipeline-map" && <PipelineMapPanel />}
              {activeSection === "line-workflow-guide" && (
                <LineWorkflowGuidePanel onNavigate={handleSectionChange} />
              )}
              {activeSection === "db-viewer" && <DbViewerPanel />}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
