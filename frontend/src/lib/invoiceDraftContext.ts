/**
 * 請求書の材料（GET /invoices/draft-context）と試算（POST /invoices/preview）の形と、
 * 画面で使う純粋な関数（invoice-create-portfolio 便D・design.md §3-2）。
 *
 * 通貨・支払方法・税率の選択肢の正本はサーバーの材料の道だけ。ここに通貨や支払方法の直書きを置かない。
 * 文言は文言キーで返し、t() は部品が呼ぶ（この関数群は React も i18n も読まない）。
 */
import { API_ERROR_REASON_KEYS } from "./apiErrorReason";

export type PaymentMethodType = "bank" | "wise" | "paypal";

export interface DraftAddress {
  company_name: string | null;
  billing_display_name: string | null;
  label: string | null;
  postal_code: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  phone: string | null;
  // サーバーの DraftContextAddress（backend/app/schemas/invoice.py）が返す発送先の残りの欄
  recipient_name?: string | null;
  email?: string | null;
  tax_id?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  address_line_3?: string | null;
  country_name?: string | null;
}

export interface DraftContextPayment {
  id: number | null;
  method_type: PaymentMethodType;
  display_name: string | null;
  wise_currency: string | null;
}

export interface DraftFxRate {
  currency: string;
  rate: number;
  fetched_at: string | null;
}

export interface DraftContext {
  company_id: number;
  ship_to: DraftAddress | null;
  bill_to: DraftAddress | null;
  contact_name: string | null;
  contact_email: string | null;
  issuer_region: string | null;
  origin_country_code: string | null;
  destination_country_code: string | null;
  destination_postal_code: string | null;
  currencies: string[];
  fx_rates: DraftFxRate[];
  default_currency: string | null;
  currency: string | null;
  payment_methods: DraftContextPayment[];
  tax_rate_percent: string | null;
  incoterms: string;
}

export interface DutyComponent {
  label: string;
  amount: string;
}

/** 試算の答え。額は文字（サーバーの Decimal をそのまま文字で受ける） */
export interface InvoicePreview {
  currency: string;
  subtotal: string;
  shipping_fee: string | null;
  tax_amount: string | null;
  tax_rate_percent: string | null;
  duty_amount: string | null;
  duty_label: string | null;
  duty_components: DutyComponent[];
  total_amount: string | null;
  uncomputed: string[];
  incoterms: string;
}

export type ShippingChoice =
  | { mode: "none" }
  | { mode: "calculate"; carrier: string; service_type: string | null; fee: number; currency: string };

export interface PaymentMethodRef {
  method_type: PaymentMethodType;
  id: number | null;
}

export interface InvoicePreviewRequest {
  company_id: number;
  currency: string;
  items: Array<{ quantity: number; unit_price: number }>;
  shipping: ShippingChoice | null;
}

/** 材料の道の path。invoice_id のときは保存した地域と通貨で候補を返す（design.md §3-4） */
export function draftContextPath(companyId: number, contactId: number | null): string {
  return contactId === null
    ? `/invoices/draft-context?company_id=${companyId}`
    : `/invoices/draft-context?company_id=${companyId}&contact_id=${contactId}`;
}

export function draftContextPathForInvoice(invoiceId: number | string): string {
  return `/invoices/draft-context?invoice_id=${invoiceId}`;
}

/** 選択肢の値（Select の value）。bank・wise は版の id、paypal は id なし */
export function paymentKey(p: { method_type: string; id: number | null }): string {
  return `${p.method_type}:${p.id ?? ""}`;
}

/** 支払方法の種類の文言キー（表示名が無いときと、種類を添えるときに使う） */
export const PAYMENT_METHOD_LABEL_KEYS: Readonly<Record<PaymentMethodType, string>> = {
  bank: "invoiceForm.method_bank",
  wise: "invoiceForm.method_wise",
  paypal: "invoiceForm.method_paypal",
};

function listOf<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

/** 通貨に合う支払方法だけ。Wise は wise_currency が請求書の通貨と同じ行だけ（design.md §3-2） */
export function paymentChoicesFor(ctx: DraftContext | null | undefined, currency: string): DraftContextPayment[] {
  return listOf<DraftContextPayment>(ctx?.payment_methods).filter(
    (p) => p.method_type !== "wise" || (currency !== "" && p.wise_currency === currency),
  );
}

/** 選んでいた値がいまの候補に無ければ外す（K3） */
export function effectivePaymentKey(choices: DraftContextPayment[], chosen: string): string {
  return choices.some((p) => paymentKey(p) === chosen) ? chosen : "";
}

export function paymentRefFromKey(choices: DraftContextPayment[], key: string): PaymentMethodRef | null {
  const hit = choices.find((p) => paymentKey(p) === key);
  return hit ? { method_type: hit.method_type, id: hit.id } : null;
}

export function currencyChoices(ctx: DraftContext | null | undefined): string[] {
  return listOf<string>(ctx?.currencies);
}

/**
 * 使う通貨。人か見積が選んだ値があれば、それが候補にあるときだけ使う（黙って別の通貨に替えない）。
 * 選んでいなければ会社の既定の通貨（候補にあるときだけ）。どちらも無ければ ""（未選択）。
 */
export function resolveCurrency(ctx: DraftContext | null | undefined, choice: string): string {
  const list = currencyChoices(ctx);
  if (choice !== "") return list.includes(choice) ? choice : "";
  const fallback = ctx?.default_currency ?? "";
  return fallback !== "" && list.includes(fallback) ? fallback : "";
}

export function fxRateFor(ctx: DraftContext | null | undefined, currency: string): DraftFxRate | null {
  return listOf<DraftFxRate>(ctx?.fx_rates).find((r) => r.currency === currency) ?? null;
}

/** 額の表示。null・空・数でない値は null を返し、部品が「未計算」を出す */
export function formatMoney(value: string | number | null | undefined, currency: string): string | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  try {
    return n.toLocaleString("ja-JP", { style: "currency", currency });
  } catch {
    return `${currency} ${n.toLocaleString()}`;
  }
}

/** 数量は 1 以上の整数（サーバーは int・ge=1） */
export function isValidQuantity(quantity: number): boolean {
  return Number.isInteger(quantity) && quantity >= 1;
}

/** 単価は 0 以上で小数 2 けたまで（サーバーは Decimal・decimal_places=2） */
export function isValidUnitPrice(price: number): boolean {
  return Number.isFinite(price) && price >= 0 && Math.abs(Math.round(price * 100) - price * 100) < 1e-6;
}

/** 作れる明細: 名前があり、数量が整数 1 以上、単価が 0 より大きく小数 2 けたまで（今の作成画面と同じ条件に整数を足した） */
export function isCreatableItem(item: { product_name: string; quantity: number; unit_price: number }): boolean {
  return item.product_name.trim() !== "" && isValidQuantity(item.quantity) && isValidUnitPrice(item.unit_price) && item.unit_price > 0;
}

/** 「未計算」の理由コード → 文言キー。理由の表（apiErrorReason.ts）に無いコードは共通の「未計算」 */
export function uncomputedReasonKey(reason: string): string {
  return Object.prototype.hasOwnProperty.call(API_ERROR_REASON_KEYS, reason)
    ? API_ERROR_REASON_KEYS[reason]
    : "invoiceForm.notComputed";
}

/** 住所を 1 行にする（読むだけの表示） */
export function addressLine(a: DraftAddress | null | undefined): string {
  if (!a) return "";
  return [a.postal_code, a.state, a.city, a.address, a.country].filter((s) => s !== null && s !== undefined && s !== "").join(" ");
}
