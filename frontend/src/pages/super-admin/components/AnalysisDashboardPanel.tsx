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
import React, { useEffect, useRef, useState } from "react";
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
import { Button } from "../../../components/Button";
import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import { Tabs } from "../../../components/Tabs";
import type { TabItem } from "../../../components/Tabs";
import { SelectControl } from "../../../components/Select";
import type { SelectOption } from "../../../components/Select";
import { DashboardIcons } from "../../../constants/icons";
import type { Icon } from "../../../constants/icons";
import type { AnalysisRulesSidebarKey } from "./AnalysisRulesSidebar";
import type { SupplierQualitySummary } from "../../../features/tcg-analysis-review/supplierQuality";
import "./AnalysisDashboardPanel.css";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

type DashboardTab = "import" | "extraction" | "analysis" | "distribution";

interface ImportResultResponse {
  status: "imported" | "already_imported";
  review_status: "ok" | "pending_review";
  message_count: number;
  provider_count: number;
  unresolved_count: number;
  unresolved_display_names: string[];
  import_job_id: string;
}

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

interface ExtractionBySupplierItem {
  supplier_code: string | null;
  supplier_name: string | null;
  total_jobs: number;
  done_count: number;
  error_count: number;
  empty_count: number;
}

interface PipelineSummary {
  extraction: ExtractionSummary;
  analysis: AnalysisSummary;
  review_reasons: ReviewReason[];
  engine: EngineSummary;
  recent_errors: RecentError[];
  extraction_by_supplier: ExtractionBySupplierItem[];
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
  const [trendDays, setTrendDays] = useState<number>(7);

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

  // Supplier quality summaries (lazy, analysis tab)
  const [qualitySummaries, setQualitySummaries] = useState<SupplierQualitySummary[] | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  // Supplier Pipeline data
  const [supplierData, setSupplierData] = useState<SupplierPipelineResponse | null>(null);
  const [supplierLoading, setSupplierLoading] = useState(false);

  // Load pipeline data on mount and when trendDays changes
  useEffect(() => {
    setLoading(true);
    setSupplierLoading(true);
    setError(null);
    Promise.all([
      api.get<PipelineSummary>("/tcg/analysis-dashboard/pipeline-summary"),
      api.get<TrendDay[]>(`/tcg/analysis-dashboard/trend?days=${trendDays}`),
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
  }, [t, trendDays]);

  // Lazy load import data when tab is first opened; re-fetch trend when trendDays changes
  useEffect(() => {
    if (activeTab !== "import" || importLoading) return;
    // fetch summary only when not yet loaded; always fetch trend on trendDays change
    if (importData !== null) {
      // only re-fetch trend
      setImportLoading(true);
      setImportError(null);
      api.get<ImportTrendDay[]>(`/tcg/analysis-dashboard/import-trend?days=${trendDays}`)
        .then((trendRes) => {
          setImportTrend(trendRes);
        })
        .catch(() => {
          setImportError(t("analysisRules.dashboard.fetchError"));
        })
        .finally(() => {
          setImportLoading(false);
        });
      return;
    }
    setImportLoading(true);
    setImportError(null);
    Promise.all([
      api.get<ImportSummary>("/tcg/analysis-dashboard/import-summary"),
      api.get<ImportTrendDay[]>(`/tcg/analysis-dashboard/import-trend?days=${trendDays}`),
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
  }, [activeTab, trendDays, t]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // Lazy load supplier quality summaries when analysis tab is first opened
  useEffect(() => {
    if (activeTab !== "analysis" || qualitySummaries !== null || qualityLoading) return;
    setQualityLoading(true);

    interface ApiSummaryRaw {
      supplier_id: string;
      supplier_name: string;
      analysis_count: number;
      needs_review_count: number;
      product_id_unresolved_count: number;
      unit_unresolved_count: number;
      condition_fallback_count: number | null;
    }
    interface ApiQualityResponse {
      summaries: ApiSummaryRaw[];
    }

    api
      .get<ApiQualityResponse>("/tcg/supplier-quality-summaries")
      .then((res) => {
        setQualitySummaries(
          res.summaries.map((raw) => ({
            supplierId: raw.supplier_id,
            supplierName: raw.supplier_name,
            analysisCount: raw.analysis_count,
            needsReviewCount: raw.needs_review_count,
            productIdUnresolvedCount: raw.product_id_unresolved_count,
            unitUnresolvedCount: raw.unit_unresolved_count,
            conditionFallbackCount: raw.condition_fallback_count,
          }))
        );
      })
      .catch(() => {
        // silently ignore — table will not render
        setQualitySummaries([]);
      })
      .finally(() => {
        setQualityLoading(false);
      });
  }, [activeTab, qualitySummaries, qualityLoading]);

  const tabItems: TabItem<DashboardTab>[] = [
    { key: "import", label: t("analysisRules.dashboard.tabImport") },
    { key: "extraction", label: t("analysisRules.dashboard.tabExtraction") },
    { key: "analysis", label: t("analysisRules.dashboard.tabAnalysis") },
    { key: "distribution", label: t("analysisRules.dashboard.tabDistribution") },
  ];

  const periodOptions: SelectOption[] = [
    { value: "7", label: t("analysisRules.dashboard.period7d") },
    { value: "30", label: t("analysisRules.dashboard.period30d") },
    { value: "90", label: t("analysisRules.dashboard.period90d") },
    { value: "180", label: t("analysisRules.dashboard.period180d") },
    { value: "360", label: t("analysisRules.dashboard.period360d") },
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
        <div className="analysis-dashboard-period-selector" aria-label={t("analysisRules.dashboard.periodLabel")}>
          <SelectControl
            options={periodOptions}
            size="sm"
            value={String(trendDays)}
            onChange={(e) => setTrendDays(Number(e.target.value))}
          />
        </div>
      </div>

      {/* ── Import Tab ───────────────────────────────────────────────────── */}
      {activeTab === "import" && (
        <ImportTabContent
          data={importData}
          trend={importTrend}
          loading={importLoading}
          error={importError}
          trendDays={trendDays}
          t={t}
          onNavigate={handleCta}
          ArrowRightIcon={ArrowRightIcon}
          onUploadSuccess={() => {
            // Re-fetch import summary after successful upload
            setImportData(null);
          }}
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
            trendDays={trendDays}
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
            qualitySummaries={qualitySummaries}
            qualityLoading={qualityLoading}
            trendDays={trendDays}
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
  trendDays: number;
  t: (key: string) => string;
  onNavigate: (key: AnalysisRulesSidebarKey) => void;
  ArrowRightIcon: Icon;
  onUploadSuccess: () => void;
}

function ImportTabContent({ data, trend, loading, error, trendDays, t, onNavigate, ArrowRightIcon, onUploadSuccess }: ImportTabContentProps) {
  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [windowHours, setWindowHours] = useState("24");
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadResult, setUploadResult] = useState<ImportResultResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (file: File | null) => {
    if (!file) return;
    if (!file.name.endsWith(".txt")) {
      setUploadError(t("tcgLineImport.errorTxtOnly"));
      return;
    }
    setUploadError("");
    setUploadResult(null);
    setSelectedFile(file);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0] ?? null;
    handleFileChange(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError(t("tcgLineImport.errorSelectFile"));
      return;
    }
    setUploading(true);
    setUploadError("");
    setUploadResult(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    const hours = parseInt(windowHours, 10);
    formData.append("window_hours", isNaN(hours) ? "24" : String(hours));

    try {
      const data = await api.postForm<ImportResultResponse>("/tcg/line-import", formData);
      setUploadResult(data);
      onUploadSuccess();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : t("tcgLineImport.errorUploadFailed"));
    } finally {
      setUploading(false);
    }
  };

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

  const orphanCount = data.orphan_count ?? 0;

  return (
    <>
      {/* ── アップロードセクション ── */}
      <Card variant="container" density="compact">
        <h3>{t("analysisRules.dashboard.importUploadTitle")}</h3>

        {/* ドロップゾーン */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className="analysis-dashboard-dropzone"
          data-dragging={isDragging}
        >
          {/* ui-allow: 非表示ファイル入力はドロップゾーン専用ref用途、汎用コンポーネント非対象 (#3285) */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt"
            onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
            style={{ display: "none" }}
          />
          {/* ui-allow: Lucide file-up スタイルインラインSVG — 登録アイコンコンポーネントに該当なし (#3285) */}
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="analysis-dashboard-dropzone-icon"
            aria-hidden="true"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="12" y2="12" />
            <line x1="15" y1="15" x2="12" y2="12" />
          </svg>
          <p>{selectedFile ? selectedFile.name : t("analysisRules.dashboard.importDropHint")}</p>
        </div>

        {/* ウィンドウ時間 */}
        <div className="analysis-dashboard-upload-options">
          <label>{t("analysisRules.dashboard.importWindowHours")}</label>
          {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
          <input
            type="number"
            min="0"
            value={windowHours}
            onChange={(e) => setWindowHours(e.target.value)}
            className="analysis-dashboard-window-input"
          />
        </div>

        {/* アップロードボタン */}
        <Button
          variant="primary"
          size="sm"
          onClick={handleUpload}
          disabled={uploading || !selectedFile}
          loading={uploading}
          loadingText={t("analysisRules.dashboard.importUploading")}
        >
          {t("analysisRules.dashboard.importUploadButton")}
        </Button>

        {/* エラー */}
        {uploadError && <Badge variant="danger">{uploadError}</Badge>}

        {/* 成功結果 */}
        {uploadResult && uploadResult.status !== "already_imported" && (
          <div className="analysis-dashboard-upload-result">
            <Badge variant={uploadResult.review_status === "pending_review" ? "warning" : "success"}>
              {uploadResult.review_status === "pending_review"
                ? t("analysisRules.dashboard.importNeedsReview")
                : t("analysisRules.dashboard.importSuccess")}
            </Badge>
            <span>{t("analysisRules.dashboard.importResultMessages").replace("{count}", String(uploadResult.message_count))}</span>
            {uploadResult.review_status === "pending_review" && (
              <Button variant="secondary" size="sm" onClick={() => onNavigate("import")}>
                {t("analysisRules.dashboard.importGoReview")}
              </Button>
            )}
          </div>
        )}
        {uploadResult && uploadResult.status === "already_imported" && (
          <Badge variant="neutral">{t("analysisRules.dashboard.importAlreadyImported")}</Badge>
        )}
      </Card>

      {/* 孤立メッセージ警告 */}
      {orphanCount > 0 && (
        <div className="analysis-dashboard-problem-banner">
          <Badge variant="warning">
            {`${orphanCount.toLocaleString()}${t("analysisRules.dashboard.items")} ${t("analysisRules.dashboard.importOrphanMessages")}`}
          </Badge>
          <button
            type="button"
            className="analysis-dashboard-cta-btn"
            onClick={() => onNavigate("supplier-master")}
          >
            {t("analysisRules.dashboard.importOrphanCta")}
            <ArrowRightIcon size={14} />
          </button>
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
          <span className="analysis-dashboard-engine-value">{data.latest_import_at ? new Date(data.latest_import_at).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "-"}</span>
        </div>
      )}

      {/* インポートトレンドグラフ */}
      {trend.length > 0 && (
        <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
          <div className="analysis-dashboard-section-title">
            {`${trendDays}${t("analysisRules.dashboard.importTrendTitle")}`}
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
  trendDays: number;
  t: (key: string) => string;
  onNavigate: (key: AnalysisRulesSidebarKey) => void;
  ArrowRightIcon: Icon;
}

function ExtractionTabContent({ data, trend, supplierData, supplierLoading, trendDays, t, onNavigate, ArrowRightIcon }: ExtractionTabContentProps) {
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
            {`${trendDays}${t("analysisRules.dashboard.trendTitle")}`}
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
              { key: "created_at", header: t("analysisRules.dashboard.errorDate"), width: "180px", renderCell: (row) => row.created_at ? new Date(row.created_at).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "-" },
            ]}
            data={data.recent_errors}
            rowKey={(row) => row.id}
            density="compact"
            emptyState={t("analysisRules.dashboard.noErrors")}
          />
        </Card>
      )}

      {/* 提供者別抽出エラー内訳 */}
      {data.extraction_by_supplier.filter((s) => s.error_count > 0).length > 0 && (
        <Card variant="container" density="compact">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.extractionSupplierTitle")}
          </div>
          <DataTable<ExtractionBySupplierItem>
            columns={[
              {
                key: "supplier_name",
                header: t("analysisRules.dashboard.extractionSupplierName"),
              },
              {
                key: "total_jobs",
                header: t("analysisRules.dashboard.extractionSupplierTotal"),
                width: "100px",
                renderCell: (row) => row.total_jobs.toLocaleString(),
              },
              {
                key: "done_count",
                header: t("analysisRules.dashboard.extractionSupplierDone"),
                width: "80px",
                renderCell: (row) => row.done_count.toLocaleString(),
              },
              {
                key: "error_count",
                header: t("analysisRules.dashboard.extractionSupplierError"),
                width: "80px",
                renderCell: (row) => (
                  <Badge variant="danger">{row.error_count.toLocaleString()}</Badge>
                ),
              },
            ]}
            data={data.extraction_by_supplier.filter((s) => s.error_count > 0)}
            rowKey={(row) => row.supplier_code ?? row.supplier_name ?? ""}
            density="compact"
            emptyState={t("analysisRules.dashboard.noData")}
          />
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
  qualitySummaries: SupplierQualitySummary[] | null;
  qualityLoading: boolean;
  trendDays: number;
  t: (key: string) => string;
  onNavigate: (key: AnalysisRulesSidebarKey) => void;
  ArrowRightIcon: Icon;
}

function AnalysisTabContent({ data, trend, supplierData, supplierLoading, qualitySummaries, qualityLoading, trendDays, t, onNavigate, ArrowRightIcon }: AnalysisTabContentProps) {
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

      {/* 提供者別解析問題テーブル (supplier-quality-summaries) */}
      {!qualityLoading && qualitySummaries !== null && (() => {
        const problemRows = qualitySummaries.filter(
          (s) => s.needsReviewCount > 0 || s.productIdUnresolvedCount > 0 || s.unitUnresolvedCount > 0
        );
        if (problemRows.length === 0) return null;

        type QualityRow = SupplierQualitySummary;
        const qualityColumns: DataTableColumn<QualityRow>[] = [
          {
            key: "supplierName",
            header: t("analysisRules.dashboard.analysisSupplierName"),
          },
          {
            key: "analysisCount",
            header: t("analysisRules.dashboard.analysisSupplierAnalysisCount"),
            width: "100px",
            renderCell: (row) => row.analysisCount.toLocaleString(),
          },
          {
            key: "productIdUnresolvedCount",
            header: t("analysisRules.dashboard.analysisSupplierPidUnresolved"),
            width: "120px",
            renderCell: (row) =>
              row.productIdUnresolvedCount > 0 ? (
                <Badge variant="danger">{row.productIdUnresolvedCount.toLocaleString()}</Badge>
              ) : (
                <span>{row.productIdUnresolvedCount.toLocaleString()}</span>
              ),
          },
          {
            key: "unitUnresolvedCount",
            header: t("analysisRules.dashboard.analysisSupplierUnitUnresolved"),
            width: "120px",
            renderCell: (row) =>
              row.unitUnresolvedCount > 0 ? (
                <Badge variant="warning">{row.unitUnresolvedCount.toLocaleString()}</Badge>
              ) : (
                <span>{row.unitUnresolvedCount.toLocaleString()}</span>
              ),
          },
          {
            key: "needsReviewCount",
            header: t("analysisRules.dashboard.analysisSupplierNeedsReview"),
            width: "100px",
            renderCell: (row) =>
              row.needsReviewCount > 0 ? (
                <Badge variant="warning">{row.needsReviewCount.toLocaleString()}</Badge>
              ) : (
                <span>{row.needsReviewCount.toLocaleString()}</span>
              ),
          },
        ];

        return (
          <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
            <div className="analysis-dashboard-section-title">
              {t("analysisRules.dashboard.analysisSupplierTitle")}
            </div>
            <DataTable<QualityRow>
              columns={qualityColumns}
              data={problemRows}
              rowKey={(row) => row.supplierId}
              density="compact"
              emptyState={t("analysisRules.dashboard.noData")}
            />
            <div className="analysis-dashboard-ctas">
              <button
                type="button"
                className="analysis-dashboard-cta-btn"
                onClick={() => onNavigate("needs-review")}
              >
                {t("analysisRules.dashboard.ctaNeedsReview")}
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
          </Card>
        );
      })()}

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
            {`${trendDays}${t("analysisRules.dashboard.trendTitle")}`}
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
  t: (key: string) => string;
}

function DistributionTabContent({ data, loading, error, t }: DistributionTabContentProps) {
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

  const STALE_DAYS = 7;

  const isLastResultFailed = (lastResult: string | null): boolean => {
    if (!lastResult) return false;
    const lower = lastResult.toLowerCase();
    return lower.includes("error") || lower.includes("fail");
  };

  const isLastResultOk = (lastResult: string | null): boolean => {
    if (!lastResult) return false;
    const lower = lastResult.toLowerCase();
    return lower === "ok" || lower === "success";
  };

  const isStale = (lastDistributedAt: string | null): boolean => {
    if (!lastDistributedAt) return false;
    const diffMs = Date.now() - new Date(lastDistributedAt).getTime();
    return diffMs > STALE_DAYS * 24 * 60 * 60 * 1000;
  };

  const hasDistributionProblem = (row: DistributionTarget): boolean => {
    if (!row.is_active) return false;
    if (isLastResultFailed(row.last_result)) return true;
    if (!row.last_distributed_at) return true;
    if (isStale(row.last_distributed_at)) return true;
    return false;
  };

  const distributionProblemCount = data.targets.filter(hasDistributionProblem).length;

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
      renderCell: (row) => {
        if (!row.last_distributed_at) {
          if (row.is_active) {
            return <Badge variant="danger">{t("analysisRules.dashboard.distributionNeverRun")}</Badge>;
          }
          return "-";
        }
        const formatted = new Date(row.last_distributed_at).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" });
        if (row.is_active && isStale(row.last_distributed_at)) {
          return <Badge variant="warning">{formatted}</Badge>;
        }
        return <>{formatted}</>;
      },
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
      renderCell: (row) => {
        const val = row.last_result;
        if (!val) return "-";
        if (isLastResultFailed(val)) {
          return <Badge variant="danger">{t("analysisRules.dashboard.distributionResultFailed")}</Badge>;
        }
        if (isLastResultOk(val)) {
          return <Badge variant="success">{t("analysisRules.dashboard.distributionResultSuccess")}</Badge>;
        }
        return <>{val}</>;
      },
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

  return (
    <>
      {/* 配信先問題バー */}
      {distributionProblemCount > 0 && (
        <div className="analysis-dashboard-problem-banner">
          <Badge variant="danger">
            {`${distributionProblemCount}${t("analysisRules.dashboard.distributionProblemsCount")}`}
          </Badge>
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
