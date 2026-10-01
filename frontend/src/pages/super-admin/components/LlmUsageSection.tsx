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
import "./LlmUsageSection.css";

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

/**
 * 為替レート SSOT（ADR-148: public.app_fx_rates）の読み取りレスポンス。
 * GET /fx-rates/{currency}（backend/app/routers/fx_rate_admin.py）。
 * frontend/src/pages/super-admin/FxRatePage.tsx と同形。共有クライアントは存在しないため
 * 既存パターン（各ページで api.get を直接呼ぶ）を踏襲する。
 */
interface FxRate {
  currency: string;
  rate_jpy: number;
  fetched_at: string;
  updated_at: string;
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

// チャート装飾（Google AI Studio の使用状況ページを見せ方の参考・数値主張なし）。
// ADR-067: 数値そのものはトークンではないため、recharts の数値 props として
// 直接使用する（AnalysisDashboardPanel.tsx の strokeWidth={2} 等と同じ前例）。
const CHART_HEIGHT = 240;
const MODEL_CHART_HEIGHT = 200;
const AXIS_TICK_FONT_SIZE = 12;
const BAR_RADIUS: [number, number, number, number] = [4, 4, 0, 0];
const BAR_SIZE = 24;
const LINE_STROKE_WIDTH = 2;
const LAST_POINT_DOT_RADIUS = 4;
const ACTIVE_DOT_RADIUS = 5;
const LEGEND_ICON_SIZE = 8;

const GRID_STROKE_VAR = "var(--border)";
const AXIS_TICK_FILL_VAR = "var(--text-muted)";

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

/** 円表示用フォーマッタ（ADR-148: USD→JPY 換算後の値を整形する）。 */
function makeJpyFormatter(language: string): (value: number | null, t: (key: string) => string) => string {
  const formatter = new Intl.NumberFormat(language, {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  });
  return (value, t) => (value == null ? t("analysisRules.dashboard.usage.notReported") : formatter.format(value));
}

/** コストチャート Y 軸の桁短縮表示（単位付き。例: ¥500, ¥1.2K / $1.2K）。 */
function makeCompactCurrencyFormatter(language: string, currency: "JPY" | "USD"): (value: number) => string {
  const formatter = new Intl.NumberFormat(language, {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 1,
  });
  return (value) => formatter.format(value);
}

/** USD → JPY 換算（ADR-148 SSOT: public.app_fx_rates.rate_jpy を使用）。変換ロジックはここ一箇所に集約する。 */
function toJpy(usd: number, rateJpy: number): number {
  return usd * rateJpy;
}

/** fetched_at（UTC ISO文字列）を JST 表示に整形する（他ページと同じ Asia/Tokyo 固定の既存パターンを踏襲）。 */
function formatFetchedAtJst(isoString: string, language: string): string {
  return new Date(isoString).toLocaleString(language, {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function purposeLabel(purpose: string, t: (key: string) => string): string {
  if (!KNOWN_PURPOSES.includes(purpose)) return purpose;
  return t(`analysisRules.dashboard.usage.purpose.${purpose}`);
}

function formatSuccessRatePercent(value: number | null): string {
  if (value == null) return "";
  return `${(value * 100).toFixed(1)}%`;
}

/** 概要カードの成功率表示。NULL（記録なし）は notReported にフォールバックする。 */
function formatSuccessRateOrNotReported(value: number | null, t: (key: string) => string): string {
  if (value == null) return t("analysisRules.dashboard.usage.notReported");
  return `${(value * 100).toFixed(1)}%`;
}

/** Y軸の数値を桁短縮表示する（例: 29.8M）。ツールチップは formatNumber 等でフル桁を維持する。 */
export function formatCompactNumber(value: number, language: string): string {
  return new Intl.NumberFormat(language, { notation: "compact" }).format(value);
}

/** daily_requests の completed/failed を合算し、成功率とエラー件数を算出する。 */
function summarizeDailyRequests(rows: LlmUsageDailyRequestsItem[]): {
  successRate: number | null;
  errorCount: number;
} {
  const totals = rows.reduce(
    (acc, row) => ({
      completed: acc.completed + row.completed,
      failed: acc.failed + row.failed,
    }),
    { completed: 0, failed: 0 }
  );
  const denominator = totals.completed + totals.failed;
  return {
    successRate: denominator === 0 ? null : totals.completed / denominator,
    errorCount: totals.failed,
  };
}

/** 折れ線の最終点だけに丸いドットを描く dot レンダラー（ホバー時は activeDot が効く）。 */
function renderLastPointDot(dataLength: number, color: string) {
  return (props: { cx?: number; cy?: number; index?: number }) => {
    if (props.index !== dataLength - 1 || props.cx == null || props.cy == null) {
      return <></>;
    }
    return <circle cx={props.cx} cy={props.cy} r={LAST_POINT_DOT_RADIUS} fill={color} stroke="none" />;
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// コンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function LlmUsageSection({ days, t }: LlmUsageSectionProps) {
  const [data, setData] = useState<LlmUsageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fxRate, setFxRate] = useState<FxRate | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<LlmUsageResponse>(`/tcg/analysis-dashboard/llm-usage?days=${days}`),
      // 為替レートは失敗しても本体データの表示は止めない（ADR-148: 読み取りは全ユーザー可）。
      // 失敗・未取得時は呼び出し側で USD 表示へフォールバックする。
      api.get<FxRate>("/fx-rates/USD").catch(() => null),
    ])
      .then(([res, fx]) => {
        setData(res);
        setFxRate(fx != null && typeof fx.rate_jpy === "number" ? fx : null);
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
  const compactTick = (value: number) => formatCompactNumber(value, i18n.language);

  // ADR-148: USD→JPY 換算（1箇所に集約）。レート未取得時は null のまま USD 表示にフォールバックする。
  const costRate = fxRate != null ? fxRate.rate_jpy : null;
  const formatJpy = makeJpyFormatter(i18n.language);
  /** 生の USD 値（API レスポンス）を表示用文字列にする唯一のヘルパー。全コスト表示箇所から呼ぶ。 */
  const formatCost = (usd: number | null): string =>
    costRate == null ? formatCurrency(usd, t) : formatJpy(usd == null ? null : toJpy(usd, costRate), t);
  /** 既に換算済みの値（チャート用に事前変換したデータ）を表示用文字列にする。 */
  const formatConvertedCost = (value: number): string =>
    costRate == null ? formatCurrency(value, t) : formatJpy(value, t);
  const costTick = makeCompactCurrencyFormatter(i18n.language, costRate == null ? "USD" : "JPY");
  const convertCost = (usd: number | null): number | null =>
    costRate == null || usd == null ? usd : toJpy(usd, costRate);

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
      renderCell: (row) => formatCost(row.cost_usd),
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
      renderCell: (row) => formatCost(row.cost_usd),
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
      renderCell: (row) => formatCost(row.cost_usd),
    },
  ];

  const purposeOrder = data.by_purpose.map((row) => row.purpose);
  // チャートに渡す前に USD→JPY 換算を済ませる（pivotByPurpose は通貨を意識しない汎用関数のまま維持）。
  const dailyByPurposeConverted = data.daily_by_purpose.map((row) => ({ ...row, cost_usd: convertCost(row.cost_usd) }));
  const monthlyByPurposeConverted = data.monthly_by_purpose.map((row) => ({ ...row, cost_usd: convertCost(row.cost_usd) }));
  const dailyByPurposeData = pivotByPurpose(dailyByPurposeConverted, (row) => row.date);
  const monthlyByPurposeData = pivotByPurpose(monthlyByPurposeConverted, (row) => row.month);
  const formatChartCurrency = (value: number) => formatConvertedCost(value);

  const errorCodeOrder = uniqueInOrder(data.daily_errors.map((row) => row.error_code));
  const dailyErrorsData = pivotErrorsByDate(data.daily_errors);
  const dailyRequestsData = [...data.daily_requests].sort((a, b) => a.date.localeCompare(b.date));

  const modelOrder = uniqueInOrder(data.daily_by_model.map((row) => row.model));
  const inputTokensByModelData = pivotByModel(data.daily_by_model, "prompt_tokens");
  const outputTokensByModelData = pivotByModel(data.daily_by_model, "output_tokens");
  const requestsByModelData = pivotByModel(data.daily_by_model, "calls");

  const { successRate, errorCount } = summarizeDailyRequests(data.daily_requests);

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

      {/* サマリーカード: 主要指標を1枚に集約（Google AI Studio の使用状況ページを見せ方の参考） */}
      <Card variant="container" density="compact" className="llm-usage-summary">
        <div className="llm-usage-summary__hero">
          <span className="llm-usage-summary__hero-label">
            {t("analysisRules.dashboard.usage.summary.costLabel")}
          </span>
          <span className="llm-usage-summary__hero-value">
            {formatCost(data.total.cost_usd)}
          </span>
        </div>
        <div className="llm-usage-summary__stats">
          <div className="llm-usage-summary__stat">
            <span className="llm-usage-summary__stat-label">
              {t("analysisRules.dashboard.usage.summary.callsLabel")}
            </span>
            <span className="llm-usage-summary__stat-value">
              {data.total.calls.toLocaleString()}
            </span>
          </div>
          <div className="llm-usage-summary__stat">
            <span className="llm-usage-summary__stat-label">
              {t("analysisRules.dashboard.usage.summary.inputLabel")}
            </span>
            <span className="llm-usage-summary__stat-value">
              {formatNumber(data.total.prompt_tokens, t)}
            </span>
          </div>
          <div className="llm-usage-summary__stat">
            <span className="llm-usage-summary__stat-label">
              {t("analysisRules.dashboard.usage.summary.outputLabel")}
            </span>
            <span className="llm-usage-summary__stat-value">
              {formatOutputTokens(data.total.candidates_tokens, data.total.thoughts_tokens, t)}
            </span>
          </div>
          <div className="llm-usage-summary__stat">
            <span className="llm-usage-summary__stat-label">
              {t("analysisRules.dashboard.usage.summary.successRateLabel")}
            </span>
            <span className="llm-usage-summary__stat-value">
              {formatSuccessRateOrNotReported(successRate, t)}
            </span>
          </div>
          <div className="llm-usage-summary__stat">
            <span className="llm-usage-summary__stat-label">
              {t("analysisRules.dashboard.usage.summary.errorCountLabel")}
            </span>
            <span className="llm-usage-summary__stat-value">
              {errorCount.toLocaleString()}
            </span>
          </div>
        </div>
      </Card>

      {/* ADR-148: 円換算レートの出典を明示（過去日も現在レートで一律換算している旨の注記を含む） */}
      {costRate != null && fxRate != null ? (
        <p className="analysis-dashboard-section-note" data-testid="llm-usage-fx-note">
          {t("analysisRules.dashboard.usage.fx.note", {
            rate: fxRate.rate_jpy.toLocaleString(i18n.language, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 4,
            }),
            fetchedAt: formatFetchedAtJst(fxRate.fetched_at, i18n.language),
          })}
        </p>
      ) : (
        <p className="analysis-dashboard-section-note" data-testid="llm-usage-fx-fallback-note">
          {t("analysisRules.dashboard.usage.fx.fallbackNote")}
        </p>
      )}

      {/* 概要（LINE抽出）/ モデル別 / 費用 を1枚のカードに集約。カード見出しは行1（概要）のタイトルを兼ねる */}
      <Card variant="container" density="compact" className="llm-usage-charts">
        <div className="analysis-dashboard-section-title">
          {t("analysisRules.dashboard.usage.health.title")}
        </div>

        {/* 行1: 概要（LINE抽出）: Google AI Studio の使用状況ページを参考にした見せ方 */}
        <div className="llm-usage-charts__row">
          <p className="analysis-dashboard-section-note">
            {t("analysisRules.dashboard.usage.health.note")}
          </p>
          <div className="llm-usage-charts__grid">
            <div className="llm-usage-charts__item">
              <div className="llm-usage-charts__item-title">
                {t("analysisRules.dashboard.usage.health.requestsChartTitle")}
              </div>
              {dailyRequestsData.length === 0 ? (
                <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
              ) : (
                <div className="analysis-dashboard-chart llm-usage-chart">
                  <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                    <ComposedChart data={dailyRequestsData}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={GRID_STROKE_VAR} />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <YAxis
                        yAxisId="attempts"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                        allowDecimals={false}
                        tickFormatter={compactTick}
                      />
                      <YAxis
                        yAxisId="successRate"
                        orientation="right"
                        domain={[0, 100]}
                        tickFormatter={(value: number) => `${value}%`}
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <Tooltip
                        formatter={(value, name) =>
                          name === t("analysisRules.dashboard.usage.health.successRateLabel")
                            ? [formatSuccessRatePercent(Number(value) / 100), name]
                            : [Number(value).toLocaleString(), name]
                        }
                      />
                      <Legend verticalAlign="bottom" iconType="circle" iconSize={LEGEND_ICON_SIZE} />
                      <Bar
                        yAxisId="attempts"
                        dataKey="attempts"
                        name={t("analysisRules.dashboard.usage.health.attemptsLabel")}
                        fill="var(--chart-series-1)"
                        radius={BAR_RADIUS}
                        barSize={BAR_SIZE}
                      />
                      <Line
                        yAxisId="successRate"
                        type="monotone"
                        dataKey={(row: LlmUsageDailyRequestsItem) =>
                          row.success_rate == null ? null : row.success_rate * 100
                        }
                        name={t("analysisRules.dashboard.usage.health.successRateLabel")}
                        stroke="var(--color-success)"
                        strokeWidth={LINE_STROKE_WIDTH}
                        connectNulls={false}
                        dot={renderLastPointDot(dailyRequestsData.length, "var(--color-success)")}
                        activeDot={{ r: ACTIVE_DOT_RADIUS }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <div className="llm-usage-charts__item">
              <div className="llm-usage-charts__item-title">
                {t("analysisRules.dashboard.usage.health.errorsChartTitle")}
              </div>
              {dailyErrorsData.length === 0 ? (
                <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
              ) : (
                <div className="analysis-dashboard-chart llm-usage-chart">
                  <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                    <BarChart data={dailyErrorsData}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={GRID_STROKE_VAR} />
                      <XAxis
                        dataKey="key"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                        tickFormatter={compactTick}
                      />
                      <Tooltip />
                      <Legend verticalAlign="bottom" iconType="circle" iconSize={LEGEND_ICON_SIZE} />
                      {errorCodeOrder.map((errorCode, index) => (
                        <Bar
                          key={errorCode}
                          dataKey={errorCode}
                          name={errorCode}
                          stackId="errors"
                          fill={PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length]}
                          radius={BAR_RADIUS}
                          barSize={BAR_SIZE}
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 行2: モデル別（トークン・リクエスト数の日次推移） */}
        <div className="llm-usage-charts__row">
          <div className="llm-usage-charts__row-title">
            {t("analysisRules.dashboard.usage.health.modelTrendTitle")}
          </div>
          {modelOrder.length === 0 ? (
            <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
          ) : (
            <div className="llm-usage-charts__grid">
              <div className="llm-usage-charts__item">
                <div className="llm-usage-charts__item-title">
                  {t("analysisRules.dashboard.usage.health.inputTokensChartTitle")}
                </div>
                <div className="analysis-dashboard-chart llm-usage-chart">
                  <ResponsiveContainer width="100%" height={MODEL_CHART_HEIGHT}>
                    <LineChart data={inputTokensByModelData}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={GRID_STROKE_VAR} />
                      <XAxis
                        dataKey="key"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <YAxis
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                        tickFormatter={compactTick}
                      />
                      <Tooltip />
                      <Legend verticalAlign="bottom" iconType="circle" iconSize={LEGEND_ICON_SIZE} />
                      {modelOrder.map((model, index) => {
                        const color = PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length];
                        return (
                          <Line
                            key={model}
                            type="monotone"
                            dataKey={model}
                            name={model}
                            stroke={color}
                            strokeWidth={LINE_STROKE_WIDTH}
                            connectNulls={false}
                            dot={renderLastPointDot(inputTokensByModelData.length, color)}
                            activeDot={{ r: ACTIVE_DOT_RADIUS }}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="llm-usage-charts__item">
                <div className="llm-usage-charts__item-title">
                  {t("analysisRules.dashboard.usage.health.outputTokensChartTitle")}
                </div>
                <div className="analysis-dashboard-chart llm-usage-chart">
                  <ResponsiveContainer width="100%" height={MODEL_CHART_HEIGHT}>
                    <LineChart data={outputTokensByModelData}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={GRID_STROKE_VAR} />
                      <XAxis
                        dataKey="key"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <YAxis
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                        tickFormatter={compactTick}
                      />
                      <Tooltip />
                      <Legend verticalAlign="bottom" iconType="circle" iconSize={LEGEND_ICON_SIZE} />
                      {modelOrder.map((model, index) => {
                        const color = PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length];
                        return (
                          <Line
                            key={model}
                            type="monotone"
                            dataKey={model}
                            name={model}
                            stroke={color}
                            strokeWidth={LINE_STROKE_WIDTH}
                            connectNulls={false}
                            dot={renderLastPointDot(outputTokensByModelData.length, color)}
                            activeDot={{ r: ACTIVE_DOT_RADIUS }}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="llm-usage-charts__item">
                <div className="llm-usage-charts__item-title">
                  {t("analysisRules.dashboard.usage.health.requestsByModelChartTitle")}
                </div>
                <div className="analysis-dashboard-chart llm-usage-chart">
                  <ResponsiveContainer width="100%" height={MODEL_CHART_HEIGHT}>
                    <LineChart data={requestsByModelData}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={GRID_STROKE_VAR} />
                      <XAxis
                        dataKey="key"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                        tickFormatter={compactTick}
                      />
                      <Tooltip />
                      <Legend verticalAlign="bottom" iconType="circle" iconSize={LEGEND_ICON_SIZE} />
                      {modelOrder.map((model, index) => {
                        const color = PURPOSE_CHART_COLOR_VARS[index % PURPOSE_CHART_COLOR_VARS.length];
                        return (
                          <Line
                            key={model}
                            type="monotone"
                            dataKey={model}
                            name={model}
                            stroke={color}
                            strokeWidth={LINE_STROKE_WIDTH}
                            connectNulls={false}
                            dot={renderLastPointDot(requestsByModelData.length, color)}
                            activeDot={{ r: ACTIVE_DOT_RADIUS }}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 行3: 費用（使いみち別・積み上げ棒） */}
        <div className="llm-usage-charts__row">
          <div className="llm-usage-charts__row-title">
            {t("analysisRules.dashboard.usage.costRowTitle")}
          </div>
          <div className="llm-usage-charts__grid">
            <div className="llm-usage-charts__item">
              <div className="llm-usage-charts__item-title">
                {t("analysisRules.dashboard.usage.dailyByPurposeChartTitle")}
              </div>
              {dailyByPurposeData.length === 0 ? (
                <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
              ) : (
                <div className="analysis-dashboard-chart llm-usage-chart">
                  <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                    <BarChart data={dailyByPurposeData}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={GRID_STROKE_VAR} />
                      <XAxis
                        dataKey="key"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <YAxis
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                        tickFormatter={costTick}
                      />
                      <Tooltip formatter={(value) => formatChartCurrency(Number(value))} />
                      <Legend
                        verticalAlign="bottom"
                        iconType="circle"
                        iconSize={LEGEND_ICON_SIZE}
                        formatter={(purpose) => purposeLabel(String(purpose), t)}
                      />
                      {purposeOrder.map((purpose) => (
                        <Bar
                          key={purpose}
                          dataKey={purpose}
                          name={purpose}
                          stackId="cost"
                          fill={purposeColor(purpose, purposeOrder)}
                          radius={BAR_RADIUS}
                          barSize={BAR_SIZE}
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <div className="llm-usage-charts__item">
              <div className="llm-usage-charts__item-title">
                {t("analysisRules.dashboard.usage.monthlyByPurposeChartTitle")}
              </div>
              {monthlyByPurposeData.length === 0 ? (
                <p className="analysis-dashboard-empty">{t("analysisRules.dashboard.noData")}</p>
              ) : (
                <div className="analysis-dashboard-chart llm-usage-chart">
                  <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                    <BarChart data={monthlyByPurposeData}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={GRID_STROKE_VAR} />
                      <XAxis
                        dataKey="key"
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                      />
                      <YAxis
                        tick={{ fontSize: AXIS_TICK_FONT_SIZE, fill: AXIS_TICK_FILL_VAR }}
                        tickFormatter={costTick}
                      />
                      <Tooltip formatter={(value) => formatChartCurrency(Number(value))} />
                      <Legend
                        verticalAlign="bottom"
                        iconType="circle"
                        iconSize={LEGEND_ICON_SIZE}
                        formatter={(purpose) => purposeLabel(String(purpose), t)}
                      />
                      {purposeOrder.map((purpose) => (
                        <Bar
                          key={purpose}
                          dataKey={purpose}
                          name={purpose}
                          stackId="cost"
                          fill={purposeColor(purpose, purposeOrder)}
                          radius={BAR_RADIUS}
                          barSize={BAR_SIZE}
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        </div>
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
