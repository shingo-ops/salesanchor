/**
 * 要確認の件への保存操作の唯一の置き場所（API を呼ぶ処理と送る中身の正本）。
 * 件を開いた画面（ReviewItemDrawer / ProductMasterDrawer）が使う。
 *   - 商品を直す:     POST /tcg/items/{id}/corrections （field_name='product_id'）
 *   - このままで良い: POST /tcg/items/{id}/review-ack
 *   - 商品の候補:     GET  /tcg/products/search?query=
 *   - 新規登録:       GET  /tcg/products/registration-form / POST /tcg/products/check-duplicates / POST /tcg/products
 *   - 検索キーワード: POST /tcg/products/{id}/search-keywords
 */
import { api } from "../../lib/api";

/** 保存に必要な、件の最小の形（AnalysisReviewItem・一覧の行のどちらも満たす） */
export interface ReviewActionTarget {
  extraction_item_id: string;
  source_message_id: string;
  system: Record<string, string>;
}

export interface ProductCandidate {
  product_id: string;
  product_uuid: string;
  japanese_title: string;
  search_keywords: string;
}

export interface ProductOption {
  value: string;
  label: string;
  /** 商品の番号（整数文字列）。検索キーワードの追加 API に使う */
  productId?: string;
}

/** 商品を product_uuid で確定する。system_value は今の product_uuid（無ければ空） */
export function postProductCorrection(item: ReviewActionTarget, productUuid: string) {
  return api.post<{ ok: boolean; saved: number }>(
    `/tcg/items/${encodeURIComponent(item.extraction_item_id)}/corrections`,
    {
      source_message_id: item.source_message_id,
      fields: [{ field_name: "product_id", system_value: item.system.product_uuid || "", human_value: productUuid }],
    },
  );
}

/** 指定の理由コードを「このままで良い」として記録する */
export function postReviewAck(item: ReviewActionTarget, codes: string[]) {
  return api.post(`/tcg/items/${item.extraction_item_id}/review-ack`, {
    source_message_id: item.source_message_id,
    codes,
  });
}

/** 有効な商品を名前の部分一致で探す（最大10件はサーバー側） */
export async function searchProductCandidates(query: string): Promise<ProductCandidate[]> {
  const params = new URLSearchParams({ query });
  const result = await api.get<{ candidates: ProductCandidate[] }>(`/tcg/products/search?${params.toString()}`);
  return result.candidates;
}

/** 候補を「名前で表示・product_uuid が値」の選択肢にする */
export async function searchProductOptions(query: string): Promise<ProductOption[]> {
  const candidates = await searchProductCandidates(query);
  return candidates.map((candidate) => ({ value: candidate.product_uuid, label: candidate.japanese_title, productId: candidate.product_id }));
}

// ── 商品マスタ新規登録（API の型は、ここ1か所だけに置く） ─────────────────────────

export type LookupOption = { id: string; name: string };

export type RegistrationForm = {
  item: { extraction_item_id: string; source_message_id: string; raw_name: string };
  lookups: Record<string, LookupOption[]>;
};

export type RegistrationValues = {
  product_kind_id: string;
  work_id: string;
  manufacturer_id: string;
  product_category_id: string;
  mark: string;
  japanese_title: string;
  english_title: string;
  release_date: string;
  search_keywords: string;
  exclude_keywords: string;
};

export type DupCandidate = { product_id: string; japanese_title: string };

export type CreateProductResult = { ok: boolean; product_id?: string; code?: string; candidates?: DupCandidate[] };

export type AddKeywordResult = { ok: boolean; code?: string };

/** 新規登録フォームの選択肢を取る */
export function fetchRegistrationForm(item: ReviewActionTarget) {
  const params = new URLSearchParams({
    extraction_item_id: item.extraction_item_id,
    source_message_id: item.source_message_id,
  });
  return api.get<RegistrationForm>(`/tcg/products/registration-form?${params.toString()}`);
}

/** 似た商品がないか確認する */
export function checkProductDuplicates(item: ReviewActionTarget, values: RegistrationValues) {
  return api.post<{ candidates: DupCandidate[] }>("/tcg/products/check-duplicates", {
    extraction_item_id: item.extraction_item_id,
    source_message_id: item.source_message_id,
    ...values,
  });
}

/** 商品マスタに登録する。force=true は「似た商品を確認済みで新規登録」 */
export function createProduct(item: ReviewActionTarget, values: RegistrationValues, force: boolean) {
  return api.post<CreateProductResult>("/tcg/products", {
    extraction_item_id: item.extraction_item_id,
    source_message_id: item.source_message_id,
    ...values,
    force,
  });
}

/** 商品に検索キーワードを1つ足す（productId は整数文字列） */
export function addSearchKeyword(productId: string, keyword: string) {
  return api.post<AddKeywordResult>(`/tcg/products/${encodeURIComponent(productId)}/search-keywords`, {
    new_keyword: keyword,
  });
}
