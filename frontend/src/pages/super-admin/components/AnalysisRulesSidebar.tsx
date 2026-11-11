/**
 * AnalysisRulesSidebar — 解析管理ページ左サイドメニュー
 *
 * hub-shell.css の hub-subnav / hub-subnav-item / hub-subnav-title / hub-subnav-section を使用。
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。独自CSS禁止。
 */
import { useTranslation } from "react-i18next";

export type AnalysisRulesSidebarKey =
  | "dashboard"
  | "import"
  | "accuracy-management"
  | "needs-review"
  | "error-log"
  | "sold-out-results"
  | "rule-management"
  | "extraction-rules"
  | "knowledge-aliases"
  // 全体設定へ移動済み。ダッシュボード・手順ガイドの中の key の文字だけが今も使うので型には残す（受け手が転送する）
  | "product-master"
  | "supplier-master"
  | "conditions-master"
  | "unit-master"
  | "prompt-config"
  | "pipeline-map"
  | "line-workflow-guide"
  | "db-viewer";

interface Props {
  activeKey: AnalysisRulesSidebarKey;
  onChange: (key: AnalysisRulesSidebarKey) => void;
  needsReviewCount?: number;
}

export function AnalysisRulesSidebar({ activeKey, onChange, needsReviewCount }: Props) {
  const { t } = useTranslation();

  function navItem(key: AnalysisRulesSidebarKey, label: string, badge?: number) {
    const isActive = activeKey === key;
    return (
      <button
        key={key}
        type="button"
        className={`hub-subnav-item${isActive ? " active" : ""}`}
        onClick={() => onChange(key)}
        aria-pressed={isActive}
        data-testid={`analysis-subnav-${key}`}
      >
        {label}
        {badge !== undefined && badge > 0 && (
          <span
            style={{
              marginLeft: "var(--space-2)",
              fontSize: "var(--font-xs)",
              color: "var(--text-muted)",
            }}
          >
            {t("analysisRules.needsReview.count", { count: badge })}
          </span>
        )}
      </button>
    );
  }

  return (
    <nav
      className="hub-subnav"
      aria-label={t("analysisRules.page.title")}
    >
      {/* 解析状況グループ */}
      <div className="hub-subnav-section">
        <span className="hub-subnav-title">
          {t("analysisRules.sidebar.groupAnalysisStatus")}
        </span>
        {navItem("dashboard", t("analysisRules.sidebar.dashboard"))}
        {navItem("import", t("analysisRules.sidebar.import"))}
        {navItem("accuracy-management", t("analysisRules.sidebar.accuracyManagement"))}
        {navItem("needs-review", t("analysisRules.sidebar.needsReview"), needsReviewCount)}
        {navItem("error-log", t("analysisRules.sidebar.errorLog"))}
        {navItem("sold-out-results", t("analysisRules.sidebar.soldOutResults"))}
      </div>

      {/* ルール管理グループ */}
      <div className="hub-subnav-section">
        <span className="hub-subnav-title">
          {t("analysisRules.sidebar.groupRuleManagement")}
        </span>
        {navItem("rule-management", t("analysisRules.sidebar.ruleManagement"))}
        {navItem("extraction-rules", t("analysisRules.sidebar.extractionRules"))}
        {navItem("knowledge-aliases", t("analysisRules.sidebar.knowledgeAliases"))}
        {navItem("prompt-config", t("analysisRules.sidebar.promptConfig"))}
        {navItem("conditions-master", t("analysisRules.sidebar.conditionsMaster"))}
        {navItem("unit-master", t("analysisRules.sidebar.unitMaster"))}
      </div>

      {/* システムグループ */}
      <div className="hub-subnav-section">
        <span className="hub-subnav-title">
          {t("analysisRules.sidebar.groupSystem")}
        </span>
        {navItem("pipeline-map", t("analysisRules.sidebar.pipelineMap"))}
        {navItem("line-workflow-guide", t("analysisRules.sidebar.lineWorkflowGuide"))}
        {navItem("db-viewer", t("analysisRules.sidebar.dbViewer"))}
      </div>
    </nav>
  );
}
