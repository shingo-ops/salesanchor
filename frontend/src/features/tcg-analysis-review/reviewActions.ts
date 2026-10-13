/**
 * 要確認の件への保存操作の唯一の置き場所（API を呼ぶ処理と送る中身の正本）。
 * 一覧の行（ReviewRowActions）と、件を開いた画面（ReviewItemDrawer / ProductMasterDrawer）の両方が使う。
 *   - 商品を直す:     POST /tcg/items/{id}/corrections （field_name='product_id'）
 *   - このままで良い: POST /tcg/items/{id}/review-ack
 *   - 商品の候補:     GET  /tcg/products/search?query=
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
  return candidates.map((candidate) => ({ value: candidate.product_uuid, label: candidate.japanese_title }));
}
