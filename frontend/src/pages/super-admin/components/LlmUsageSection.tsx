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
  ComposedChart,
  BarChart,
  LineChart,
  Bar,
  Line,
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

interface LlmUsageDailyRequestsItem {
  date: string;
  attempts: number;
  completed: number;
  failed: number;
  success_rate: number | null;
}

interface LlmUsageDailyErrorItem {
  date: string;
  error_code: string;
  count: number;
}

interface LlmUsageDailyByModelItem {
  date: string;
  model: string;
  calls: number;
  prompt_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
}

interface LlmUsageResponse {
  total: LlmUsageTotal;
  by_purpose: LlmUsageByPurposeItem[];
  by_model: LlmUsageByModelItem[];
  daily: LlmUsageDailyItem[];
  daily_by_purpose: LlmUsageDailyByPurposeItem[];
  monthly_by_purpose: LlmUsageMonthlyByPurposeItem[];
  daily_requests: LlmUsageDailyRequestsItem[];
  daily_errors: LlmUsageDailyErrorItem[];
  daily_by_model: LlmUsageDailyByModelItem[];
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
// ADR-067: 新規 hex は追加しない。カレンダードメインの --cal-* を他ドメインから直接
// 参照すると、カレンダー側の配色変更がこのチャートを無言で巻き込んでしまうため、
// frontend/src/tokens.css に --chart-series-1〜7（--cal-* のエイリアス）を新設し、
// そちらを参照する（light/dark 両方定義済み）。
const PURPOSE_CHART_COLOR_VARS = [
  "var(--chart-series-1)",
  "var(--chart-series-2)",
  "var(--chart-series-3)",
  "var(--chart-series-4)",
  "var(--chart-series-5)",
  "var(--chart-series-6)",
  "var(--chart-series-7)",
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

function pivotErrorsByDate(rows: LlmUsageDailyErrorItem[]): PivotRow[] {
  const map = new Map<string, PivotRow>();
  for (const row of rows) {
    if (!map.has(row.date)) {
      map.set(row.date, { key: row.date });
    }
    const entry = map.get(row.date) as PivotRow;
    entry[row.error_code] = row.count;
  }
  return Array.from(map.values());
}

function uniqueInOrder(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    if (!seen.has(value)) {
      seen.add(value);
      result.push(value);
    }
  }
  return result;
}

function pivotByModel(
  rows: LlmUsageDailyByModelItem[],
  valueKey: "prompt_tokens" | "output_tokens" | "calls"
): PivotRow[] {
  const map = new Map<string, PivotRow>();
  for (const row of rows) {
    if (!map.has(row.date)) {
      map.set(row.date, { key: row.date });
    }
    const entry = map.get(row.date) as PivotRow;
    const value = row[valueKey];
    if (value !== null) {
      entry[row.model] = value;
    }
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

function formatSuccessRatePercent(value: number | null): string {
  if (value == null) return "";
  return `${(value * 100).toFixed(1)}%`;
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

  const errorCodeOrder = uniqueInOrder(data.daily_errors.map((row) => row.error_code));
  const dailyErrorsData = pivotErrorsByDate(data.daily_errors);
  const dailyRequestsData = [...data.daily_requests].sort((a, b) => a.date.localeCompare(b.date));

  const modelOrder = uniqueInOrder(data.daily_by_model.map((row) => row.model));
  const inputTokensByModelData = pivotByModel(data.daily_by_model, "prompt_tokens");
  const outputTokensByModelData = pivotByModel(data.daily_by_model, "output_tokens");
  const requestsByModelData = pivotByModel(data.daily_by_model, "calls");

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

      {/* 概要（LINE抽出）: Google AI Studio の使用状況ページを参考にした見せ方 */}
      <div className="analysis-dashboard-section-title">
        {t("analysisRules.dashboard.usage.health.title")}
      </div>
      <p className="analysis-dashboard-section-note">
        {t("analysisRules.dashboard.usage.health.note")}
      </p>
      <div className="analysis-dashboard-grid">
        <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.usage.health.requestsChartTitle")}
          </div>
          {dailyRequestsData.length === 0 ? (
            <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
          ) : (
            <div className="analysis-dashboard-chart">
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={dailyRequestsData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis yAxisId="attempts" fontSize={12} allowDecimals={false} />
                  <YAxis
                    yAxisId="successRate"
                    orientation="right"
                    domain={[0, 100]}
                    tickFormatter={(value: number) => `${value}%`}
                    fontSize={12}
                  />
                  <Tooltip
                    formatter={(value, name) =>
                      name === t("analysisRules.dashboard.usage.health.successRateLabel")
                        ? [formatSuccessRatePercent(Number(value) / 100), name]
                        : [Number(value).toLocaleString(), name]
                    }
                  />
                  <Legend />
                  <Bar
                    yAxisId="attempts"
                    dataKey="attempts"
                    name={t("analysisRules.dashboard.usage.health.attemptsLabel")}
                    fill="var(--chart-series-1)"
                  />
                  <Line
                    yAxisId="successRate"
                    type="monotone"
                    dataKey={(row: LlmUsageDailyRequestsItem) =>
                      row.success_rate == null ? null : row.success_rate * 100
                    }
                    name={t("analysisRules.dashboard.usage.health.successRateLabel")}
                    stroke="var(--color-success)"
                    connectNulls={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
          <div className="analysis-dashboard-section-title">
            {t("analysisRules.dashboard.usage.health.errorsChartTitle")}
          </div>
          {dailyErrorsData.length === 0 ? (
            <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
          ) : (
            <div className="analysis-dashboard-chart">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={dailyErrorsData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="key" fontSize={12} />
                  <YAxis fontSize={12} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  {errorCodeOrder.map((errorCode, index) => (
                    <Bar
                      key={errorCode}
                      dataKey={errorCode}
                      name={errorCode}
                      stackId="errors"
                      fill={PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      {/* モデル別（トークン・リクエスト数の日次推移） */}
      <div className="analysis-dashboard-section-title">
        {t("analysisRules.dashboard.usage.health.modelTrendTitle")}
      </div>
      {modelOrder.length === 0 ? (
        <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
      ) : (
        <div className="analysis-dashboard-grid">
          <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
            <div className="analysis-dashboard-section-title">
              {t("analysisRules.dashboard.usage.health.inputTokensChartTitle")}
            </div>
            <div className="analysis-dashboard-chart">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={inputTokensByModelData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="key" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Legend />
                  {modelOrder.map((model, index) => (
                    <Line
                      key={model}
                      type="monotone"
                      dataKey={model}
                      name={model}
                      stroke={PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length]}
                      connectNulls={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
            <div className="analysis-dashboard-section-title">
              {t("analysisRules.dashboard.usage.health.outputTokensChartTitle")}
            </div>
            <div className="analysis-dashboard-chart">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={outputTokensByModelData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="key" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Legend />
                  {modelOrder.map((model, index) => (
                    <Line
                      key={model}
                      type="monotone"
                      dataKey={model}
                      name={model}
                      stroke={PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length]}
                      connectNulls={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card variant="container" density="compact" className="analysis-dashboard-chart-card">
            <div className="analysis-dashboard-section-title">
              {t("analysisRules.dashboard.usage.health.requestsByModelChartTitle")}
            </div>
            <div className="analysis-dashboard-chart">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={requestsByModelData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="key" fontSize={12} />
                  <YAxis fontSize={12} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  {modelOrder.map((model, index) => (
                    <Line
                      key={model}
                      type="monotone"
                      dataKey={model}
                      name={model}
                      stroke={PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length]}
                      connectNulls={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
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
