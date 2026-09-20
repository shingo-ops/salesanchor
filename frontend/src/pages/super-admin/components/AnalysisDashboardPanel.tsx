/**
 * AnalysisDashboardPanel — 解析ダッシュボード（UX改善版）
 *
 * 認知科学ベースのレイアウト:
 * 1. ボトルネックヒーロー（最悪指標を自動検出・最上部に表示）
 * 2. 信号灯KPIカード（緑/黄/赤のボーダーで健全性を即座に判断）
 * 3. CTAボタン（次のアクションへ直接遷移）
 * 4. 詳細セクション（理由内訳・エンジン・エラー）
 *
 * API: GET /api/v1/tcg/analysis-dashboard/pipeline-summary
 * ADR-027: 全UI文字列は t("key") 経由
 * ADR-067: 色・サイズはデザイントークンのみ
 * ADR-144: Card / Badge / DataTable 金型のみ使用
 *
 * NOTE: /tcg/analysis-dashboard/trend は削除済み（backend から除去）。
 *       トレンドグラフは PR #3611 でバックエンドエンドポイント削除に伴い除去。
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { Card } from "../../../components/Card";
import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import { DashboardIcons } from "../../../constants/icons";
import type { AnalysisRulesSidebarKey } from "./AnalysisRulesSidebar";
import "./AnalysisDashboardPanel.css";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

interface ReviewReason {
  reason: string;
  count: number;
}

interface RecentError {
  id: string;
  error_message: string | null;
  created_at: string | null;
  prompt_version: string | null;
}

interface ExtractionSummary {
  total: number;
  by_status: {
    done: number;
    error: number;
    pending: number;
    running: number;
    empty: number;
  };
  stale_running_count: number;
  error_rate: number;
}

interface AnalysisSummary {
  total: number;
  pid_resolved_count: number;
  pid_resolved_rate: number;
  unit_resolved_count: number;
  unit_resolved_rate: number;
  needs_review_count: number;
  needs_review_rate: number;
  missing_count: number;
}

interface EngineSummary {
  current_model: string | null;
  current_prompt_version: string | null;
  current_engine_version: string | null;
}

interface PipelineSummary {
  extraction: ExtractionSummary;
  analysis: AnalysisSummary;
  review_reasons: ReviewReason[];
  engine: EngineSummary;
  recent_errors: RecentError[];
}

// ──────────────────────────────────────────────────────────────────────────────
// 信号灯ヘルパー
// ──────────────────────────────────────────────────────────────────────────────

type SignalLevel = "success" | "warning" | "danger";

function getSignalLevel(rate: number): SignalLevel {
  if (rate >= 0.8) return "success";
  if (rate >= 0.6) return "warning";
  return "danger";
}

function getSignalClass(level: SignalLevel): string {
  return `analysis-dashboard-signal--${level}`;
}

// ──────────────────────────────────────────────────────────────────────────────
// ボトルネック検出用の指標定義
// ──────────────────────────────────────────────────────────────────────────────

interface MetricDef {
  labelKey: string;
  rate: number;
  displayRate: number; // 表示値（needsReviewは反転しない生値を表示）
  level: SignalLevel;
  ctaKey: AnalysisRulesSidebarKey;
  ctaLabelKey: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface AnalysisDashboardPanelProps {
  onNavigate?: (key: AnalysisRulesSidebarKey) => void;
}

// ──────────────────────────────────────────────────────────────────────────────
// コンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function AnalysisDashboardPanel({ onNavigate }: AnalysisDashboardPanelProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<PipelineSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.get<PipelineSummary>("/tcg/analysis-dashboard/pipeline-summary")
      .then((summaryRes) => {
        setData(summaryRes);
      })
      .catch(() => {
        setError(t("analysisRules.dashboard.fetchError"));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [t]);

  if (loading) {
    return (
      <div className="analysis-dashboard">
        <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.loading")}</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="analysis-dashboard">
        <p className="analysis-dashboard-error">
          {error ?? t("analysisRules.dashboard.fetchError")}
        </p>
      </div>
    );
  }

  // 算出値（rate は 0〜1 の小数）
  const extractionSuccessRate =
    data.extraction.total > 0
      ? data.extraction.by_status.done / data.extraction.total
      : 0;
  const pidRate = data.analysis.pid_resolved_rate;
  const unitRate = data.analysis.unit_resolved_rate;
  const needsReviewRate = data.analysis.needs_review_rate;
  // needsReview: 少ないほど良い → 信号判定は「1 - rate」で健全性に換算
  const needsReviewHealthRate = 1 - needsReviewRate;

  // ボトルネック検出用指標リスト
  const metrics: MetricDef[] = [
    {
      labelKey: "analysisRules.dashboard.extractionSuccessRate",
      rate: extractionSuccessRate,
      displayRate: extractionSuccessRate,
      level: getSignalLevel(extractionSuccessRate),
      ctaKey: "accuracy-management",
      ctaLabelKey: "analysisRules.dashboard.ctaAccuracy",
    },
    {
      labelKey: "analysisRules.dashboard.pidResolutionRate",
      rate: pidRate,
      displayRate: pidRate,
      level: getSignalLevel(pidRate),
      ctaKey: "product-master",
      ctaLabelKey: "analysisRules.dashboard.ctaProductMaster",
    },
    {
      labelKey: "analysisRules.dashboard.unitResolutionRate",
      rate: unitRate,
      displayRate: unitRate,
      level: getSignalLevel(unitRate),
      ctaKey: "unit-master",
      ctaLabelKey: "analysisRules.dashboard.ctaUnitMaster",
    },
    {
      labelKey: "analysisRules.dashboard.needsReviewRate",
      rate: needsReviewHealthRate,
      displayRate: needsReviewRate, // 表示は生の「要確認率」
      level: getSignalLevel(needsReviewHealthRate),
      ctaKey: "needs-review",
      ctaLabelKey: "analysisRules.dashboard.ctaNeedsReview",
    },
  ];

  // 最悪指標 = ボトルネック
  const bottleneck = metrics.reduce((worst, m) =>
    m.rate < worst.rate ? m : worst
  );

  const hasEngineInfo =
    data.engine.current_model != null ||
    data.engine.current_prompt_version != null ||
    data.engine.current_engine_version != null;

  const errorColumns: DataTableColumn<RecentError>[] = [
    {
      key: "error_message",
      header: t("analysisRules.dashboard.errorMessage"),
    },
    {
      key: "created_at",
      header: t("analysisRules.dashboard.errorDate"),
      width: "180px",
    },
  ];

  const handleCta = (key: AnalysisRulesSidebarKey) => {
    if (onNavigate) {
      onNavigate(key);
    }
  };

  const ArrowRightIcon = DashboardIcons.arrowRight;

  return (
    <div className="analysis-dashboard">

      {/* 1. ボトルネックヒーロー（最悪指標のみ表示・成功時は非表示） */}
      {bottleneck.level !== "success" && (
        <div className={`analysis-dashboard-hero ${getSignalClass(bottleneck.level)}`}>
          <div className="analysis-dashboard-hero-content">
            <Badge variant={bottleneck.level === "danger" ? "danger" : "warning"} dot>
              {t("analysisRules.dashboard.bottleneckLabel")}
            </Badge>
            <div className="analysis-dashboard-hero-metric">
              <span className="analysis-dashboard-hero-name">
                {t(bottleneck.labelKey)}
              </span>
              <span className="analysis-dashboard-hero-value">
                {(bottleneck.displayRate * 100).toFixed(1)}%
              </span>
            </div>
            <p className="analysis-dashboard-hero-desc">
              {t("analysisRules.dashboard.bottleneckDesc")}
            </p>
            <button
              type="button"
              className="analysis-dashboard-cta-btn analysis-dashboard-cta-btn--primary"
              onClick={() => handleCta(bottleneck.ctaKey)}
            >
              {t(bottleneck.ctaLabelKey)}
              <ArrowRightIcon size={16} />
            </button>
          </div>
        </div>
      )}

      {/* 2. 信号灯KPIカード */}
      <div className="analysis-dashboard-metrics">
        {/* 総ジョブ数（中立・信号なし） */}
        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.totalJobs")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {data.extraction.total.toLocaleString()}
            <span className="analysis-dashboard-metric-unit">
              {t("analysisRules.dashboard.jobs")}
            </span>
          </div>
        </Card>

        {metrics.map((m) => (
          <Card
            key={m.labelKey}
            variant="metric"
            density="compact"
            className={getSignalClass(m.level)}
          >
            <div className="analysis-dashboard-metric-label">
              {t(m.labelKey)}
            </div>
            <div className="analysis-dashboard-metric-value">
              {(m.displayRate * 100).toFixed(1)}%
            </div>
          </Card>
        ))}
      </div>

      {/* アラートバッジ */}
      <div className="analysis-dashboard-alerts">
        {data.extraction.stale_running_count > 0 && (
          <div className="analysis-dashboard-alert-item">
            <Badge variant="danger" dot>
              {t("analysisRules.dashboard.staleRunning")}{" "}
              {data.extraction.stale_running_count}
              {t("analysisRules.dashboard.items")}
            </Badge>
          </div>
        )}
        {data.analysis.missing_count > 0 && (
          <div className="analysis-dashboard-alert-item">
            <Badge variant="warning" dot>
              {t("analysisRules.dashboard.analysisMissing")}{" "}
              {data.analysis.missing_count}
              {t("analysisRules.dashboard.items")}
            </Badge>
          </div>
        )}
        <div className="analysis-dashboard-alert-item">
          <Badge variant="info" dot>
            {t("analysisRules.dashboard.pending")}{" "}
            {data.extraction.by_status.pending}
            {t("analysisRules.dashboard.items")}
          </Badge>
        </div>
      </div>

      {/* 3. CTAボタン */}
      <div className="analysis-dashboard-ctas">
        <button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => handleCta("needs-review")}
        >
          {t("analysisRules.dashboard.ctaNeedsReview")}
          <span className="analysis-dashboard-cta-count">
            {data.analysis.needs_review_count.toLocaleString()}
            {t("analysisRules.dashboard.items")}
          </span>
          <ArrowRightIcon size={16} />
        </button>
        <button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => handleCta("product-master")}
        >
          {t("analysisRules.dashboard.ctaProductMaster")}
          <ArrowRightIcon size={16} />
        </button>
        <button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => handleCta("accuracy-management")}
        >
          {t("analysisRules.dashboard.ctaAccuracy")}
          <ArrowRightIcon size={16} />
        </button>
      </div>

      {/* 4. 詳細セクション（理由内訳・エンジン情報・直近エラー） */}
      <div className="analysis-dashboard-grid">
        {/* 要確認の理由内訳 */}
        <Card variant="container" density="compact">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.reviewReasons")}
          </div>
          {data.review_reasons.length === 0 ? (
            <p className="analysis-dashboard-empty">
              {t("analysisRules.dashboard.noData")}
            </p>
          ) : (
            <ul className="analysis-dashboard-reason-list">
              {data.review_reasons.map((item) => (
                <li key={item.reason} className="analysis-dashboard-reason-item">
                  <span>{item.reason}</span>
                  <span className="analysis-dashboard-reason-count">
                    {item.count.toLocaleString()}
                    {t("analysisRules.dashboard.items")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* エンジン情報 */}
        <Card variant="container" density="compact">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.engineInfo")}
          </div>
          {!hasEngineInfo ? (
            <p className="analysis-dashboard-empty">
              {t("analysisRules.dashboard.noData")}
            </p>
          ) : (
            <div className="analysis-dashboard-engine-list">
              <div className="analysis-dashboard-engine-item">
                <span className="analysis-dashboard-engine-label">
                  {t("analysisRules.dashboard.currentModel")}
                </span>
                <span className="analysis-dashboard-engine-value">
                  {data.engine.current_model}
                </span>
              </div>
              <div className="analysis-dashboard-engine-item">
                <span className="analysis-dashboard-engine-label">
                  {t("analysisRules.dashboard.promptVersion")}
                </span>
                <span className="analysis-dashboard-engine-value">
                  {data.engine.current_prompt_version}
                </span>
              </div>
              <div className="analysis-dashboard-engine-item">
                <span className="analysis-dashboard-engine-label">
                  {t("analysisRules.dashboard.engineVersion")}
                </span>
                <span className="analysis-dashboard-engine-value">
                  {data.engine.current_engine_version}
                </span>
              </div>
            </div>
          )}
        </Card>

        {/* 直近のエラー */}
        <Card variant="container" density="compact">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.recentErrors")}
          </div>
          {data.recent_errors.length === 0 ? (
            <p className="analysis-dashboard-empty">
              {t("analysisRules.dashboard.noErrors")}
            </p>
          ) : (
            <DataTable<RecentError>
              columns={errorColumns}
              data={data.recent_errors}
              rowKey={(row) => row.id}
              density="compact"
              emptyState={t("analysisRules.dashboard.noErrors")}
            />
          )}
        </Card>
      </div>
    </div>
  );
}
