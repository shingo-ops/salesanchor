// buybackTypes.ts — 買取価格ページの型定義・定数

export interface BuybackProduct {
  shop_product_id: string;
  shop_code: string;
  product_name: string;
  card_game: string;
  product_type: string;
  price_s: number | null;
  price_a: number | null;
  price_am: number | null;
  price_b: number | null;
  price_c: number | null;
  last_seen_at: string | null;
  // マッチング結果
  product_code: string | null;
  product_name_ja: string | null;
  match_status: "auto" | "pending_review" | "manual" | "unmatched";
}

export interface MatchCandidate {
  product_id: number;
  product_code: string;
  keyword: string;
  kw_len: number;
}

export interface PendingReviewItem {
  shop_product_id: string;
  shop_code: string;
  product_name: string;
  card_game: string;
  product_type: string;
  match_candidates: MatchCandidate[];
}

export interface PendingReviewResponse {
  items: PendingReviewItem[];
  total: number;
}

export interface BuybackListResponse {
  items: BuybackProduct[];
  total: number;
  counts_by_game: Record<string, number>;
}

export interface PriceHistoryEntry {
  price_s: number | null;
  price_a: number | null;
  price_am: number | null;
  price_b: number | null;
  price_c: number | null;
  fetched_at: string;
}

export interface PriceHistoryResponse {
  shop_product_id: string;
  product_name: string;
  shop_code: string;
  card_game: string;
  product_type: string;
  history: PriceHistoryEntry[];
}

export interface AlertRule {
  id: string;
  name: string;
  card_game: string | null;
  shop_code: string | null;
  product_type: string | null;
  shop_product_id: string | null;
  direction: string;
  threshold_pct: number;
  price_grade: string;
  is_active: boolean;
  last_notified_at: string | null;
  cooldown_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface AlertFormState {
  name: string;
  card_game: string;
  shop_code: string;
  product_type: string;
  direction: string;
  threshold_pct: string;
  price_grade: string;
  is_active: boolean;
  cooldown_minutes: string;
}

export interface ByProductItem {
  product_id: number;
  product_code: string;
  name_ja: string;
  category: string;
  release_date: string | null;
  image_url: string | null;
  homura_price_s: number | null;
  homura_price_a: number | null;
  homura_price_b: number | null;
  homura_shop_product_id: string | null;
  homura_product_name: string | null;
  shinsoku_price_s: number | null;
  shinsoku_price_a: number | null;
  shinsoku_price_b: number | null;
  shinsoku_shop_product_id: string | null;
  shinsoku_product_name: string | null;
}

export interface ByProductResponse {
  items: ByProductItem[];
  total: number;
  counts_by_category: Record<string, number>;
}

export type CardGame = "all" | "pokemon" | "onepiece" | "yugioh" | "dragonball" | "weiss" | "lorcana";
export type ShopFilter = "all" | "shinsoku" | "homura";

export const PER_PAGE = 50;

export const INITIAL_ALERT_FORM: AlertFormState = {
  name: "",
  card_game: "",
  shop_code: "",
  product_type: "",
  direction: "down",
  threshold_pct: "5",
  price_grade: "price_s",
  is_active: true,
  cooldown_minutes: "360",
};

export function formatPrice(price: number | null): string {
  if (price === null || price === undefined) return "—";
  return `¥${price.toLocaleString()}`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function formatChartDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}
