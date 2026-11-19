/**
 * 請求書・見積の商品行の純粋な関数（invoice-create-portfolio design-v2 §3-3・§3-8）。
 *
 * - 値段・在庫数・重さはサーバーの在庫の道（useDraftInventory）の値だけを使う。ここに値を直書きしない。
 * - 単価の初期値は「在庫表の円の値段 ÷ 為替」を小数 2 けたで切り捨て（PO 2026-11-18「1」）。円の請求書は直さない。
 *   為替が無い通貨は 0 にして作成を止める（手で直せる）。通貨を選び直したら、手で直していない行だけ入れ直す。
 * - 文言は文言キーで返し、t() は部品が呼ぶ（React も i18n も読まない）。
 */
import { isCreatableItem } from "../../lib/invoiceDraftContext";
import type { LineItem, QuoteHandoffState } from "./quoteDraft";
import { blankItem } from "./quoteDraft";
import type { DraftInventoryItem } from "./useDraftInventory";

/** 初期の行数と最大の行数（見本どおり。§3-3） */
export const INIT_ROWS = 12;
export const MAX_ROWS = 20;

/** 状態の並び順（在庫表の列と同じ）。これ以外の状態は後ろに名前順 */
export const STATE_ORDER: readonly string[] = ["Case", "Sealed box", "No shrink box", "Damaged sealed box"];

/** 空の行（商品が選ばれていない行。数量 0 は「空」の印で、保存には送らない） */
export function emptyRow(): LineItem {
  return {
    ...blankItem,
    quantity: 0,
    category_code: null,
    stock_limit: null,
    price_yen: null,
    price_edited: false,
    zero_stock_warning: false,
  };
}

/** 行を INIT_ROWS まで空の行で足す（それより多ければそのまま。消さない） */
export function padRows(rows: LineItem[]): LineItem[] {
  const out = [...rows];
  while (out.length < INIT_ROWS) out.push(emptyRow());
  return out;
}

/** 在庫表の画面から持ってきた商品を先頭の行から入れる（§3-1）。カテゴリ・状態は在庫の答えから画面が引く */
export function handoffRows(handoff: QuoteHandoffState): LineItem[] {
  const picked = (handoff?.selectedProducts ?? []).map((p) => ({
    ...emptyRow(),
    product_id: p.product_id,
    product_name: p.product_name,
    inventory_id: p.inventory_id ?? null,
    quantity: 1,
  }));
  return padRows(picked);
}

/** 円 → 請求書の通貨。円はそのまま。為替が無い・0 以下は 0。ほかは小数 2 けたで切り捨て */
export function yenToCurrency(yen: number | null | undefined, currency: string, rate: number | null | undefined): number {
  if (yen === null || yen === undefined || !Number.isFinite(yen)) return 0;
  if (currency === "JPY") return yen;
  if (rate === null || rate === undefined || !(rate > 0)) return 0;
  return Math.floor((yen * 100) / rate + 1e-9) / 100;
}

/** 状態の名前 → 保存する unit（§3-3）。"Case"→case・box を含む→box・pack を含む→pack・ほかは null */
export function unitFromState(state: string): string | null {
  if (state === "Case") return "case";
  const s = state.toLowerCase();
  if (s.includes("box")) return "box";
  if (s.includes("pack")) return "pack";
  return null;
}

/** 状態に合う 1 個の重さ。"Case" はケースの重さ、ほかは BOX の重さ。無ければ null */
export function weightForState(item: DraftInventoryItem, state: string): number | null {
  const w = state === "Case" ? item.case_weight_kg : item.box_weight_kg;
  return w === null || w === undefined ? null : w;
}

/** 在庫のある状態だけ（数が 0 の状態は除く。数が分からない null は残す）を、在庫表の列の順で */
export function statesFor(item: DraftInventoryItem | undefined): string[] {
  if (!item) return [];
  const keys = Object.keys(item.cells).filter((k) => {
    const q = item.cells[k]?.quantity;
    return q === null || q === undefined || q > 0;
  });
  const known = STATE_ORDER.filter((s) => keys.includes(s));
  const others = keys.filter((k) => !STATE_ORDER.includes(k)).sort();
  return [...known, ...others];
}

/** 在庫の上限を超えたら上限に戻す */
export function clampQuantity(quantity: number, limit: number | null | undefined): number {
  return limit !== null && limit !== undefined && quantity > limit ? limit : quantity;
}

/** 行のカテゴリ。行に無ければ商品の作品の符号（在庫表から持ってきた行） */
export function categoryOf(row: LineItem, items: DraftInventoryItem[]): string {
  if (row.category_code) return row.category_code;
  if (row.product_id === null) return "";
  return items.find((i) => i.product_id === row.product_id)?.work_code ?? "";
}

/** カテゴリを選び直す。変われば、その行の商品・状態・数量を空にする（§3-3） */
export function changeCategory(row: LineItem, code: string): LineItem {
  if ((row.category_code ?? "") === code) return row;
  return { ...emptyRow(), category_code: code === "" ? null : code };
}

/** 商品を選ぶ。状態・重さ・単価・在庫上限は空に戻す（状態を選んだときに入る） */
export function applyProduct(row: LineItem, item: DraftInventoryItem): LineItem {
  return {
    ...emptyRow(),
    category_code: item.work_code ?? row.category_code ?? null,
    product_id: item.product_id,
    product_name: item.name,
    name_en: item.name_en,
    box_weight_kg: item.box_weight_kg,
    case_weight_kg: item.case_weight_kg,
    quantity: row.quantity,
  };
}

/** 状態を選ぶ。重さ・単価・在庫上限が入り、数量が空なら 1、上限を超えれば上限（§3-3・K11・K12） */
export function applyState(
  row: LineItem,
  item: DraftInventoryItem,
  state: string,
  currency: string,
  rate: number | null,
): LineItem {
  if (state === "") {
    return { ...row, condition: null, unit: null, weight: null, unit_price: 0, price_yen: null, price_edited: false, stock_limit: null };
  }
  const cell = item.cells[state];
  const priceYen = cell?.price ?? null;
  const limit = cell?.quantity ?? null;
  const quantity = row.quantity >= 1 ? row.quantity : 1;
  return {
    ...row,
    // 在庫表の画面から持ってきた行は英語名を持たないため、在庫の道の値で入れる
    name_en: item.name_en,
    condition: state,
    unit: unitFromState(state),
    weight: weightForState(item, state),
    box_weight_kg: item.box_weight_kg,
    case_weight_kg: item.case_weight_kg,
    price_yen: priceYen,
    price_edited: false,
    unit_price: yenToCurrency(priceYen, currency, rate),
    stock_limit: limit,
    quantity: clampQuantity(quantity, limit),
  };
}

/** 数量を打つ。整数でない・0 未満は 0、上限を超えたら上限 */
export function applyQuantity(row: LineItem, text: string): LineItem {
  const n = Number(text);
  const q = text.trim() === "" || !Number.isFinite(n) || n < 0 ? 0 : Math.floor(n);
  return { ...row, quantity: clampQuantity(q, row.stock_limit) };
}

/** 単価を打つ。手で直した印を付ける（通貨を選び直しても入れ直さない） */
export function applyUnitPrice(row: LineItem, text: string): LineItem {
  const n = Number(text);
  return { ...row, unit_price: text.trim() === "" || !Number.isFinite(n) ? 0 : n, price_edited: true };
}

/** 通貨を選び直したとき、手で直していない行だけ単価を入れ直す（PO 2026-11-18「1」） */
export function reconvertPrices(rows: LineItem[], currency: string, rate: number | null): LineItem[] {
  return rows.map((r) =>
    r.price_edited || r.price_yen === null || r.price_yen === undefined
      ? r
      : { ...r, unit_price: yenToCurrency(r.price_yen, currency, rate) },
  );
}

export type RowStatus = "empty" | "needsState" | "weightMissing" | "invalid" | "ready";

/** 行の状態。空の行は送らない。状態が無い・重さが無い・数や単価が正しくない行があれば作成を止める（§3-3・K20・K21） */
export function rowStatus(row: LineItem): RowStatus {
  if (row.product_id === null && row.product_name.trim() === "") return "empty";
  if (!row.condition) return "needsState";
  if (row.weight === null || row.weight === undefined) return "weightMissing";
  return isCreatableItem(row) ? "ready" : "invalid";
}

/** 商品の入った行だけ */
export function filledRows(rows: LineItem[]): LineItem[] {
  return rows.filter((r) => rowStatus(r) !== "empty");
}

/** 作れるか: 商品の入った行が 1 つ以上で、その全部が ready */
export function allRowsReady(rows: LineItem[]): boolean {
  const filled = filledRows(rows);
  return filled.length > 0 && filled.every((r) => rowStatus(r) === "ready");
}

/** 総重量（重さ×数量の和・小数 3 けた）。重さの無い行は数えない */
export function totalWeight(rows: LineItem[]): number {
  const sum = filledRows(rows).reduce((acc, r) => (r.weight === null || r.weight === undefined ? acc : acc + r.weight * r.quantity), 0);
  return Math.round(sum * 1000) / 1000;
}

/** 小計（画面の表示だけ。合計はサーバーの試算） */
export function rowSubtotal(row: LineItem): number {
  return Math.round(row.quantity * row.unit_price * 100) / 100;
}

/** 保存に送る形（今の InvoiceItemInput。画面だけの項目は送らない） */
export function toInvoiceItem(row: LineItem) {
  return {
    product_id: row.product_id,
    product_name: row.product_name,
    name_en: row.name_en ?? null,
    condition: row.condition ?? null,
    unit: row.unit ?? null,
    quantity: row.quantity,
    unit_price: row.unit_price,
    weight: row.weight,
  };
}
