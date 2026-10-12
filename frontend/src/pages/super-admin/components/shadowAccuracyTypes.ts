/**
 * 解析精度管理（新方式）: API レスポンスの型と共通定数。
 * API は backend/app/routers/tcg_shadow_accuracy.py（読み取り専用）。
 * 兆候の定義は backend/app/services/shadow_accuracy_signals.py が SSOT。
 */

export const SIGNAL_CODES = ["S1", "S2", "S3", "S4", "S5", "S6"] as const;
export type SignalCode = (typeof SIGNAL_CODES)[number];

/** 期間（日数）。0 は全期間。 */
export const PERIOD_DAYS = [7, 30, 0] as const;
export type PeriodDays = (typeof PERIOD_DAYS)[number];

export type SignalCounts = Record<SignalCode, number>;

export interface SummaryTotals {
  blocks: number;
  needs_review_count: number;
  auto_confirmed: number;
  auto_confirmed_ratio: number | null;
  matched: number;
  ambiguous: number;
  unmatched: number;
  price_fixed: number;
  quantity_fixed: number;
  sold_out: number;
  pre_order: number;
}

export interface SupplierSummaryRow {
  supplier_id: number | null;
  supplier_name: string | null;
  blocks: number;
  needs_review_count: number;
  needs_review_ratio: number | null;
  signals: SignalCounts;
}

export interface AccuracySummary {
  days: number;
  supplier_id: number | null;
  totals: SummaryTotals;
  signals: SignalCounts;
  conditions: { condition: string | null; blocks: number }[];
  by_supplier: SupplierSummaryRow[];
}

export interface AccuracyPostRow {
  job_id: string;
  run_id: string;
  supplier_id: number | null;
  supplier_name: string | null;
  posted_at: string | null;
  blocks: number;
  needs_review_count: number;
  signals: SignalCounts;
}

export interface AccuracyPostsResponse {
  items: AccuracyPostRow[];
  total: number;
  offset: number;
  limit: number;
}

export interface ReviewItemEntry {
  item: string | null;
  reason: string | null;
  candidates: { product_id: number; product_name: string | null }[];
}

export interface AccuracyBlock {
  id: string;
  block_index: number;
  line_start: number | null;
  line_end: number | null;
  heading_line_start: number | null;
  heading_line_end: number | null;
  raw_product_name: string | null;
  raw_price: string | null;
  raw_unit: string | null;
  raw_quantity: string | null;
  raw_state: string | null;
  raw_ship: string | null;
  raw_multi: string | null;
  product_id: number | null;
  product_name: string | null;
  product_mark: string | null;
  match_status: "matched" | "ambiguous" | "unmatched";
  needs_review: boolean;
  status: string | null;
  condition_canonical: string | null;
  price_normalized: number | null;
  quantity_normalized: number | null;
  ship_offer_type: string | null;
  ship_timing: string | null;
  exclusion: string | null;
  evidence: { basis?: string; price_qty?: { basis?: string; reasons?: string[] } } | null;
  review_items: ReviewItemEntry[];
  signals: Record<SignalCode, boolean>;
}

export interface AccuracyPostDetail {
  job_id: string;
  run: {
    id: string;
    prompt_key: string;
    engine_version: string;
    requested_model: string;
    status: string;
    started_at: string | null;
    finished_at: string | null;
  };
  supplier_id: number | null;
  supplier_name: string | null;
  posted_at: string | null;
  raw_text: string;
  blocks: AccuracyBlock[];
}

export interface PostFilters {
  needsReview: "" | "true" | "false";
  signal: "" | SignalCode;
}
