/**
 * ファネルダッシュボード API 薄い1枚
 * モック→実API 切替はこのファイルの MOCK_MODE 変更のみ
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

// TODO: 実API結線時は false に変更（または VITE_MOCK_FUNNEL_API=false を.envに追加）
const MOCK_MODE = (import.meta.env.VITE_MOCK_FUNNEL_API ?? "true") !== "false";

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

// ─── API 呼び出し ──────────────────────────────────────────────────────

export function getFunnel(month: string, scope?: "mine"): Promise<FunnelResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_FUNNEL);
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return api.get<FunnelResponse>(`/analytics/funnel?${params}`);
}

export function getRevenueSummary(month: string, scope?: "mine"): Promise<RevenueSummaryResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_REVENUE_SUMMARY);
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return api.get<RevenueSummaryResponse>(`/analytics/revenue-summary?${params}`);
}

export function getFollowUps(scope?: "mine"): Promise<FollowUpsResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_FOLLOW_UPS);
  const params = scope ? new URLSearchParams({ scope }) : new URLSearchParams();
  return api.get<FollowUpsResponse>(`/analytics/follow-ups?${params}`);
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
