/**
 * AnalysisDashboardPanel — 解析ダッシュボードパネル
 *
 * API: GET /api/v1/tcg/analysis-dashboard/pipeline-summary
 * ADR-027: 全UI文字列は t("key") 経由。ハードコード日本語禁止。
 * ADR-067: 色・サイズはデザイントークンのみ。
 * ADR-144: Card / Badge / DataTable 金型のみ使用。
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { Card } from "../../../components/Card";
import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import "./AnalysisDashboardPanel.css";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義（API contract に合わせて定義）
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
// コンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function AnalysisDashboardPanel() {
  const { t } = useTranslation();
  const [data, setData] = useState<PipelineSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .get<PipelineSummary>("/tcg/analysis-dashboard/pipeline-summary")
      .then((res) => {
        setData(res);
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
        <p className="analysis-dashboard-empty">
          {t("analysisRules.dashboard.loading")}
        </p>
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

  // 算出値
  const extractionSuccessRate =
    data.extraction.total > 0
      ? (data.extraction.by_status.done / data.extraction.total) * 100
      : 0;

  // エンジン情報が全て null の場合は「データなし」とみなす
  const hasEngineInfo =
    data.engine.current_model != null ||
    data.engine.current_prompt_version != null ||
    data.engine.current_engine_version != null;

  // エラーテーブル用列定義
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

  return (
    <div className="analysis-dashboard">
      {/* 上段: KPIカード5枚 */}
      <div className="analysis-dashboard-metrics">
        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.totalJobs")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {data.extraction.total.toLocaleString()}
            <span
              style={{
                fontSize: "var(--font-sm)",
                marginLeft: "var(--space-1)",
                color: "var(--text-secondary)",
              }}
            >
              {t("analysisRules.dashboard.jobs")}
            </span>
          </div>
        </Card>

        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.extractionSuccessRate")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {extractionSuccessRate.toFixed(1)}%
          </div>
        </Card>

        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.pidResolutionRate")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {(data.analysis.pid_resolved_rate * 100).toFixed(1)}%
          </div>
        </Card>

        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.unitResolutionRate")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {(data.analysis.unit_resolved_rate * 100).toFixed(1)}%
          </div>
        </Card>

        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.needsReviewRate")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {(data.analysis.needs_review_rate * 100).toFixed(1)}%
          </div>
        </Card>
      </div>

      {/* 中段: アラートバッジ */}
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

      {/* 下段グリッド */}
      <div className="analysis-dashboard-grid">
        {/* 下段左: 要確認の理由内訳 */}
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

        {/* 下段中: エンジン情報 */}
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

        {/* 下段右: 直近のエラー */}
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
