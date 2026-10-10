import { api } from "../../lib/api";
import type { CodeCollision } from "./CodeCollisionNotice";

export const classificationFields = ["product_kind_id", "work_id", "manufacturer_id", "product_category_id"] as const;
export type Classification = typeof classificationFields[number];
export interface Detail {
  revision: string;
  product: Record<Classification, string | null> & {
    id: string; code: string; japanese_title: string; english_title: string | null;
    mark: string | null; release_date: string | null; search_keywords: string[]; exclude_keywords: string[];
    required_output_value: string | null; category_class: string; is_active: boolean; created_at: string;
  };
  lookups: Record<Classification, { id: string; name: string; is_active: boolean }[]>;
  code_collisions?: CodeCollision[];
}
export type Draft = Record<Classification, string> & {
  japanese_title: string; english_title: string; mark: string; release_date: string;
  search_keywords: string; exclude_keywords: string;
};

export function draftFrom(result: Detail): Draft {
  const p = result.product;
  if (!/^[0-9a-f]{64}$/.test(result.revision) ||
      typeof p.japanese_title !== "string" || !Array.isArray(p.search_keywords) ||
      !Array.isArray(p.exclude_keywords) ||
      ![...p.search_keywords, ...p.exclude_keywords].every(word => typeof word === "string") ||
      !classificationFields.every(field => Array.isArray(result.lookups?.[field]))) {
    throw new Error("Invalid product detail");
  }
  return { japanese_title: p.japanese_title, english_title: p.english_title ?? "", mark: p.mark ?? "",
    release_date: p.release_date ?? "", product_kind_id: p.product_kind_id ?? "", work_id: p.work_id ?? "",
    manufacturer_id: p.manufacturer_id ?? "", product_category_id: p.product_category_id ?? "",
    search_keywords: p.search_keywords.join("\n"), exclude_keywords: p.exclude_keywords.join("\n") };
}

export const words = (value: string) => value.split("\n").map(word => word.trim()).filter(Boolean);

/** PUT /tcg/products/detail/{id} の body。商品詳細ドロワーの保存と除外ワード追加で共用する。 */
export function buildUpdateBody(draft: Draft, initial: Draft | null, detail: Detail) {
  return {
    ...draft, revision: detail.revision, release_date: draft.release_date || null,
    product_kind_id: draft.product_kind_id ? Number(draft.product_kind_id) : null, work_id: draft.work_id ? Number(draft.work_id) : null,
    manufacturer_id: draft.manufacturer_id || null, product_category_id: draft.product_category_id ? Number(draft.product_category_id) : null,
    search_keywords: draft.search_keywords === initial?.search_keywords ? detail.product.search_keywords : words(draft.search_keywords),
    exclude_keywords: draft.exclude_keywords === initial?.exclude_keywords ? detail.product.exclude_keywords : words(draft.exclude_keywords),
  };
}

export type AddWordResult = "added" | "exists" | "staged";

/**
 * 既存商品の除外ワードに1語足す。最新の詳細を読み、revision つきで保存する（audit_log に変更前後が残る経路）。
 * revision が合わない（409）ときは ApiError がそのまま上がる。API を呼ぶのはここだけ。
 */
export async function addExcludeWord(productId: number, word: string): Promise<AddWordResult> {
  const detail = await api.get<Detail>(`/tcg/products/detail/${productId}`);
  if (Number(detail.product?.id) !== productId) throw new Error("Product mismatch");
  const base = draftFrom(detail);
  if (detail.product.exclude_keywords.includes(word)) return "exists";
  const draft: Draft = { ...base, exclude_keywords: [...detail.product.exclude_keywords, word].join("\n") };
  await api.put<Detail>(`/tcg/products/detail/${productId}`, buildUpdateBody(draft, base, detail));
  return "added";
}
