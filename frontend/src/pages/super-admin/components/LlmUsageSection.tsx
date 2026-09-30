/**
 * LlmUsageSection — LLM 使用量台帳（ADR-1004: public.llm_usage_events）タブ
 *
 * API: GET /tcg/analysis-dashboard/llm-usage?days=N
 *
 * ADR-027: 全UI文字列は t("key") 経由
 * ADR-067: 色・サイズはデザイントークンのみ
 * ADR-144: Card / DataTable 金型のみ使用
 */
import { useEffect, useState } from "react";
import i18n from "../../../i18n";
import { api } from "../../../lib/api";
import { Card } from "../../../components/Card";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

interface LlmUsageTotal {
  calls: number;
  prompt_tokens: number | null;
  cached_content_tokens: number | null;
  candidates_tokens: number | null;
  thoughts_tokens: number | null;
  tool_use_prompt_tokens: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
}

interface LlmUsageByPurposeItem {
  purpose: string;
  calls: number;
  prompt_tokens: number | null;
  cached_content_tokens: number | null;
  candidates_tokens: number | null;
  thoughts_tokens: number | null;
  tool_use_prompt_tokens: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
}

interface LlmUsageByModelItem {
  model: string;
  calls: number;
  cost_usd: number | null;
}

interface LlmUsageDailyItem {
  date: string;
  calls: number;
  cost_usd: number | null;
  prompt_tokens: number | null;
  candidates_tokens: number | null;
  thoughts_tokens: number | null;
}

interface LlmUsageResponse {
  total: LlmUsageTotal;
  by_purpose: LlmUsageByPurposeItem[];
  by_model: LlmUsageByModelItem[];
  daily: LlmUsageDailyItem[];
}

// ──────────────────────────────────────────────────────────────────────────────
// 定数
// ──────────────────────────────────────────────────────────────────────────────

const KNOWN_PURPOSES = [
  "line_extraction",
  "line_extraction_shadow",
  "inventory_parse_fallback",
  "translation_inbound",
  "translation_inbound_escalation",
  "translation_outbound",
];

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface LlmUsageSectionProps {
  days: number;
  t: (key: string, options?: Record<string, unknown>) => string;
}

// ──────────────────────────────────────────────────────────────────────────────
// ヘルパー
// ──────────────────────────────────────────────────────────────────────────────

function formatNumber(value: number | null, t: (key: string) => string): string {
  if (value == null) return t("analysisRules.dashboard.usage.notReported");
  return value.toLocaleString();
}

function formatOutputTokens(
  candidates: number | null,
  thoughts: number | null,
  t: (key: string) => string
): string {
  if (candidates == null && thoughts == null) {
    return t("analysisRules.dashboard.usage.notReported");
  }
  return ((candidates ?? 0) + (thoughts ?? 0)).toLocaleString();
}

function makeCurrencyFormatter(language: string): (value: number | null, t: (key: string) => string) => string {
  const formatter = new Intl.NumberFormat(language, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  });
  return (value, t) => (value == null ? t("analysisRules.dashboard.usage.notReported") : formatter.format(value));
}

function purposeLabel(purpose: string, t: (key: string) => string): string {
  if (!KNOWN_PURPOSES.includes(purpose)) return purpose;
  return t(`analysisRules.dashboard.usage.purpose.${purpose}`);
}

// ──────────────────────────────────────────────────────────────────────────────
// コンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function LlmUsageSection({ days, t }: LlmUsageSectionProps) {
  const [data, setData] = useState<LlmUsageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .get<LlmUsageResponse>(`/tcg/analysis-dashboard/llm-usage?days=${days}`)
      .then((res) => {
        setData(res);
      })
      .catch(() => {
        setError(t("analysisRules.dashboard.fetchError"));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [days, t]);

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

  const formatCurrency = makeCurrencyFormatter(i18n.language);

  const byPurposeColumns: DataTableColumn<LlmUsageByPurposeItem>[] = [
    {
      key: "purpose",
      header: t("analysisRules.dashboard.usage.colPurpose"),
      renderCell: (row) => purposeLabel(row.purpose, t),
    },
    {
      key: "calls",
      header: t("analysisRules.dashboard.usage.colCalls"),
      width: "80px",
      renderCell: (row) => row.calls.toLocaleString(),
    },
    {
      key: "prompt_tokens",
      header: t("analysisRules.dashboard.usage.colInput"),
      width: "100px",
      renderCell: (row) => formatNumber(row.prompt_tokens, t),
    },
    {
      key: "cached_content_tokens",
      header: t("analysisRules.dashboard.usage.colCached"),
      width: "100px",
      renderCell: (row) => formatNumber(row.cached_content_tokens, t),
    },
    {
      key: "candidates_tokens",
      header: t("analysisRules.dashboard.usage.colOutput"),
      width: "100px",
      renderCell: (row) => formatNumber(row.candidates_tokens, t),
    },
    {
      key: "thoughts_tokens",
      header: t("analysisRules.dashboard.usage.colThoughts"),
      width: "100px",
      renderCell: (row) => formatNumber(row.thoughts_tokens, t),
    },
    {
      key: "tool_use_prompt_tokens",
      header: t("analysisRules.dashboard.usage.colTool"),
      width: "100px",
      renderCell: (row) => formatNumber(row.tool_use_prompt_tokens, t),
    },
    {
      key: "total_tokens",
      header: t("analysisRules.dashboard.usage.colTotal"),
      width: "100px",
      renderCell: (row) => formatNumber(row.total_tokens, t),
    },
    {
      key: "cost_usd",
      header: t("analysisRules.dashboard.usage.colCost"),
      width: "120px",
      renderCell: (row) => formatCurrency(row.cost_usd, t),
    },
  ];

  const dailyColumns: DataTableColumn<LlmUsageDailyItem>[] = [
    {
      key: "date",
      header: t("analysisRules.dashboard.usage.colDate"),
      width: "120px",
    },
    {
      key: "calls",
      header: t("analysisRules.dashboard.usage.colCalls"),
      width: "80px",
      renderCell: (row) => row.calls.toLocaleString(),
    },
    {
      key: "prompt_tokens",
      header: t("analysisRules.dashboard.usage.colInput"),
      width: "100px",
      renderCell: (row) => formatNumber(row.prompt_tokens, t),
    },
    {
      key: "output",
      header: t("analysisRules.dashboard.usage.colOutput"),
      width: "100px",
      renderCell: (row) => formatOutputTokens(row.candidates_tokens, row.thoughts_tokens, t),
    },
    {
      key: "thoughts_tokens",
      header: t("analysisRules.dashboard.usage.colThoughts"),
      width: "100px",
      renderCell: (row) => formatNumber(row.thoughts_tokens, t),
    },
    {
      key: "cost_usd",
      header: t("analysisRules.dashboard.usage.colCost"),
      width: "120px",
      renderCell: (row) => formatCurrency(row.cost_usd, t),
    },
  ];

  const byModelColumns: DataTableColumn<LlmUsageByModelItem>[] = [
    {
      key: "model",
      header: t("analysisRules.dashboard.usage.colModel"),
    },
    {
      key: "calls",
      header: t("analysisRules.dashboard.usage.colCalls"),
      width: "80px",
      renderCell: (row) => row.calls.toLocaleString(),
    },
    {
      key: "cost_usd",
      header: t("analysisRules.dashboard.usage.colCost"),
      width: "120px",
      renderCell: (row) => formatCurrency(row.cost_usd, t),
    },
  ];

  return (
    <div className="analysis-dashboard-existing-section">
      <p className="analysis-dashboard-section-note">
        {t("analysisRules.dashboard.usage.note")}
      </p>

      {/* 段1: 4枚のメトリクスカード */}
      <div className="analysis-dashboard-metrics">
        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.usage.metricCost")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {formatCurrency(data.total.cost_usd, t)}
          </div>
        </Card>
        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.usage.metricCalls")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {data.total.calls.toLocaleString()}
          </div>
        </Card>
        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.usage.metricInput")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {formatNumber(data.total.prompt_tokens, t)}
          </div>
        </Card>
        <Card variant="metric" density="compact">
          <div className="analysis-dashboard-metric-label">
            {t("analysisRules.dashboard.usage.metricOutput")}
          </div>
          <div className="analysis-dashboard-metric-value">
            {formatOutputTokens(data.total.candidates_tokens, data.total.thoughts_tokens, t)}
          </div>
        </Card>
      </div>

      {/* 段2: 使いみち別 */}
      <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.usage.byPurposeTitle")}
        </div>
        <DataTable<LlmUsageByPurposeItem>
          columns={byPurposeColumns}
          data={data.by_purpose}
          rowKey={(row) => row.purpose}
          density="compact"
          emptyState={t("analysisRules.dashboard.noData")}
        />
      </Card>

      {/* 段3: 日別 */}
      <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.usage.dailyTitle")}
        </div>
        <DataTable<LlmUsageDailyItem>
          columns={dailyColumns}
          data={data.daily}
          rowKey={(row) => row.date}
          density="compact"
          emptyState={t("analysisRules.dashboard.noData")}
        />
      </Card>

      {/* 段4: モデル別 */}
      <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.usage.byModelTitle")}
        </div>
        <DataTable<LlmUsageByModelItem>
          columns={byModelColumns}
          data={data.by_model}
          rowKey={(row) => row.model}
          density="compact"
          emptyState={t("analysisRules.dashboard.noData")}
        />
      </Card>
    </div>
  );
}
