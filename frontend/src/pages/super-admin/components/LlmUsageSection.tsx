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
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
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
  computed_total_tokens: number | null;
  total_mismatch_calls: number;
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
  computed_total_tokens: number | null;
  total_mismatch_calls: number;
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

interface LlmUsageDailyByPurposeItem {
  date: string;
  purpose: string;
  cost_usd: number | null;
  calls: number;
}

interface LlmUsageMonthlyByPurposeItem {
  month: string;
  purpose: string;
  calls: number;
  cost_usd: number | null;
}

interface LlmUsageResponse {
  total: LlmUsageTotal;
  by_purpose: LlmUsageByPurposeItem[];
  by_model: LlmUsageByModelItem[];
  daily: LlmUsageDailyItem[];
  daily_by_purpose: LlmUsageDailyByPurposeItem[];
  monthly_by_purpose: LlmUsageMonthlyByPurposeItem[];
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

// 積み上げ棒グラフの使いみち別カラー。
// ADR-067: 新規 hex は追加しない。既存の分類用カラートークン（--cal-*、スケジュール
// カテゴリ用に light/dark 両方が定義済み）を流用する。
const PURPOSE_CHART_COLOR_VARS = [
  "var(--cal-personal)",
  "var(--cal-meeting)",
  "var(--cal-purchase)",
  "var(--cal-shipping)",
  "var(--cal-billing)",
  "var(--cal-release)",
  "var(--cal-holiday)",
];

function purposeColor(purpose: string, allPurposes: string[]): string {
  const index = allPurposes.indexOf(purpose);
  const safeIndex = index === -1 ? 0 : index % PURPOSE_CHART_COLOR_VARS.length;
  return PURPOSE_CHART_COLOR_VARS[safeIndex];
}

type PivotRow = { key: string } & Record<string, number | string>;

function pivotByPurpose<T extends { purpose: string; cost_usd: number | null }>(
  rows: T[],
  keyOf: (row: T) => string
): PivotRow[] {
  const map = new Map<string, PivotRow>();
  for (const row of rows) {
    const key = keyOf(row);
    if (!map.has(key)) {
      map.set(key, { key });
    }
    const entry = map.get(key) as PivotRow;
    entry[row.purpose] = row.cost_usd ?? 0;
  }
  return Array.from(map.values());
}

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
      key: "computed_total_tokens",
      header: t("analysisRules.dashboard.usage.colTotal"),
      width: "100px",
      renderCell: (row) => formatNumber(row.computed_total_tokens, t),
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

  const purposeOrder = data.by_purpose.map((row) => row.purpose);
  const dailyByPurposeData = pivotByPurpose(data.daily_by_purpose, (row) => row.date);
  const monthlyByPurposeData = pivotByPurpose(data.monthly_by_purpose, (row) => row.month);
  const formatChartCurrency = (value: number) => formatCurrency(value, t);

  return (
    <div className="analysis-dashboard-existing-section">
      <p className="analysis-dashboard-section-note">
        {t("analysisRules.dashboard.usage.note")}
      </p>
      {data.total.total_mismatch_calls > 0 && (
        <p className="analysis-dashboard-section-note">
          {t("analysisRules.dashboard.usage.totalMismatchNote", { count: data.total.total_mismatch_calls })}
        </p>
      )}

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

      {/* 日次の費用（使いみち別・積み上げ棒） */}
      <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.usage.dailyByPurposeChartTitle")}
        </div>
        {dailyByPurposeData.length === 0 ? (
          <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
        ) : (
          <div className="analysis-dashboard-chart">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={dailyByPurposeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="key" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip formatter={(value) => formatChartCurrency(Number(value))} />
                <Legend formatter={(purpose) => purposeLabel(String(purpose), t)} />
                {purposeOrder.map((purpose) => (
                  <Bar
                    key={purpose}
                    dataKey={purpose}
                    name={purpose}
                    stackId="cost"
                    fill={purposeColor(purpose, purposeOrder)}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* 月次の費用（使いみち別・積み上げ棒） */}
      <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.usage.monthlyByPurposeChartTitle")}
        </div>
        {monthlyByPurposeData.length === 0 ? (
          <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
        ) : (
          <div className="analysis-dashboard-chart">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={monthlyByPurposeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="key" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip formatter={(value) => formatChartCurrency(Number(value))} />
                <Legend formatter={(purpose) => purposeLabel(String(purpose), t)} />
                {purposeOrder.map((purpose) => (
                  <Bar
                    key={purpose}
                    dataKey={purpose}
                    name={purpose}
                    stackId="cost"
                    fill={purposeColor(purpose, purposeOrder)}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

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
