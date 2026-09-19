import { api } from "../../lib/api";

export type SourceScope = "all" | "active" | "history";
export interface SoldOutItem {
  analysis_result_id: string;
  extraction_item_id: string;
  source_message_id: string;
  supplier_id: string | null;
  product_id: string | null;
  provider: string;
  product_title: string;
  raw_product_name: string;
  raw_quantity: string;
  raw_price: string;
  raw_unit: string;
  raw_state: string;
  raw_memo: string;
  raw_text: string;
  status: "Sold out";
  source_is_active: boolean | null;
  line_posted_at: string | null;
  line_start: number | null;
  line_end: number | null;
}
export interface SoldOutResponse {
  items: SoldOutItem[];
  total: number;
  offset: number;
  limit: number;
  as_of: string;
}
export function fetchSoldOut(q: string, sourceScope: SourceScope, offset: number) {
  const params = new URLSearchParams({ q: q.trim(), source_scope: sourceScope, offset: String(offset), limit: "50" });
  return api.get<SoldOutResponse>(`/tcg/sold-out-results?${params}`);
}
