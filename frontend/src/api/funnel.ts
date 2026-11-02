/**
 * ファネルダッシュボード API 薄い1枚
 * 表示モードは VITE_FUNNEL_DASHBOARD 1本で制御:
 *   unset / false → "off"  : セクション自体を非レンダリング（本番デフォルト）
 *   "mock"        → "mock" : モックフィクスチャを返す（開発・E2E）
 *   "live"        → "live" : 実APIを呼ぶ（バックエンドPR2/3マージ後）
 * API contract: docs/handoff/funnel-dashboard-stage1/api-contract.md
 */

import { api } from "../lib/api";
import {
  MOCK_FUNNEL,
  MOCK_REVENUE_SUMMARY,
  MOCK_FOLLOW_UPS,
  MOCK_CHANNELS,
  MOCK_REASONS_WON,
  MOCK_REASONS_LOST,
} from "../mocks/funnelFixtures";

type FunnelMode = "off" | "mock" | "live";

export const FUNNEL_MODE: FunnelMode = (() => {
  const v = import.meta.env.VITE_FUNNEL_DASHBOARD;
  if (v === "mock" || v === "live") return v;
  return "off";
})();

const MOCK_MODE = FUNNEL_MODE === "mock";
export const FUNNEL_MOCK = MOCK_MODE;

// ─── 型定義（API contract と同形） ────────────────────────────────────

export interface FunnelResponse {
  month: string;
  month_elapsed_pct: number;
  leads: { target: number; actual: number };
  conversion: { target_rate: number; actual_rate: number; converted: number };
  active: { count: number; amount: number; coverage_pct_of_remaining_target: number };
  closed: { won_target: number; won: number; won_rate: number; lost: number };
}

export interface RevenueSummaryResponse {
  revenue: { target: number; actual: number; pace: "ahead" | "on_track" | "behind" };
  split: { new: number; repeat: number };
  new_customers: { target: number; actual: number };
  active_existing_customers: number;
  gross_margin: { amount: number; uncosted_orders: number };
}

export interface FollowUpItem {
  customer_id: number;
  name: string;
  segment: "order_stopped" | "no_repeat_after_first" | "won_no_order";
  days: number;
  last_order_at: string | null;
  last_contact_at: string | null;
  assignee: string;
}

export interface FollowUpsResponse {
  items: FollowUpItem[];
}

export interface ChannelRow {
  initiative: string;
  channel: string;
  leads: number;
  conversion_rate: number;
  win_rate: number;
  avg_order_value: number;
  gross_margin: number;
}

export interface ChannelsResponse {
  rows: ChannelRow[];
}

export interface ReasonItem {
  label: string;
  primary_count: number;
  secondary_count: number;
}

export interface ReasonMemo {
  deal_id: number;
  primary_label: string;
  memo: string;
  closed_at: string;
}

export interface ReasonsResponse {
  reasons: ReasonItem[];
  memos: ReasonMemo[];
}

export interface WeeklyAdvisorReason {
  last_order_at: string | null;
  last_contact_at: string | null;
  avg_interval_days: number | null;
  days_since_last_order: number | null;
  days_since_contact: number | null;
  pace_score: number | null;
  contact_score: number | null;
  decline_score: number | null;
  total_score: number | null;
  current_order_count: number | null;
  previous_order_count: number | null;
  current_revenue: number | null;
  previous_revenue: number | null;
}

export interface WeeklyAdvisorAction {
  rank: number;
  type: "reorder" | "churn_risk" | "comm_low";
  company_id: number;
  company_name: string;
  lead_id: number | null;
  score: number;
  expected_value: number;
  suggested_action: string;
  reason: WeeklyAdvisorReason;
}

export interface WeeklyAdvisorResponse {
  period: string;
  scope: string;
  stale_days: number;
  actions: WeeklyAdvisorAction[];
}

export interface PriorityProspectAxisBreakdown {
  axis: string;
  value: string;
  n: number;
  conversions: number;
  raw_rate: number;
  smoothed_rate: number;
  low_sample: boolean;
}

export interface PriorityProspectItem {
  lead_id: number;
  type: "priority_prospect";
  ease_pct: number;
  monthly_forecast: number;
  rank_score: number;
  score: number;
  expected_value: number;
  suggested_action: string;
  axis_breakdown: PriorityProspectAxisBreakdown[];
  low_sample_flags: string[];
}

export interface PriorityProspectsResponse {
  scope: string;
  items: PriorityProspectItem[];
}

// ─── API 呼び出し ──────────────────────────────────────────────────────

export function funnelPath(month: string, scope?: "mine"): string {
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return `/analytics/funnel?${params}`;
}

export function revenueSummaryPath(month: string, scope?: "mine"): string {
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return `/analytics/revenue-summary?${params}`;
}

export function followUpsPath(scope?: "mine"): string {
  const params = scope ? new URLSearchParams({ scope }) : new URLSearchParams();
  return `/analytics/follow-ups?${params}`;
}

export const WEEKLY_ADVISOR_DEFENSIVE_PATH = `/analytics/weekly-advisor-defensive?${new URLSearchParams({ scope: "mine", period: "3m" })}`;

export const PRIORITY_PROSPECTS_PATH = `/analytics/priority-prospects?${new URLSearchParams({ scope: "mine" })}`;

export const LEAD_CONVERSION_FACTORS_PATH = "/analytics/lead-conversion-factors";

export function getFunnel(month: string, scope?: "mine"): Promise<FunnelResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_FUNNEL);
  return api.get<FunnelResponse>(funnelPath(month, scope));
}

export function getRevenueSummary(month: string, scope?: "mine"): Promise<RevenueSummaryResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_REVENUE_SUMMARY);
  return api.get<RevenueSummaryResponse>(revenueSummaryPath(month, scope));
}

export function getFollowUps(scope?: "mine"): Promise<FollowUpsResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_FOLLOW_UPS);
  return api.get<FollowUpsResponse>(followUpsPath(scope));
}

export function getChannels(month: string, scope?: "mine"): Promise<ChannelsResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_CHANNELS);
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return api.get<ChannelsResponse>(`/analytics/channels?${params}`);
}

export function getReasons(
  type: "won" | "lost",
  month: string,
): Promise<ReasonsResponse> {
  if (MOCK_MODE)
    return Promise.resolve(type === "won" ? MOCK_REASONS_WON : MOCK_REASONS_LOST);
  return api.get<ReasonsResponse>(`/analytics/reasons?type=${type}&month=${month}`);
}

export interface LeadConversionFactorItem {
  key: string;
  odds_ratio: number | null;
  ci_low: number | null;
  ci_high: number | null;
  significant: boolean;
  computable: boolean;
}

export interface LeadConversionFactorsResponse {
  status: "ok" | "insufficient" | "not_computable";
  included_count: number;
  won_count: number;
  lost_count: number;
  required_per_item: number;
  item_count: number;
  excluded: {
    by_status: number;
    other_values: number;
    no_inbound: number;
    no_outbound: number;
    no_reply_pair: number;
    no_sales_form: number;
    missing_scale_or_type: number;
  };
  items: LeadConversionFactorItem[];
}
