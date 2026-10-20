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
/** ADR-1028 便4: 荷姿（入数・重さ・出典）。API の1行 */
export interface PackagingRow {
  unit_code: string; contained_unit_code: string | null;
  contained_count: number | null; count_source: string | null; count_source_urls: string[];
  weight_kg: string | number | null; weight_source: string | null; weight_source_urls: string[];
  note: string | null; updated_at: string | null;
}
export interface PackagingUnit {
  code: string; contained_code: string; name: string; name_en: string | null;
  contained_name: string; contained_name_en: string | null;
}
/** 画面の下書き。数は文字列、URL は改行区切りの文字列 */
export interface PackagingDraft {
  unit_code: string; contained_count: string; count_source: string; count_source_urls: string;
  weight_kg: string; weight_source: string; weight_source_urls: string; note: string;
}
export const LEGACY_SOURCE = "legacy";
export interface Detail {
  revision: string;
  product: Record<Classification, string | null> & {
    id: string; code: string; japanese_title: string; english_title: string | null;
    mark: string | null; release_date: string | null; search_keywords: string[]; exclude_keywords: string[];
    required_output_value: string | null; category_class: string; is_active: boolean; created_at: string;
    product_format_id: number | string | null; blank_confirmations: string[]; tenant_id?: string | null;
    packagings: PackagingRow[];
  };
  packaging_units: PackagingUnit[];
  packaging_sources: string[];
  lookups: Record<Classification, { id: string; name: string; is_active: boolean }[]> & { product_format_id: FormatOption[] };
  code_collisions?: CodeCollision[];
}
export type Draft = Record<Classification, string> & {
  japanese_title: string; english_title: string; mark: string; release_date: string;
  search_keywords: string; exclude_keywords: string;
  product_format_id: string; blank_confirmations: BlankCode[];
  packagings: PackagingDraft[];
};

export const emptyPackaging = (unit_code: string): PackagingDraft => ({
  unit_code, contained_count: "", count_source: "", count_source_urls: "", weight_kg: "", weight_source: "", weight_source_urls: "", note: "",
});

export function draftFrom(result: Detail): Draft {
  const p = result.product;
  if (!/^[0-9a-f]{64}$/.test(result.revision) ||
      typeof p.japanese_title !== "string" || !Array.isArray(p.search_keywords) ||
      !Array.isArray(p.exclude_keywords) ||
      ![...p.search_keywords, ...p.exclude_keywords].every(word => typeof word === "string") ||
      !classificationFields.every(field => Array.isArray(result.lookups?.[field])) ||
      // ADR-1020: 印と細分類の選択肢が無い応答では開かない（空とみなして送ると保存済みの印を消すため）
      !Array.isArray(p.blank_confirmations) || !Array.isArray(result.lookups?.product_format_id) ||
      // ADR-1028 便4: 荷姿の行・単位・出典が配列でない応答では開かない（空とみなして送ると保存済みの荷姿を消すため）
      !Array.isArray(p.packagings) || !Array.isArray(result.packaging_units) || !Array.isArray(result.packaging_sources)) {
    throw new Error("Invalid product detail");
  }
  const packagings = result.packaging_units.map((unit): PackagingDraft => {
    const row = p.packagings.find(r => r.unit_code === unit.code);
    if (!row) return emptyPackaging(unit.code);
    return { unit_code: unit.code, contained_count: row.contained_count == null ? "" : String(row.contained_count),
      count_source: row.count_source ?? "", count_source_urls: (row.count_source_urls ?? []).join("\n"),
      weight_kg: row.weight_kg == null ? "" : String(row.weight_kg), weight_source: row.weight_source ?? "",
      weight_source_urls: (row.weight_source_urls ?? []).join("\n"), note: row.note ?? "" };
  });
  return { japanese_title: p.japanese_title, english_title: p.english_title ?? "", mark: p.mark ?? "",
    release_date: p.release_date ?? "", product_kind_id: p.product_kind_id ?? "", work_id: p.work_id ?? "",
    manufacturer_id: p.manufacturer_id ?? "", product_category_id: p.product_category_id ?? "",
    search_keywords: p.search_keywords.join("\n"), exclude_keywords: p.exclude_keywords.join("\n"),
    product_format_id: p.product_format_id == null ? "" : String(p.product_format_id),
    blank_confirmations: blankConfirmable.map(([code]) => code).filter(code => p.blank_confirmations.includes(code)),
    packagings };
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
export function missingFields(draft: Omit<Draft, "packagings">): RequiredDraftField[] {
  return requiredDraftFields.filter(field => {
    if (String(draft[field] ?? "").trim()) return false;
    const code = blankCodeOf(field);
    return !(code && draft.blank_confirmations.includes(code));
  });
}

const normPackaging = (r: PackagingDraft) => ({
  ...Object.fromEntries(Object.entries(r).map(([k, v]) => [k, String(v ?? "").trim()])),
  count_source_urls: words(r.count_source_urls), weight_source_urls: words(r.weight_source_urls),
});

/** 荷姿の下書きが元と違うか（空白と URL の改行の違いは無視して比べる） */
export function packagingsChanged(a: PackagingDraft[] | undefined, b: PackagingDraft[] | undefined): boolean {
  return JSON.stringify((a ?? []).map(normPackaging)) !== JSON.stringify((b ?? []).map(normPackaging));
}

const packagingBody = (r: PackagingDraft) => ({
  unit_code: r.unit_code,
  contained_count: r.contained_count.trim() ? Number(r.contained_count) : null,
  count_source: r.count_source || null, count_source_urls: words(r.count_source_urls),
  weight_kg: r.weight_kg.trim() ? r.weight_kg.trim() : null,
  weight_source: r.weight_source || null, weight_source_urls: words(r.weight_source_urls),
  note: r.note.trim() ? r.note.trim() : null,
});

/** PUT /tcg/products/detail/{id} の body。商品詳細ドロワーの保存と除外ワード追加で共用する。 */
export function buildUpdateBody(draft: Draft, initial: Draft | null, detail: Detail) {
  const { packagings, ...rest } = draft;
  // 荷姿は「共用商品で、かつ変えたとき」だけ送る（送らなければサーバーは触らない）
  const sendPackagings = detail.product.tenant_id == null && packagingsChanged(packagings, initial?.packagings);
  return {
    ...rest, ...(sendPackagings ? { packagings: packagings.map(packagingBody) } : {}), revision: detail.revision, release_date: draft.release_date || null,
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

// ADR-1028 便4: 荷姿の保存で返る 422 の符号を画面の言葉に直す
export const PACKAGING_ERROR_CODES = [
  "PACKAGING_UNKNOWN_UNIT", "PACKAGING_DUPLICATE_UNIT", "PACKAGING_SOURCE_MISMATCH", "PACKAGING_URLS_REQUIRED",
  "PACKAGING_DUPLICATE_URL", "PACKAGING_INVALID_URL", "PACKAGING_LEGACY_NOT_ALLOWED",
  "PACKAGING_NOTE_WITHOUT_VALUE", "PACKAGING_SHARED_ONLY",
] as const;

export function packagingErrorMessage(err: unknown, t: TFunction): string | null {
  if (!(err instanceof ApiError) || err.status !== 422) return null;
  const code = PACKAGING_ERROR_CODES.find(c => err.message === c || err.message.startsWith(`${c}:`));
  return code ? t(`productDetail.packaging.errors.${code}`) : null;
}
