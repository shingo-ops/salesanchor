/**
 * 閲覧ページ（/viewer/）が受け取る応答の型。
 * openapi の 200 応答は型なし（schema: {}）なので、生成型に頼らずここに1つ書く。
 * 形の正本は backend の GET /api/v1/viewer/inventory と POST /api/v1/viewer/login。
 */

/** offer_type は in_stock / pre_order / null（どちらでもない status） */
export type ViewerOfferType = "in_stock" | "pre_order" | null;

/** 作り置きの1行（15キー）。unit_price・quantity・posted_at は文字列で、無いときは ''。 */
export interface ViewerRow {
  posted_at: string;
  mark: string;
  japanese_title: string;
  english_title: string;
  condition: string;
  unit_price: string;
  quantity: string;
  note_ja: string;
  status: string;
  release_date: string;
  series: string;
  provider: string;
  search_keywords: string;
  ship_ja: string;
  offer_type: ViewerOfferType;
}

/** 表に渡す行。受け取ったときの配列の位置を idx に持ち、rowKey と最後の並びのキーにする。 */
export interface ViewerTableRow extends ViewerRow {
  idx: number;
}

export interface ViewerInventoryResponse {
  /** ISO8601（UTC） */
  updated_at: string;
  fresh_window_hours: number;
  rows: ViewerRow[];
}

export interface ViewerLoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  must_change_password: boolean;
}

export interface ViewerSignupResponse {
  signup_code: string;
  /** ISO8601 */
  expires_at: string;
  invite_url: string | null;
}

/** ④ 案内の種類 */
export type ViewerNoticeKind = "preparing" | "suspended" | "expired" | "error";
