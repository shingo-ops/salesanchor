/** 会社・連絡先の状態の記号（DB public.customer_statuses の code）。記号を書いてよいのはこのファイルだけ（ADR-1076）。名前は書かない（DB の name_ja / name_en が正本）。 */
export const CUSTOMER_STATUS_CODES = {
  active: "active",
  inactive: "inactive",
  archived: "archived",
  pendingDedupReview: "pending_dedup_review",
} as const;
export type CustomerStatusCode = (typeof CUSTOMER_STATUS_CODES)[keyof typeof CUSTOMER_STATUS_CODES];
/** API GET /customer-statuses の1行 */
export interface CustomerStatusRow { code: string; name_ja: string; name_en: string; sort_order: number; is_active: boolean; selectable_on_create: boolean; }
