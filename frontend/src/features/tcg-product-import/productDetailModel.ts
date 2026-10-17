import type { TFunction } from "i18next";
import { api, ApiError } from "../../lib/api";
import type { CodeCollision } from "./CodeCollisionNotice";

export const classificationFields = ["product_kind_id", "work_id", "manufacturer_id", "product_category_id"] as const;
export type Classification = typeof classificationFields[number];
/** ADR-1020: 「調べたが無い」の印を付けられる項目（API の項目名 → 下書きの項目名） */
export const blankConfirmable = [
  ["name_en", "english_title"], ["mark", "mark"], ["release_date", "release_date"], ["exclude_keywords", "exclude_keywords"],
] as const;
export type BlankCode = typeof blankConfirmable[number][0];
export type FormatOption = { id: string; name: string; is_active: boolean; game_ids: string[] };
export interface Detail {
  revision: string;
  product: Record<Classification, string | null> & {
    id: string; code: string; japanese_title: string; english_title: string | null;
    mark: string | null; release_date: string | null; search_keywords: string[]; exclude_keywords: string[];
    required_output_value: string | null; category_class: string; is_active: boolean; created_at: string;
    product_format_id: number | string | null; blank_confirmations: string[]; tenant_id?: string | null;
  };
  lookups: Record<Classification, { id: string; name: string; is_active: boolean }[]> & { product_format_id: FormatOption[] };
  code_collisions?: CodeCollision[];
}
export type Draft = Record<Classification, string> & {
  japanese_title: string; english_title: string; mark: string; release_date: string;
  search_keywords: string; exclude_keywords: string;
  product_format_id: string; blank_confirmations: BlankCode[];
};

export function draftFrom(result: Detail): Draft {
  const p = result.product;
  if (!/^[0-9a-f]{64}$/.test(result.revision) ||
      typeof p.japanese_title !== "string" || !Array.isArray(p.search_keywords) ||
      !Array.isArray(p.exclude_keywords) ||
      ![...p.search_keywords, ...p.exclude_keywords].every(word => typeof word === "string") ||
      !classificationFields.every(field => Array.isArray(result.lookups?.[field])) ||
      // ADR-1020: 印と細分類の選択肢が無い応答では開かない（空とみなして送ると保存済みの印を消すため）
      !Array.isArray(p.blank_confirmations) || !Array.isArray(result.lookups?.product_format_id)) {
    throw new Error("Invalid product detail");
  }
  return { japanese_title: p.japanese_title, english_title: p.english_title ?? "", mark: p.mark ?? "",
    release_date: p.release_date ?? "", product_kind_id: p.product_kind_id ?? "", work_id: p.work_id ?? "",
    manufacturer_id: p.manufacturer_id ?? "", product_category_id: p.product_category_id ?? "",
    search_keywords: p.search_keywords.join("\n"), exclude_keywords: p.exclude_keywords.join("\n"),
    product_format_id: p.product_format_id == null ? "" : String(p.product_format_id),
    blank_confirmations: blankConfirmable.map(([code]) => code).filter(code => p.blank_confirmations.includes(code)) };
}

export const words = (value: string) => value.split("\n").map(word => word.trim()).filter(Boolean);

/** 選んだ作品（ゲーム）に紐づく細分類だけを返す。正は product_format_game_links（API の game_ids） */
export const formatOptionsFor = (options: FormatOption[], workId: string) =>
  workId ? options.filter(option => option.game_ids.includes(String(workId))) : [];

/** 作品を変えた後の細分類。新しい作品に紐づかなければ空に戻す */
export const formatAfterWorkChange = (options: FormatOption[], workId: string, formatId: string) =>
  formatOptionsFor(options, workId).some(option => option.id === formatId) ? formatId : "";

/** 下書きの項目名 → 印の項目名（印を付けられない項目は undefined） */
export const blankCodeOf = (field: keyof Draft): BlankCode | undefined =>
  blankConfirmable.find(([, draftField]) => draftField === field)?.[0];

const requiredDraftFields = [
  "japanese_title", "english_title", "mark", "release_date", "search_keywords", "exclude_keywords",
  "work_id", "product_format_id", "product_category_id",
] as const;
export type RequiredDraftField = typeof requiredDraftFields[number];

/** ADR-1020 の9項目のうち、未入力で印も無い項目（案内の表示に使う。便2では保存を止めない） */
export function missingFields(draft: Draft): RequiredDraftField[] {
  return requiredDraftFields.filter(field => {
    if (String(draft[field] ?? "").trim()) return false;
    const code = blankCodeOf(field);
    return !(code && draft.blank_confirmations.includes(code));
  });
}

/** PUT /tcg/products/detail/{id} の body。商品詳細ドロワーの保存と除外ワード追加で共用する。 */
export function buildUpdateBody(draft: Draft, initial: Draft | null, detail: Detail) {
  return {
    ...draft, revision: detail.revision, release_date: draft.release_date || null,
    product_kind_id: draft.product_kind_id ? Number(draft.product_kind_id) : null, work_id: draft.work_id ? Number(draft.work_id) : null,
    manufacturer_id: draft.manufacturer_id || null, product_category_id: draft.product_category_id ? Number(draft.product_category_id) : null,
    product_format_id: draft.product_format_id ? Number(draft.product_format_id) : null, blank_confirmations: draft.blank_confirmations,
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

// ADR-1020 便3b: バックエンドが必須9項目で止めたときの符号（REQUIRED_FIELDS_MISSING:/REQUIRED_FIELDS_CLEARED:）を、画面の言葉に直す
const REQUIRED_FIELD_PREFIXES = [
  ["REQUIRED_FIELDS_MISSING:", "productDetail.requiredFieldsMissing"],
  ["REQUIRED_FIELDS_CLEARED:", "productDetail.requiredFieldsCleared"],
] as const;

// API の項目名 → 文言キー（productDetail.<key>）。載っていない名前はそのまま出す
const REQUIRED_FIELD_LABEL_KEYS: Record<string, string> = {
  name: "japanese_title",
  name_en: "english_title",
};

export function requiredFieldsMessage(err: unknown, t: TFunction): string | null {
  if (!(err instanceof ApiError) || err.status !== 422) return null;
  const code = err.message;
  for (const [prefix, key] of REQUIRED_FIELD_PREFIXES) {
    if (!code.startsWith(prefix)) continue;
    const fields = code
      .slice(prefix.length)
      .split(",")
      .filter((f) => f !== "")
      .map((f) => {
        const label = REQUIRED_FIELD_LABEL_KEYS[f] ?? f;
        const k = `productDetail.${label}`;
        const text = t(k);
        return text === k ? f : text;
      });
    return t(key, { fields: fields.join(t("reviewItem.wizard.register.listSeparator")) });
  }
  return null;
}
