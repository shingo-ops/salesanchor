/**
 * 請求書・見積の商品行で使う在庫（GET /invoices/draft-inventory）を読む（invoice-create-portfolio design-v2 §3-3・§3-4）。
 *
 * 道は 1 回だけ呼ぶ（category で絞らない）。カテゴリでの絞り込みは画面で work_code を見て行う。
 * 値段・在庫数・重さの正本はサーバーのこの道だけ。画面で値段や重さを直書きしない。
 */
import { useApiQuery } from "../../lib/query/apiQuery";

export const DRAFT_INVENTORY_PATH = "/invoices/draft-inventory";

/** 状態ごとの値段（円）と在庫数。backend/app/schemas/inventory_aggregated.py の ConditionCell */
export interface DraftInventoryCell {
  price: number | null;
  quantity: number | null;
}

export interface DraftInventoryCategory {
  code: string;
  name_ja: string | null;
}

export interface DraftInventoryItem {
  product_id: number;
  name: string;
  name_en: string | null;
  mark: string | null;
  work_code: string | null;
  box_weight_kg: number | null;
  case_weight_kg: number | null;
  /** 状態の名前 → 値段と数。在庫の無い状態はキーごと無い */
  cells: Record<string, DraftInventoryCell>;
}

export interface DraftInventory {
  categories: DraftInventoryCategory[];
  items: DraftInventoryItem[];
}

export interface DraftInventoryState {
  categories: DraftInventoryCategory[];
  items: DraftInventoryItem[];
  loading: boolean;
  /** 読めなかったときの文（api が文言にしたもの）。読めたら "" */
  error: string;
}

function asDraftInventory(data: unknown): DraftInventory | null {
  if (data === null || typeof data !== "object" || Array.isArray(data)) return null;
  const d = data as Partial<DraftInventory>;
  return Array.isArray(d.items) && Array.isArray(d.categories) ? (d as DraftInventory) : null;
}

export function useDraftInventory(): DraftInventoryState {
  const q = useApiQuery<DraftInventory>(DRAFT_INVENTORY_PATH);
  const data = asDraftInventory(q.data);
  return {
    categories: data?.categories ?? [],
    items: data?.items ?? [],
    loading: q.isPending,
    error: q.error ? (q.error instanceof Error ? q.error.message : String(q.error)) : "",
  };
}

/** 商品の候補の絞り込み。商品名・英語名・型番のどれかに、大文字小文字を区別せず含まれれば当たり。空の検索語は全部 */
export function productMatches(item: DraftInventoryItem, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (q === "") return true;
  return [item.name, item.name_en, item.mark].some((s) => s !== null && s.toLowerCase().includes(q));
}
