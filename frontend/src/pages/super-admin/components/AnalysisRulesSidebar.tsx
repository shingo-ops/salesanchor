/**
 * AnalysisRulesSidebar — 解析管理ページ左サイドメニュー
 *
 * hub-shell.css の hub-subnav / hub-subnav-item / hub-subnav-title / hub-subnav-section を使用。
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。独自CSS禁止。
 */
import { useTranslation } from "react-i18next";

export type AnalysisRulesSidebarKey =
  | "import"
  | "accuracy-management"
  | "needs-review"
  | "sold-out"
  | "date-rule"
  | "product-master"
  | "supplier-master"
  | "conditions-master";

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
        {navItem("import", t("analysisRules.sidebar.import"))}
        {navItem("accuracy-management", t("analysisRules.sidebar.accuracyManagement"))}
        {navItem("needs-review", t("analysisRules.sidebar.needsReview"), needsReviewCount)}
      </div>

      {/* ルール管理グループ */}
      <div className="hub-subnav-section">
        <span className="hub-subnav-title">
          {t("analysisRules.sidebar.groupRuleManagement")}
        </span>
        {navItem("sold-out", t("analysisRules.sidebar.soldOut"))}
        {navItem("date-rule", t("analysisRules.sidebar.dateRule"))}
      </div>

      {/* マスタ管理グループ */}
      <div className="hub-subnav-section">
        <span className="hub-subnav-title">
          {t("analysisRules.sidebar.groupMasterManagement")}
        </span>
        {navItem("product-master", t("analysisRules.sidebar.productMaster"))}
        {navItem("supplier-master", t("analysisRules.sidebar.supplierMaster"))}
        {navItem("conditions-master", t("analysisRules.sidebar.conditionsMaster"))}
      </div>
    </nav>
  );
}
