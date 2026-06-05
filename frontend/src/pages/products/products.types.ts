/**
 * 商品マスタ（ProductsPage）の型定義・定数。
 * ページ本体の肥大化（800 行上限）回避のため切り出し（orders.types.ts と同パターン）。
 */

export interface Product {
  id: number;
  product_code: string | null;
  name_ja: string;
  name_en: string | null;
  product_kind: string | null;
  category: string | null;
  mark: string | null;
  status: string;
  condition: string | null;
  unit_price: number | null;
  quantity: number;
  weight: number | null;
  notes: string | null;
  release_date: string | null;
  created_at: string;
  updated_at: string;
  // Phase 1-C M-MVP（2026-04-28）
  jan_code: string | null;
  card_number: string | null;
  expansion_code: string | null;
  rarity: string | null;
  language: string | null;
  unit_price_usd: number | null;
  unit_price_eur: number | null;
  image_url: string | null;
  is_archived: boolean;
  archived_at: string | null;
  supplier_default_id: number | null;
  tcg_type: string | null;
  set_type: string | null;
  unit: string | null;
  // ADR-093 Phase 1: 商品マスタ全項目（Box 属性 + 発送ラベル + 検索/分類）
  boxes_per_case: number | null;
  packs_per_box: number | null;
  box_weight_kg: number | null;
  case_weight_kg: number | null;
  volume_weight: number | null;
  moq: number | null;
  hs_code: string | null;
  material: string | null;
  item: string | null;
  required_output_value: string | null;
  search_keywords: string | null;
  exclude_keywords: string | null;
  related_series: string | null;
  category_classification: string | null;
  // 手動並び替え（行ドラッグ）順。NULL=未設定。
  display_order: number | null;
}

export type FormState = {
  name_ja: string;
  name_en: string;
  product_kind: string;
  category: string;
  tcg_type: string;
  set_type: string;
  mark: string;
  status: string;
  condition: string;
  unit: string;
  unit_price: string;
  quantity: string;
  weight: string;
  notes: string;
  release_date: string;
  // Phase 1-C M-MVP
  jan_code: string;
  card_number: string;
  expansion_code: string;
  rarity: string;
  language: string;
  unit_price_usd: string;
  unit_price_eur: string;
  image_url: string;
  // ADR-093 Phase 1: 商品マスタ全項目（Box 属性 + 発送ラベル + 検索/分類）
  boxes_per_case: string;
  packs_per_box: string;
  box_weight_kg: string;
  case_weight_kg: string;
  volume_weight: string;
  moq: string;
  hs_code: string;
  material: string;
  item: string;
  required_output_value: string;
  search_keywords: string;
  exclude_keywords: string;
  related_series: string;
  category_classification: string;
};

export const emptyForm: FormState = {
  name_ja: "", name_en: "", product_kind: "TCG", category: "", tcg_type: "", set_type: "", mark: "",
  status: "active", condition: "", unit: "", unit_price: "", quantity: "0",
  weight: "", notes: "", release_date: "",
  jan_code: "", card_number: "", expansion_code: "", rarity: "", language: "",
  unit_price_usd: "", unit_price_eur: "", image_url: "",
  boxes_per_case: "", packs_per_box: "", box_weight_kg: "", case_weight_kg: "",
  // 発送ラベルは TCG（カード）共通の既定値（ひとしさん確定 2026-06-04）
  volume_weight: "", moq: "", hs_code: "9504400000", material: "Paper", item: "Playing card",
  required_output_value: "", search_keywords: "", exclude_keywords: "",
  related_series: "", category_classification: "",
};

// 各種マスタ(product_attribute_masters)の 1 選択肢。
export type AttrOption = { code: string | null; label_ja: string; label_en: string | null };

// 商品マスタの選択肢系プルダウンは各種マスタを /products/attribute-options 経由で参照する。
// 素材プルダウンのフォールバック判定にのみ使う最小の既定集合。
const MATERIAL_OPTIONS = ["Paper"];

// 素材は取込/旧データで大文字小文字が揺れる（paper / Paper）。MATERIAL_OPTIONS と
// 大文字小文字を無視して一致させ、プルダウンで正しく選択状態にする（一致しなければ生値を返す）。
export const normalizeMaterial = (m: string): string => {
  if (!m) return "";
  return MATERIAL_OPTIONS.find((o) => o.toLowerCase() === m.toLowerCase()) ?? m;
};
