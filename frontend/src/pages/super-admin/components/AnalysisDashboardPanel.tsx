/**
 * AnalysisDashboardPanel — 4タブ構成の解析ダッシュボード
 *
 * タブ構成:
 *   1. Import      — インポート履歴・未解決名率
 *   2. Extraction  — 抽出工程KPI・アラート・トレンド
 *   3. Analysis    — 解析工程KPI・要確認理由・CTA
 *   4. Distribution — 配信先・配信結果
 *
 * API:
 *   GET /api/v1/tcg/analysis-dashboard/pipeline-summary
 *   GET /api/v1/tcg/analysis-dashboard/trend?days=7
 *   GET /api/v1/tcg/analysis-dashboard/import-summary
 *   GET /api/v1/tcg/analysis-dashboard/distribution-summary
 *
 * ADR-027: 全UI文字列は t("key") 経由
 * ADR-067: 色・サイズはデザイントークンのみ
 * ADR-144: Card / Badge / DataTable / Tabs / recharts 金型のみ使用
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { api } from "../../../lib/api";
import { Card } from "../../../components/Card";
import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import { Tabs } from "../../../components/Tabs";
import type { TabItem } from "../../../components/Tabs";
import { DashboardIcons } from "../../../constants/icons";
import type { Icon } from "../../../constants/icons";
import type { AnalysisRulesSidebarKey } from "./AnalysisRulesSidebar";
import "./AnalysisDashboardPanel.css";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

type DashboardTab = "import" | "extraction" | "analysis" | "distribution";

// Supplier Pipeline 型定義

interface SupplierImportInfo {
  active_messages: number;
  latest_received_at: string | null;
}

interface SupplierExtractionInfo {
  done: number;
  empty: number;
  error: number;
  other: number;
  status: string; // "error" | "empty" | "done" | "pending"
}

interface SupplierAnalysisInfo {
  total: number;
  pid_resolved: number;
  pid_unresolved: number;
  unit_resolved: number;
  unit_unresolved: number;
  needs_review: number;
  excluded: number;
  price_ok: number;
  price_missing: number;
  distributable: number;
}

interface SupplierPipelineItem {
  channel_id: string;
  channel_name: string;
  import_info: SupplierImportInfo;
  extraction: SupplierExtractionInfo;
  analysis: SupplierAnalysisInfo;
  severity: string; // "danger" | "warning" | "success"
}

interface FunnelDropReasons {
  pid_unresolved: number;
  unit_unresolved: number;
  needs_review: number;
  excluded: number;
  price_missing: number;
}

interface FunnelSummary {
  active_messages: number;
  extraction_done: number;
  extraction_empty: number;
  extraction_error: number;
  analysis_total: number;
  distributable: number;
  drop_reasons: FunnelDropReasons;
}

interface SupplierPipelineResponse {
  suppliers: SupplierPipelineItem[];
  funnel_summary: FunnelSummary;
}

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

interface TrendDay {
  day: string;
  extraction_total: number;
  extraction_done: number;
  extraction_error: number;
  analysis_total: number;
  pid_resolved: number;
  unit_resolved: number;
  needs_review: number;
}

interface ImportTrendDay {
  day: string;
  job_count: number;
  message_count: number;
  unresolved_count: number;
}

interface ImportRecord {
  id: string;
  filename: string | null;
  message_count: number;
  unresolved_count: number;
  review_status: string | null;
  created_at: string | null;
  created_count: number;
}

interface ImportTableRow extends ImportRecord {
  resolved_count: number;
}

interface ImportSummary {
  total_jobs: number;
  total_messages: number;
  unresolved_rate: number;
  pending_review_count: number;
  orphan_count: number;
  active_message_count: number;
  latest_import_at: string | null;
  recent_imports: ImportRecord[];
}

interface DistributionTarget {
  id: string;
  name: string;
  is_active: boolean;
  last_distributed_at: string | null;
  last_distributed_count: number | null;
  last_result: string | null;
}

interface DistributionSetting {
  key: string;
  value: string;
  note: string | null;
}

interface DistributionSummary {
  active_target_count: number;
  total_target_count: number;
  total_last_distributed: number;
  targets: DistributionTarget[];
  settings: DistributionSetting[];
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

/** unresolvedRate（低い=良い）用の信号判定。10%未満=green, 20%未満=yellow, 以上=red */
function getUnresolvedSignalLevel(rate: number): SignalLevel {
  if (rate < 0.1) return "success";
  if (rate < 0.2) return "warning";
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
  displayRate: number;
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
  const [activeTab, setActiveTab] = useState<DashboardTab>("extraction");

  // Pipeline (Extraction + Analysis) data
  const [data, setData] = useState<PipelineSummary | null>(null);
  const [trend, setTrend] = useState<TrendDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Import tab data (lazy)
  const [importData, setImportData] = useState<ImportSummary | null>(null);
  const [importTrend, setImportTrend] = useState<ImportTrendDay[]>([]);
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  // Distribution tab data (lazy)
  const [distData, setDistData] = useState<DistributionSummary | null>(null);
  const [distLoading, setDistLoading] = useState(false);
  const [distError, setDistError] = useState<string | null>(null);

  // Supplier Pipeline data
  const [supplierData, setSupplierData] = useState<SupplierPipelineResponse | null>(null);
  const [supplierLoading, setSupplierLoading] = useState(false);

  // Load pipeline data on mount
  useEffect(() => {
    setLoading(true);
    setSupplierLoading(true);
    setError(null);
    Promise.all([
      api.get<PipelineSummary>("/tcg/analysis-dashboard/pipeline-summary"),
      api.get<TrendDay[]>("/tcg/analysis-dashboard/trend?days=7"),
      api.get<SupplierPipelineResponse>("/tcg/analysis-dashboard/supplier-pipeline"),
    ])
      .then(([summaryRes, trendRes, supplierRes]) => {
        setData(summaryRes);
        setTrend(trendRes);
        setSupplierData(supplierRes);
      })
      .catch(() => {
        setError(t("analysisRules.dashboard.fetchError"));
      })
      .finally(() => {
        setLoading(false);
        setSupplierLoading(false);
      });
  }, [t]);

  // Lazy load import data when tab is first opened
  useEffect(() => {
    if (activeTab !== "import" || importData !== null || importLoading) return;
    setImportLoading(true);
    setImportError(null);
    Promise.all([
      api.get<ImportSummary>("/tcg/analysis-dashboard/import-summary"),
      api.get<ImportTrendDay[]>("/tcg/analysis-dashboard/import-trend?days=7"),
    ])
      .then(([summaryRes, trendRes]) => {
        setImportData(summaryRes);
        setImportTrend(trendRes);
      })
      .catch(() => {
        setImportError(t("analysisRules.dashboard.fetchError"));
      })
      .finally(() => {
        setImportLoading(false);
      });
  }, [activeTab, importData, importLoading, t]);

  // Lazy load distribution data when tab is first opened
  useEffect(() => {
    if (activeTab !== "distribution" || distData !== null || distLoading) return;
    setDistLoading(true);
    setDistError(null);
    api
      .get<DistributionSummary>("/tcg/analysis-dashboard/distribution-summary")
      .then((res) => {
        setDistData(res);
      })
      .catch(() => {
        setDistError(t("analysisRules.dashboard.fetchError"));
      })
      .finally(() => {
        setDistLoading(false);
      });
  }, [activeTab, distData, distLoading, t]);

  const tabItems: TabItem<DashboardTab>[] = [
    { key: "import", label: t("analysisRules.dashboard.tabImport") },
    { key: "extraction", label: t("analysisRules.dashboard.tabExtraction") },
    { key: "analysis", label: t("analysisRules.dashboard.tabAnalysis") },
    { key: "distribution", label: t("analysisRules.dashboard.tabDistribution") },
  ];

  const handleCta = (key: AnalysisRulesSidebarKey) => {
    if (onNavigate) {
      onNavigate(key);
    }
  };

  const ArrowRightIcon = DashboardIcons.arrowRight;

  // Pipeline loading/error state covers Extraction + Analysis tabs
  const pipelineLoading = loading && (activeTab === "extraction" || activeTab === "analysis");
  const pipelineError = error && (activeTab === "extraction" || activeTab === "analysis");

  return (
    <div className="analysis-dashboard">
      {/* タブナビゲーション */}
      <div className="analysis-dashboard-nav">
        <Tabs
          items={tabItems}
          activeKey={activeTab}
          onChange={setActiveTab}
          variant="underline"
          size="md"
        />
      </div>

      {/* ── Import Tab ───────────────────────────────────────────────────── */}
      {activeTab === "import" && (
        <ImportTabContent
          data={importData}
          trend={importTrend}
          loading={importLoading}
          error={importError}
          supplierData={supplierData}
          supplierLoading={supplierLoading}
          t={t}
          onNavigate={handleCta}
          ArrowRightIcon={ArrowRightIcon}
        />
      )}

      {/* ── Extraction Tab ───────────────────────────────────────────────── */}
      {activeTab === "extraction" && (
        pipelineLoading ? (
          <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.loading")}</p>
        ) : pipelineError || !data ? (
          <p className="analysis-dashboard-error">
            {error ?? t("analysisRules.dashboard.fetchError")}
          </p>
        ) : (
          <ExtractionTabContent
            data={data}
            trend={trend}
            supplierData={supplierData}
            supplierLoading={supplierLoading}
            t={t}
            onNavigate={handleCta}
            ArrowRightIcon={ArrowRightIcon}
          />
        )
      )}

      {/* ── Analysis Tab ─────────────────────────────────────────────────── */}
      {activeTab === "analysis" && (
        pipelineLoading ? (
          <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.loading")}</p>
        ) : pipelineError || !data ? (
          <p className="analysis-dashboard-error">
            {error ?? t("analysisRules.dashboard.fetchError")}
          </p>
        ) : (
          <AnalysisTabContent
            data={data}
            trend={trend}
            supplierData={supplierData}
            supplierLoading={supplierLoading}
            t={t}
            onNavigate={handleCta}
            ArrowRightIcon={ArrowRightIcon}
          />
        )
      )}

      {/* ── Distribution Tab ─────────────────────────────────────────────── */}
      {activeTab === "distribution" && (
        <DistributionTabContent
          data={distData}
          loading={distLoading}
          error={distError}
          supplierData={supplierData}
          supplierLoading={supplierLoading}
          t={t}
        />
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Import Tab
// ──────────────────────────────────────────────────────────────────────────────

interface ImportTabContentProps {
  data: ImportSummary | null;
  trend: ImportTrendDay[];
  loading: boolean;
  error: string | null;
  supplierData: SupplierPipelineResponse | null;
  supplierLoading: boolean;
  t: (key: string) => string;
  onNavigate: (key: AnalysisRulesSidebarKey) => void;
  ArrowRightIcon: Icon;
}

function ImportTabContent({ data, trend, loading, error, supplierData, supplierLoading, t, onNavigate, ArrowRightIcon }: ImportTabContentProps) {
  if (loading) {
    return <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.loading")}</p>;
  }
  if (error || !data) {
    return (
      <p className="analysis-dashboard-error">
        {error ?? t("analysisRules.dashboard.fetchError")}
      </p>
    );
  }

  // Supplier import table: severity by latest_received_at age
  const importSupplierRows = supplierData
    ? [...supplierData.suppliers].sort((a, b) => {
        const order = { danger: 0, warning: 1, success: 2 };
        const aOrder = order[a.severity as keyof typeof order] ?? 3;
        const bOrder = order[b.severity as keyof typeof order] ?? 3;
        return aOrder - bOrder;
      })
    : [];

  const getImportSeverity = (item: SupplierPipelineItem): SignalLevel => {
    const receivedAt = item.import_info.latest_received_at;
    if (!receivedAt) return "danger";
    const ageMs = Date.now() - new Date(receivedAt).getTime();
    const ageDays = ageMs / (1000 * 60 * 60 * 24);
    if (ageDays >= 7) return "danger";
    if (ageDays >= 3) return "warning";
    return "success";
  };

  const dangerImportCount = supplierData
    ? supplierData.suppliers.filter((s) => getImportSeverity(s) === "danger").length
    : 0;

  type ImportSupplierRow = SupplierPipelineItem;

  const importSupplierColumns: DataTableColumn<ImportSupplierRow>[] = [
    {
      key: "channel_name",
      header: t("analysisRules.dashboard.supplierChannelName"),
    },
    {
      key: "import_info",
      header: t("analysisRules.dashboard.supplierActiveMessages"),
      width: "120px",
      renderCell: (row) => row.import_info.active_messages.toLocaleString(),
    },
    {
      key: "import_info",
      header: t("analysisRules.dashboard.supplierLatestReceivedAt"),
      width: "160px",
      renderCell: (row) => {
        if (!row.import_info.latest_received_at) return "-";
        return new Date(row.import_info.latest_received_at).toLocaleString("ja-JP", {
          timeZone: "Asia/Tokyo",
          year: "numeric",
          month: "long",
          day: "numeric",
        });
      },
    },
    {
      key: "severity",
      header: t("analysisRules.dashboard.supplierStatus"),
      width: "100px",
      renderCell: (row) => {
        const level = getImportSeverity(row);
        return (
          <Badge variant={level}>
            {t(`analysisRules.dashboard.supplierSeverity_${level}`)}
          </Badge>
        );
      },
    },
  ];

  // Derived values: match rate (positive framing, flipped from unresolved_rate)
  const matchRate = (1 - (data.unresolved_rate ?? 0)) * 100;
  const pendingCount = data.pending_review_count ?? 0;
  const needsAttention = matchRate < 80 || pendingCount > 0;
  const headerSignal: SignalLevel =
    matchRate < 60 ? "danger" : needsAttention ? "warning" : "success";
  const matchRateSignal: SignalLevel =
    matchRate >= 80 ? "success" : matchRate >= 60 ? "warning" : "danger";
  const pendingSignal: SignalLevel = pendingCount === 0 ? "success" : "warning";

  const headerMessage =
    matchRate < 60
      ? t("analysisRules.dashboard.importStatusDanger")
      : needsAttention
        ? t("analysisRules.dashboard.importStatusWarning")
        : t("analysisRules.dashboard.importStatusOk");

  const importColumns: DataTableColumn<ImportTableRow>[] = [
    {
      key: "filename",
      header: t("analysisRules.dashboard.importFilename"),
    },
    {
      key: "message_count",
      header: t("analysisRules.dashboard.importMessageCount"),
      width: "80px",
    },
    {
      key: "created_count",
      header: t("analysisRules.dashboard.importNewCount"),
      width: "80px",
    },
    {
      key: "resolved_count",
      header: t("analysisRules.dashboard.importResolvedCount"),
      width: "80px",
    },
    {
      key: "unresolved_count",
      header: t("analysisRules.dashboard.importUnresolvedCount"),
      width: "80px",
    },
    {
      key: "review_status",
      header: t("analysisRules.dashboard.importReviewStatus"),
      width: "100px",
    },
    {
      key: "created_at",
      header: t("analysisRules.dashboard.importDate"),
      width: "180px",
      renderCell: (row: ImportTableRow) => {
        if (!row.created_at) return "-";
        return new Date(row.created_at).toLocaleString("ja-JP", {
          timeZone: "Asia/Tokyo",
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      },
    },
  ];

  const tableData: ImportTableRow[] = (data.recent_imports ?? []).map((item) => ({
    ...item,
    resolved_count: (item.created_count ?? 0) - (item.unresolved_count ?? 0),
  }));

  return (
    <>
      {/* 問題バー */}
      {!supplierLoading && dangerImportCount > 0 && (
        <div className="analysis-dashboard-problem-banner">
          <Badge variant="danger">
            {`${dangerImportCount}${t("analysisRules.dashboard.supplierProblemCount")}`}
          </Badge>
        </div>
      )}

      {/* 提供者テーブル */}
      {!supplierLoading && importSupplierRows.length > 0 && (
        <div className="analysis-dashboard-supplier-section">
          <h3>{t("analysisRules.dashboard.supplierTableTitle")}</h3>
          <DataTable<ImportSupplierRow>
            columns={importSupplierColumns}
            data={importSupplierRows}
            rowKey={(row) => row.channel_id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
        </div>
      )}

      {/* 既存コンテンツ */}
      <div className="analysis-dashboard-existing-section">

      {/* サマリーカード — 信号灯 + 3指標 + CTA */}
      <Card
        variant="metric"
        density="compact"
        className={getSignalClass(headerSignal)}
      >
        <h4 className="analysis-dashboard-import-header">{headerMessage}</h4>
        <div className="analysis-dashboard-import-summary">
          {/* 処理済みメッセージ */}
          <div className="analysis-dashboard-import-row">
            <span className="analysis-dashboard-import-label">
              {t("analysisRules.dashboard.importProcessedMessages")}
            </span>
            <span className="analysis-dashboard-import-value">
              {data.active_message_count.toLocaleString()}
              {t("analysisRules.dashboard.items")}
            </span>
          </div>

          {/* 名前の一致率 */}
          <div className="analysis-dashboard-import-row">
            <span className="analysis-dashboard-import-label">
              {t("analysisRules.dashboard.importMatchRate")}
            </span>
            <span className="analysis-dashboard-import-value">
              {matchRate.toFixed(1)}%
              <Badge variant={matchRateSignal} size="sm">
                {matchRateSignal === "success"
                  ? t("analysisRules.dashboard.importStatusOk")
                  : matchRateSignal === "warning"
                    ? t("analysisRules.dashboard.importStatusWarning")
                    : t("analysisRules.dashboard.importStatusDanger")}
              </Badge>
              {matchRate < 100 && (
                <button
                  type="button"
                  className="analysis-dashboard-cta-btn"
                  onClick={() => onNavigate("supplier-master")}
                >
                  {t("analysisRules.dashboard.importCheckSupplierCta")}
                </button>
              )}
            </span>
          </div>

          {/* 要対応 */}
          <div className="analysis-dashboard-import-row">
            <span className="analysis-dashboard-import-label">
              {t("analysisRules.dashboard.importActionRequired")}
            </span>
            <span className="analysis-dashboard-import-value">
              {pendingCount === 0
                ? t("analysisRules.dashboard.importNoAction")
                : `${pendingCount.toLocaleString()}${t("analysisRules.dashboard.items")}`}
              <Badge variant={pendingSignal} size="sm">
                {pendingSignal === "success"
                  ? t("analysisRules.dashboard.importNoAction")
                  : `${pendingCount.toLocaleString()}${t("analysisRules.dashboard.items")}`}
              </Badge>
              {pendingCount > 0 && (
                <button
                  type="button"
                  className="analysis-dashboard-cta-btn"
                  onClick={() => onNavigate("needs-review")}
                >
                  {t("analysisRules.dashboard.importReviewCta")}
                  <ArrowRightIcon size={14} />
                </button>
              )}
            </span>
          </div>
        </div>
      </Card>

      {/* 最新インポート日時 */}
      {data.latest_import_at != null && (
        <div className="analysis-dashboard-import-latest">
          <span className="analysis-dashboard-engine-label">
            {t("analysisRules.dashboard.importLatestAt")}
          </span>
          <span className="analysis-dashboard-engine-value">{data.latest_import_at}</span>
        </div>
      )}

      {/* インポートトレンドグラフ */}
      {trend.length > 0 && (
        <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.importTrendTitle")}
          </div>
          <div className="analysis-dashboard-chart">
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="job_count"
                  name={t("analysisRules.dashboard.importTrendJobCount")}
                  stroke="var(--color-warning)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="message_count"
                  name={t("analysisRules.dashboard.importTrendMessageCount")}
                  stroke="var(--color-success)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 直近インポート一覧 */}
      <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.importTotal")}
        </div>
        {tableData.length === 0 ? (
          <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
        ) : (
          <DataTable<ImportTableRow>
            columns={importColumns}
            data={tableData}
            rowKey={(row) => row.id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
        )}
      </Card>
      </div>{/* end analysis-dashboard-existing-section */}
    </>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Extraction Tab
// ──────────────────────────────────────────────────────────────────────────────

interface ExtractionTabContentProps {
  data: PipelineSummary;
  trend: TrendDay[];
  supplierData: SupplierPipelineResponse | null;
  supplierLoading: boolean;
  t: (key: string) => string;
  onNavigate: (key: AnalysisRulesSidebarKey) => void;
  ArrowRightIcon: Icon;
}

function ExtractionTabContent({ data, trend, supplierData, supplierLoading, t, onNavigate, ArrowRightIcon }: ExtractionTabContentProps) {
  const extractionSuccessRate =
    data.extraction.total > 0
      ? data.extraction.by_status.done / data.extraction.total
      : 0;

  const successLevel = getSignalLevel(extractionSuccessRate);
  const errorLevel: SignalLevel = data.extraction.error_rate > 0.2 ? "danger"
    : data.extraction.error_rate > 0.1 ? "warning" : "success";

  // Extraction-only bottleneck
  const isBottleneck = successLevel !== "success";

  // Extraction trend lines only
  const chartData = trend.map((d) => ({
    day: d.day.slice(5),
    extractionRate:
      d.extraction_total > 0
        ? Math.round((d.extraction_done / d.extraction_total) * 100)
        : 0,
    errorRate:
      d.extraction_total > 0
        ? Math.round((d.extraction_error / d.extraction_total) * 100)
        : 0,
  }));

  // Supplier extraction table
  const extractionSupplierRows = supplierData
    ? [...supplierData.suppliers].sort((a, b) => {
        const order = { error: 0, empty: 1, done: 2, pending: 3 };
        const aOrder = order[a.extraction.status as keyof typeof order] ?? 4;
        const bOrder = order[b.extraction.status as keyof typeof order] ?? 4;
        return aOrder - bOrder;
      })
    : [];

  const dangerExtractionCount = supplierData
    ? supplierData.suppliers.filter((s) => s.extraction.status === "error").length
    : 0;

  type ExtractionSupplierRow = SupplierPipelineItem;

  const extractionSupplierColumns: DataTableColumn<ExtractionSupplierRow>[] = [
    {
      key: "channel_name",
      header: t("analysisRules.dashboard.supplierChannelName"),
    },
    {
      key: "extraction",
      header: t("analysisRules.dashboard.supplierExtractionStatus"),
      width: "100px",
      renderCell: (row) => {
        const statusVariant =
          row.extraction.status === "error" ? "danger"
            : row.extraction.status === "empty" ? "warning"
              : row.extraction.status === "done" ? "success"
                : "neutral";
        return (
          <Badge variant={statusVariant}>
            {t(`analysisRules.dashboard.supplierExtractionStatus_${row.extraction.status}`)}
          </Badge>
        );
      },
    },
    {
      key: "extraction",
      header: t("analysisRules.dashboard.supplierExtractionDone"),
      width: "80px",
      renderCell: (row) => row.extraction.done.toLocaleString(),
    },
    {
      key: "extraction",
      header: t("analysisRules.dashboard.supplierExtractionError"),
      width: "80px",
      renderCell: (row) => row.extraction.error.toLocaleString(),
    },
    {
      key: "extraction",
      header: t("analysisRules.dashboard.supplierExtractionEmpty"),
      width: "80px",
      renderCell: (row) => row.extraction.empty.toLocaleString(),
    },
  ];

  return (
    <>
      {/* 問題バー */}
      {!supplierLoading && dangerExtractionCount > 0 && (
        <div className="analysis-dashboard-problem-banner">
          <Badge variant="danger">
            {`${dangerExtractionCount}${t("analysisRules.dashboard.supplierProblemCount")}`}
          </Badge>
        </div>
      )}

      {/* 提供者テーブル */}
      {!supplierLoading && extractionSupplierRows.length > 0 && (
        <div className="analysis-dashboard-supplier-section">
          <h3>{t("analysisRules.dashboard.supplierTableTitle")}</h3>
          <DataTable<ExtractionSupplierRow>
            columns={extractionSupplierColumns}
            data={extractionSupplierRows}
            rowKey={(row) => row.channel_id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
        </div>
      )}

      {/* 既存コンテンツ */}
      <div className="analysis-dashboard-existing-section">

      {/* ボトルネックヒーロー */}
      {isBottleneck && (
        <div className={`analysis-dashboard-hero ${getSignalClass(successLevel)}`}>
          <div className="analysis-dashboard-hero-content">
            <Badge variant={successLevel === "danger" ? "danger" : "warning"} dot>
              {t("analysisRules.dashboard.bottleneckLabel")}
            </Badge>
            <div className="analysis-dashboard-hero-metric">
              <span className="analysis-dashboard-hero-name">
                {t("analysisRules.dashboard.extractionSuccessRate")}
              </span>
              <span className="analysis-dashboard-hero-value">
                {(extractionSuccessRate * 100).toFixed(1)}%
              </span>
            </div>
            <p className="analysis-dashboard-hero-desc">
              {t("analysisRules.dashboard.bottleneckDesc")}
            </p>
            <button
              type="button"
              className="analysis-dashboard-cta-btn analysis-dashboard-cta-btn--primary"
              onClick={() => onNavigate("accuracy-management")}
            >
              {t("analysisRules.dashboard.ctaAccuracy")}
              <ArrowRightIcon size={16} />
            </button>
          </div>
        </div>
      )}

      {/* KPIカード */}
      <div className="analysis-dashboard-metrics">
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

        <Card
          variant="metric"
          density="compact"
          className={getSignalClass(successLevel)}
        >
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.extractionSuccessRate")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {(extractionSuccessRate * 100).toFixed(1)}%
          </div>
        </Card>

        <Card
          variant="metric"
          density="compact"
          className={getSignalClass(errorLevel)}
        >
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.extractionErrorRate")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {(data.extraction.error_rate * 100).toFixed(1)}%
          </div>
        </Card>

        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.staleRunning")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {data.extraction.stale_running_count.toLocaleString()}
            <span className="analysis-dashboard-metric-unit">
              {t("analysisRules.dashboard.items")}
            </span>
          </div>
        </Card>
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
        <div className="analysis-dashboard-alert-item">
          <Badge variant="info" dot>
            {t("analysisRules.dashboard.pending")}{" "}
            {data.extraction.by_status.pending}
            {t("analysisRules.dashboard.items")}
          </Badge>
        </div>
      </div>

      {/* CTAボタン */}
      <div className="analysis-dashboard-ctas">
        <button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => onNavigate("accuracy-management")}
        >
          {t("analysisRules.dashboard.ctaAccuracy")}
          <ArrowRightIcon size={16} />
        </button>
      </div>

      {/* 抽出トレンドグラフ */}
      {chartData.length > 0 && (
        <Card
          variant="container"
          density="compact"
          className="analysis-dashboard-chart-card"
        >
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.trendTitle")}
          </div>
          <div className="analysis-dashboard-chart">
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" fontSize={12} />
                <YAxis domain={[0, 100]} unit="%" fontSize={12} />
                <Tooltip formatter={(value) => `${Number(value)}%`} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="extractionRate"
                  name={t("analysisRules.dashboard.extractionSuccessRate")}
                  stroke="var(--color-success)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="errorRate"
                  name={t("analysisRules.dashboard.extractionErrorRate")}
                  stroke="var(--color-error)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 直近のエラー */}
      {data.recent_errors.length > 0 && (
        <Card variant="container" density="compact">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.recentErrors")}
          </div>
          <DataTable<RecentError>
            columns={[
              { key: "error_message", header: t("analysisRules.dashboard.errorMessage") },
              { key: "created_at", header: t("analysisRules.dashboard.errorDate"), width: "180px" },
            ]}
            data={data.recent_errors}
            rowKey={(row) => row.id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noErrors")}
          />
        </Card>
      )}
      </div>{/* end analysis-dashboard-existing-section */}
    </>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Analysis Tab
// ──────────────────────────────────────────────────────────────────────────────

interface AnalysisTabContentProps {
  data: PipelineSummary;
  trend: TrendDay[];
  supplierData: SupplierPipelineResponse | null;
  supplierLoading: boolean;
  t: (key: string) => string;
  onNavigate: (key: AnalysisRulesSidebarKey) => void;
  ArrowRightIcon: Icon;
}

function AnalysisTabContent({ data, trend, supplierData, supplierLoading, t, onNavigate, ArrowRightIcon }: AnalysisTabContentProps) {
  const pidRate = data.analysis.pid_resolved_rate;
  const unitRate = data.analysis.unit_resolved_rate;
  const needsReviewRate = data.analysis.needs_review_rate;
  const needsReviewHealthRate = 1 - needsReviewRate;

  const metrics: MetricDef[] = [
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
      displayRate: needsReviewRate,
      level: getSignalLevel(needsReviewHealthRate),
      ctaKey: "needs-review",
      ctaLabelKey: "analysisRules.dashboard.ctaNeedsReview",
    },
  ];

  const bottleneck = metrics.reduce((worst, m) => (m.rate < worst.rate ? m : worst));

  // Analysis trend lines only
  const chartData = trend.map((d) => ({
    day: d.day.slice(5),
    pidRate:
      d.analysis_total > 0
        ? Math.round((d.pid_resolved / d.analysis_total) * 100)
        : 0,
    unitRate:
      d.analysis_total > 0
        ? Math.round((d.unit_resolved / d.analysis_total) * 100)
        : 0,
    reviewRate:
      d.analysis_total > 0
        ? Math.round((d.needs_review / d.analysis_total) * 100)
        : 0,
  }));

  // Supplier analysis table: sort by distributable rate ascending
  const getAnalysisDistributableRate = (item: SupplierPipelineItem): number => {
    return item.analysis.total > 0
      ? item.analysis.distributable / item.analysis.total
      : 0;
  };

  const getAnalysisRateLevel = (rate: number): SignalLevel => {
    if (rate === 0) return "danger";
    if (rate < 0.5) return "warning";
    return "success";
  };

  const analysisSupplierRows = supplierData
    ? [...supplierData.suppliers].sort(
        (a, b) => getAnalysisDistributableRate(a) - getAnalysisDistributableRate(b)
      )
    : [];

  const dangerAnalysisCount = supplierData
    ? supplierData.suppliers.filter(
        (s) => getAnalysisRateLevel(getAnalysisDistributableRate(s)) === "danger"
      ).length
    : 0;

  type AnalysisSupplierRow = SupplierPipelineItem;

  const analysisSupplierColumns: DataTableColumn<AnalysisSupplierRow>[] = [
    {
      key: "channel_name",
      header: t("analysisRules.dashboard.supplierChannelName"),
    },
    {
      key: "analysis",
      header: t("analysisRules.dashboard.supplierPidResolved"),
      width: "120px",
      renderCell: (row) =>
        `${row.analysis.pid_resolved} / ${row.analysis.total}`,
    },
    {
      key: "analysis",
      header: t("analysisRules.dashboard.supplierUnitResolved"),
      width: "120px",
      renderCell: (row) =>
        `${row.analysis.unit_resolved} / ${row.analysis.total}`,
    },
    {
      key: "analysis",
      header: t("analysisRules.dashboard.supplierNeedsReview"),
      width: "100px",
      renderCell: (row) => row.analysis.needs_review.toLocaleString(),
    },
    {
      key: "analysis",
      header: t("analysisRules.dashboard.supplierDistributable"),
      width: "100px",
      renderCell: (row) => row.analysis.distributable.toLocaleString(),
    },
    {
      key: "severity",
      header: t("analysisRules.dashboard.supplierDistributableRate"),
      width: "120px",
      renderCell: (row) => {
        const rate = getAnalysisDistributableRate(row);
        const level = getAnalysisRateLevel(rate);
        const rateClass = `analysis-dashboard-rate-cell analysis-dashboard-rate-cell--${level}`;
        return (
          <div className={rateClass}>
            <Badge variant={level} size="sm">
              {(rate * 100).toFixed(0)}%
            </Badge>
          </div>
        );
      },
    },
  ];

  return (
    <>
      {/* 問題バー */}
      {!supplierLoading && dangerAnalysisCount > 0 && (
        <div className="analysis-dashboard-problem-banner">
          <Badge variant="danger">
            {`${dangerAnalysisCount}${t("analysisRules.dashboard.supplierProblemCount")}`}
          </Badge>
        </div>
      )}

      {/* 提供者テーブル */}
      {!supplierLoading && analysisSupplierRows.length > 0 && (
        <div className="analysis-dashboard-supplier-section">
          <h3>{t("analysisRules.dashboard.supplierTableTitle")}</h3>
          <DataTable<AnalysisSupplierRow>
            columns={analysisSupplierColumns}
            data={analysisSupplierRows}
            rowKey={(row) => row.channel_id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
        </div>
      )}

      {/* 既存コンテンツ */}
      <div className="analysis-dashboard-existing-section">

      {/* ボトルネックヒーロー */}
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
              onClick={() => onNavigate(bottleneck.ctaKey)}
            >
              {t(bottleneck.ctaLabelKey)}
              <ArrowRightIcon size={16} />
            </button>
          </div>
        </div>
      )}

      {/* KPIカード */}
      <div className="analysis-dashboard-metrics">
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

        {data.analysis.missing_count > 0 && (
          <div className="analysis-dashboard-alert-item">
            <Badge variant="warning" dot>
              {t("analysisRules.dashboard.analysisMissing")}{" "}
              {data.analysis.missing_count}
              {t("analysisRules.dashboard.items")}
            </Badge>
          </div>
        )}
      </div>

      {/* CTAボタン */}
      <div className="analysis-dashboard-ctas">
        <button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => onNavigate("needs-review")}
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
          onClick={() => onNavigate("product-master")}
        >
          {t("analysisRules.dashboard.ctaProductMaster")}
          <ArrowRightIcon size={16} />
        </button>
        <button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => onNavigate("unit-master")}
        >
          {t("analysisRules.dashboard.ctaUnitMaster")}
          <ArrowRightIcon size={16} />
        </button>
      </div>

      {/* 解析トレンドグラフ */}
      {chartData.length > 0 && (
        <Card
          variant="container"
          density="compact"
          className="analysis-dashboard-chart-card"
        >
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.trendTitle")}
          </div>
          <div className="analysis-dashboard-chart">
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" fontSize={12} />
                <YAxis domain={[0, 100]} unit="%" fontSize={12} />
                <Tooltip formatter={(value) => `${Number(value)}%`} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="pidRate"
                  name={t("analysisRules.dashboard.pidResolutionRate")}
                  stroke="var(--color-warning)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="unitRate"
                  name={t("analysisRules.dashboard.unitResolutionRate")}
                  stroke="var(--color-success)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="reviewRate"
                  name={t("analysisRules.dashboard.needsReviewRate")}
                  stroke="var(--color-error)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 要確認の理由内訳 */}
      <div className="analysis-dashboard-grid">
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
          {(data.engine.current_model == null &&
            data.engine.current_prompt_version == null &&
            data.engine.current_engine_version == null) ? (
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
      </div>
      </div>{/* end analysis-dashboard-existing-section */}
    </>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Distribution Tab
// ──────────────────────────────────────────────────────────────────────────────

interface DistributionTabContentProps {
  data: DistributionSummary | null;
  loading: boolean;
  error: string | null;
  supplierData: SupplierPipelineResponse | null;
  supplierLoading: boolean;
  t: (key: string) => string;
}

function DistributionTabContent({ data, loading, error, supplierData, supplierLoading, t }: DistributionTabContentProps) {
  if (loading) {
    return <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.loading")}</p>;
  }
  if (error || !data) {
    return (
      <p className="analysis-dashboard-error">
        {error ?? t("analysisRules.dashboard.fetchError")}
      </p>
    );
  }

  const targetColumns: DataTableColumn<DistributionTarget>[] = [
    {
      key: "name",
      header: t("analysisRules.dashboard.distributionTargetName"),
    },
    {
      key: "is_active",
      header: t("analysisRules.dashboard.distributionActive"),
      width: "80px",
      renderCell: (row) => (
        <Badge variant={row.is_active ? "success" : "neutral"}>
          {row.is_active
            ? t("analysisRules.dashboard.distributionActive")
            : t("analysisRules.dashboard.distributionInactive")}
        </Badge>
      ),
    },
    {
      key: "last_distributed_at",
      header: t("analysisRules.dashboard.distributionLastAt"),
      width: "160px",
    },
    {
      key: "last_distributed_count",
      header: t("analysisRules.dashboard.distributionLastCount"),
      width: "100px",
    },
    {
      key: "last_result",
      header: t("analysisRules.dashboard.distributionLastResult"),
      width: "100px",
    },
  ];

  const settingColumns: DataTableColumn<DistributionSetting>[] = [
    {
      key: "key",
      header: t("analysisRules.dashboard.distributionSettingKey"),
    },
    {
      key: "value",
      header: t("analysisRules.dashboard.distributionSettingValue"),
    },
    {
      key: "note",
      header: t("analysisRules.dashboard.distributionSettingNote"),
    },
  ];

  // Supplier distribution table: sort distributable=0 first
  const DROP_REASON_PRIORITY: Array<keyof FunnelDropReasons> = [
    "unit_unresolved",
    "pid_unresolved",
    "needs_review",
    "excluded",
    "price_missing",
  ];

  const getTopDropReason = (item: SupplierPipelineItem): keyof FunnelDropReasons | null => {
    let topKey: keyof FunnelDropReasons | null = null;
    let topVal = 0;
    for (const key of DROP_REASON_PRIORITY) {
      const val = item.analysis[key as keyof SupplierAnalysisInfo] as number;
      if (val > topVal) {
        topVal = val;
        topKey = key;
      }
    }
    return topKey;
  };

  const distributionSupplierRows = supplierData
    ? [...supplierData.suppliers].sort((a, b) => {
        const aZero = a.analysis.distributable === 0 ? 0 : 1;
        const bZero = b.analysis.distributable === 0 ? 0 : 1;
        return aZero - bZero;
      })
    : [];

  const dangerDistributionCount = supplierData
    ? supplierData.suppliers.filter((s) => s.analysis.distributable === 0).length
    : 0;

  type DistributionSupplierRow = SupplierPipelineItem;

  const distributionSupplierColumns: DataTableColumn<DistributionSupplierRow>[] = [
    {
      key: "channel_name",
      header: t("analysisRules.dashboard.supplierChannelName"),
    },
    {
      key: "analysis",
      header: t("analysisRules.dashboard.supplierDistributable"),
      width: "100px",
      renderCell: (row) => row.analysis.distributable.toLocaleString(),
    },
    {
      key: "severity",
      header: t("analysisRules.dashboard.supplierTopDropReason"),
      width: "160px",
      renderCell: (row) => {
        const topKey = getTopDropReason(row);
        if (!topKey) return "-";
        return (
          <Badge variant="warning">
            {t(`analysisRules.dashboard.supplierDropReason_${topKey}`)}
          </Badge>
        );
      },
    },
  ];

  return (
    <>
      {/* 問題バー */}
      {!supplierLoading && dangerDistributionCount > 0 && (
        <div className="analysis-dashboard-problem-banner">
          <Badge variant="danger">
            {`${dangerDistributionCount}${t("analysisRules.dashboard.supplierProblemCount")}`}
          </Badge>
        </div>
      )}

      {/* 提供者テーブル */}
      {!supplierLoading && distributionSupplierRows.length > 0 && (
        <div className="analysis-dashboard-supplier-section">
          <h3>{t("analysisRules.dashboard.supplierTableTitle")}</h3>
          <DataTable<DistributionSupplierRow>
            columns={distributionSupplierColumns}
            data={distributionSupplierRows}
            rowKey={(row) => row.channel_id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
        </div>
      )}

      {/* 既存コンテンツ */}
      <div className="analysis-dashboard-existing-section">

      {/* KPIカード */}
      <div className="analysis-dashboard-metrics">
        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.distributionActiveTargets")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {data.active_target_count.toLocaleString()}
            <span className="analysis-dashboard-metric-unit">
              {t("analysisRules.dashboard.items")}
            </span>
          </div>
        </Card>

        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.distributionTotalDistributed")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {data.total_last_distributed.toLocaleString()}
            <span className="analysis-dashboard-metric-unit">
              {t("analysisRules.dashboard.items")}
            </span>
          </div>
        </Card>
      </div>

      {/* 配信先テーブル */}
      <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.distributionTargets")}
        </div>
        {data.targets.length === 0 ? (
          <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
        ) : (
          <DataTable<DistributionTarget>
            columns={targetColumns}
            data={data.targets}
            rowKey={(row) => row.id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
        )}
      </Card>

      {/* 配信設定テーブル */}
      {data.settings.length > 0 && (
        <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.distributionSettings")}
          </div>
          <DataTable<DistributionSetting>
            columns={settingColumns}
            data={data.settings}
            rowKey={(row) => row.key}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
        </Card>
      )}
      </div>{/* end analysis-dashboard-existing-section */}
    </>
  );
}
