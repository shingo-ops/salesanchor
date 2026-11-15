# card: 便D 請求書の作成画面を「選ぶだけ」にする（invoice-create-portfolio）

状態: カード発行（Opus、2026-11-16）。PO の設計承認と実装承認は 2026-11-13「1,（２）決済手数料を合計に足す仕組みは、今回は作りません。別の作業に回します。→次便で」と、同じ日の常設の指示「…確立したなら進める。…PRマージ、デプロイまで完走させてくれ。」（design.md 第9版・審査 APPROVE）。2026-11-15 に PO が「1」で「請求書の画面の作業を先に進め、最後にまとめて見てもらう」を選んだ。
設計: docs/handoff/invoice-create-portfolio/design.md §3-1・§3-2・§4 の便 D・§6・§8 の K1・K2・K3・K4・K5・K8・K10・K11・K12・K19・K23。事実の行番号は docs/handoff/invoice-create-portfolio/recon-cd.md。サーバー側の形（draft-context・preview・理由コード）は card-C.md の D5・D8・D9・D11・D12・D14・D16 のとおり。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `b80c23725` で測った（2026-11-16 の `2cc593393` までに frontend/src の差分なし。backend の差分は secretary_dates と assistant の 5 ファイルだけで、このカードと card-C.md の触るファイルと重ならない）。全部を書き換える 5 ファイルは、書き換える前の中身を `git hash-object` で照合する（手順D2）。
危険便か: いいえ（`migrations/`・`.github/workflows/`・本番の `scripts/` を触らない）。マージ前に Opus の審査役の APPROVE と CI 全通過を必須にする（担当の作業ではない）。
同じ枝: 便 C のコミットの後に、同じ枝 `release/invoice-create-portfolio-bin-cd` に便 D を別のコミットで入れる（card-C.md 冒頭）。枝は取り直さない。便 D のコミットの後で、frontend の型の点検・言葉の点検・試験が全部通ること。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 画面の材料の正本はサーバーの GET /invoices/draft-context だけ（card-C.md D12）。届け先・請求先・担当者・通貨の候補・支払方法の候補・為替・発送元の国は、そこから読んで見せるだけ。画面に通貨の一覧や支払方法の一覧を直書きしない（K2。PO 2026-11-13「ハードコードはなくしてDBから該当する部分を取得するSSOTを採用」design.md:10）。形と小さな関数は新しい frontend/src/lib/invoiceDraftContext.ts の 1 か所にまとめ、作成画面・秘書チャット・詳細画面が同じものを使う。
- D2 合計・税・関税は画面で足し算しない。POST /invoices/preview の答えをそのまま見せる（K8）。入力が止まって 300 ミリ秒後に 1 回だけ取りに行き、答えはどの入力に対する答えかと組で持つ（新しい useInvoicePreview.ts）。答えに「未計算」が 1 つでもある間、または答えが今の入力のものでない間は、作成ボタンを押せない（K4）。未計算の理由は card-C.md D16 の言葉（apiError のキー）で出す。
- D3 送料は打ち込み欄を置かない。「送料を請求しない」か、FedEx の見積から 1 つ選ぶ（K4・K5）。見積の小窓（FedExRateModal）には、発送元の国（draft-context の origin_country_code）・届け先の国と郵便番号・品物の総重量を渡し、その 4 つの欄を読むだけにする（originCountryCode を渡したときだけ。見積の作成画面 QuoteCreatePage.tsx:289-293 は渡さないので今のまま打てる）。選んだ行の会社名を onSelectRate の 4 つ目の引数で返す（足すだけ。今の 3 つの引数の呼び出しはそのまま動く）。
- D4 品物の重さが変わったら、選んだ見積の送料を外し「もう一度選んでください」を出す（K5。古い重さの送料で作らない）。
- D5 通貨を変えたら、新しい通貨で使えない支払方法の選択を外す（K3。Wise は通貨が同じものだけ候補に出る）。
- D6 作る道に送る形は card-C.md D8・D9 のとおり: `shipping`（`{"mode":"none"}` か `{"mode":"calculate","carrier","service_type","fee","currency"}`）と `payment_method_ref`（候補が 0 件なら null）。`shipping_fee`・`tax_amount` は送らない（K12）。作れたら詳細画面へ移る（K12）。
- D7 見出しの並びは 発送先→支払いと合計→商品一覧→クリア・作成（K10）。届け先と請求先の住所は会社の画面で直す（直すボタンで会社の画面へ移る。K1）。請求書を出す側の地域が決まらない（請求先の国が無い）ときは、作れない理由（apiError.billToCountry）と会社の画面へ移るボタンを出し、作成ボタンを押せなくする（今の ADR-1061 便2-2c2a の導線を、作る前に出す形にする）。
- D8 秘書チャットの下書き（SecretaryDraftInvoice.tsx）は送料の見積を出さない。「送料を請求しない」に人がチェックしたときだけ作れる。通貨と支払方法は draft-context の候補から選ぶ。サーバーの 409 `duty_needs_carrier` などは apiError の日本語で出し、請求書を作らない（K19）。
- D9 詳細画面: 支払方法の行は版の表示名（`payment_method_display_name`。card-C.md D14）を先に出し、無ければ今の文字。下書きのときだけ支払方法を選び直す欄（新しい InvoicePaymentPicker.tsx。PATCH の `payment_method_ref` だけを送る）を出す（K23。発行済みには出さない）。
- D10 選び直す欄と作成画面の支払方法は「作る権限と直す権限の両方」を持つ人にだけ出す（design.md §6）。本番の役割では、マネージャーは直す権限だけ、テナント 4・5・6 の営業は作る権限だけを持つ（2026-11-15 に manual-only の鍵で読んだ。/tmp/CC報告ファイル/binc/prod_roles.txt）。設計 §6 は「食い違いがあれば止めて PO へ」なので、Opus は役割を変えず、画面は設計どおり両方の権限で出し、最後の PO の確認で聞く（担当は役割に触らない）。
- D11 画面の言葉は新しい最上位の区切り `invoiceForm`（38 キー）と、`fedexRateModal.colCarrier`・`secretary.invoice.shippingNoneHelp` の 2 つ。ja と en に同じキーで入れる（ADR-027）。生の input・select・textarea・色の直値・新しい `ui-allow` を足さない（ADR-144・K11）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（請求書を作る画面・秘書チャットの下書き・詳細画面の支払方法を「選ぶだけ」にする。サーバーは便 C） |
| 5 | 既存ブランチへの追記ではない | ○（便 C と同じ新しい実装の枝。C→D の順のコミット） |
| 6 | 書式は実例で示した | ○（§2 に新規と全部書き換えのファイルの全文、既存の小さな変更は変更前・変更後） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順D9 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（書き換える前の hash と変更前の文は origin/main `b80c23725` の写しで実測。試験の本数は §2 の全文から数えた） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール（新規と全部書き換えは Write ツール）。プレースホルダを残さない | ○（§2） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（便 D の報告の 1 行目に書く）

`RECEIVED invoice-create-portfolio-D HEAD=`（続けて `git rev-parse HEAD` の 40 桁。便 C のコミットの後の値）。2 行目に「本報告はカード 便D 請求書の作成画面を「選ぶだけ」にする の実行結果である」と書く。

## 0-3. 実装前点検（手順D2 で流す。外れたら実装せず BLOCKED: で停止）

- Q1 枝は `release/invoice-create-portfolio-bin-cd` で、最後のコミットが便 C（題に `invoice-create-portfolio bin C`）。
- Q2 §1 の新規 8 ファイルがどれも無い。
- Q3 全部を書き換える 5 ファイルの今の中身が基準と同じ（`git hash-object` が下の値）:
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx → `a2635433740012bde73d665c65889a71c4557c69`
  - frontend/src/features/secretary/SecretaryDraftInvoice.tsx → `8ac4490f3893c3e1b1dc73934f55866f76e0e319`
  - frontend/src/components/FedExRateModal.tsx → `dd673984cd00033d9e859be352c4742833b97c6a`
  - frontend/src/features/secretary/SecretaryChat.test.tsx → `33efe1087f87cb90f61cd0983bc7de3b2983d823`
  - frontend/src/components/BillToCountryGuidance.test.tsx → `284ea2bf4ac3fe88d5f1ff0e5234baea075211d3`
- Q4 便 C の道が入っている: `grep -c '"/invoices/draft-context"' backend/app/routers/invoices.py` が 1、`grep -c '"/invoices/preview"' backend/app/routers/invoices.py` が 1、`grep -c '"taxRate"' frontend/src/locales/ja.json` が 1。
- Q5 §2 の「変更前」の目印の行が、それぞれのファイルに 1 回ずつある（手順D2 の `grep -c -x -F` がどれも 1）。
- Q6 画面の言葉の区切り `invoiceForm` がまだ無い: `grep -c '"invoiceForm"' frontend/src/locales/ja.json frontend/src/locales/en.json` がどちらも `:0`。

## 1. 触るファイル

1. frontend/src/lib/invoiceDraftContext.ts（新規）
2. frontend/src/lib/invoiceDraftContext.test.ts（新規）
3. frontend/src/pages/invoice-create/useInvoicePreview.ts（新規）
4. frontend/src/pages/invoice-create/InvoiceShipToSection.tsx（新規）
5. frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx（新規）
6. frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx（新規）
7. frontend/src/pages/invoice-detail/InvoicePaymentPicker.tsx（新規）
8. frontend/src/pages/invoice-detail/InvoicePaymentPicker.test.tsx（新規）
9. frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（全部書き換え）
10. frontend/src/features/secretary/SecretaryDraftInvoice.tsx（全部書き換え）
11. frontend/src/components/FedExRateModal.tsx（全部書き換え）
12. frontend/src/features/secretary/SecretaryChat.test.tsx（全部書き換え）
13. frontend/src/components/BillToCountryGuidance.test.tsx（全部書き換え）
14. frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx（4 か所を直す）
15. frontend/src/components/FedExRateModal.test.tsx（2 か所を直す）
16. frontend/src/locales/ja.json（3 か所に足す）
17. frontend/src/locales/en.json（3 か所に足す）
18. 手順D6 の分かれ道に当たったときだけ: frontend/src/lib/query/batch3aPages.test.tsx・frontend/src/lib/query/batch3cPages.test.tsx・frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx・frontend/src/components/AllLegacyButtonOperationMigration.test.tsx・frontend/src/components/CommerceNavigationButtonMigration.test.tsx・frontend/src/components/CommerceSubmitButtonMigration.test.tsx のうち落ちたもの（§4 の決まった直し方だけ）

触らない: 上に無いファイル全部。特に backend/ の全部（便 C で済み）・migrations/・.github/workflows/・frontend/src/components/ の金型（Select・Button・Callout・TextField・Checkbox・Modal）・frontend/src/pages/quote-create/・frontend/api-contract/。

## 2. 変更

新規の 8 ファイルと全部書き換えの 5 ファイルは、下の全文を Write ツールでそのまま書く（足しも引きもしない）。

### 2-1. frontend/src/lib/invoiceDraftContext.ts（新規。全文）

```ts
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
```

### 2-2. frontend/src/lib/invoiceDraftContext.test.ts（新規。全文）

```ts
// invoice-create-portfolio 便D: 請求書の材料から候補を作る関数（design.md §3-2・§8 K2/K3）
import { describe, expect, it } from "vitest";
import {
  currencyChoices,
  draftContextPath,
  draftContextPathForInvoice,
  effectivePaymentKey,
  formatMoney,
  fxRateFor,
  isCreatableItem,
  isValidQuantity,
  isValidUnitPrice,
  paymentChoicesFor,
  paymentKey,
  paymentRefFromKey,
  resolveCurrency,
  uncomputedReasonKey,
  addressLine,
  type DraftContext,
} from "./invoiceDraftContext";

const CTX: DraftContext = {
  company_id: 4,
  ship_to: null,
  bill_to: null,
  contact_name: null,
  contact_email: null,
  issuer_region: "JP",
  origin_country_code: "JP",
  destination_country_code: "US",
  destination_postal_code: "10001",
  currencies: ["JPY", "USD"],
  fx_rates: [{ currency: "USD", rate: 150.5, fetched_at: "2026-11-15T00:00:00Z" }],
  default_currency: "USD",
  currency: null,
  payment_methods: [
    { id: 3, method_type: "bank", display_name: "Main bank", wise_currency: null },
    { id: 4, method_type: "wise", display_name: "Wise USD", wise_currency: "USD" },
    { id: null, method_type: "paypal", display_name: null, wise_currency: null },
  ],
  tax_rate_percent: null,
  incoterms: "DAP",
};

describe("invoiceDraftContext", () => {
  it("builds the draft-context paths", () => {
    expect(draftContextPath(4, null)).toBe("/invoices/draft-context?company_id=4");
    expect(draftContextPath(4, 5)).toBe("/invoices/draft-context?company_id=4&contact_id=5");
    expect(draftContextPathForInvoice(9)).toBe("/invoices/draft-context?invoice_id=9");
  });

  it("K3: Wise rows are offered only for their own currency", () => {
    expect(paymentChoicesFor(CTX, "USD").map(paymentKey)).toEqual(["bank:3", "wise:4", "paypal:"]);
    expect(paymentChoicesFor(CTX, "JPY").map(paymentKey)).toEqual(["bank:3", "paypal:"]);
    expect(paymentChoicesFor(CTX, "").map(paymentKey)).toEqual(["bank:3", "paypal:"]);
    expect(paymentChoicesFor(null, "USD")).toEqual([]);
  });

  it("K3: a choice that left the list is cleared", () => {
    expect(effectivePaymentKey(paymentChoicesFor(CTX, "USD"), "wise:4")).toBe("wise:4");
    expect(effectivePaymentKey(paymentChoicesFor(CTX, "JPY"), "wise:4")).toBe("");
  });

  it("turns a key back into the reference sent to the server", () => {
    const choices = paymentChoicesFor(CTX, "USD");
    expect(paymentRefFromKey(choices, "bank:3")).toEqual({ method_type: "bank", id: 3 });
    expect(paymentRefFromKey(choices, "paypal:")).toEqual({ method_type: "paypal", id: null });
    expect(paymentRefFromKey(choices, "bank:99")).toBeNull();
  });

  it("K2: currency comes only from the server list", () => {
    expect(currencyChoices(CTX)).toEqual(["JPY", "USD"]);
    expect(resolveCurrency(CTX, "")).toBe("USD");
    expect(resolveCurrency(CTX, "JPY")).toBe("JPY");
    expect(resolveCurrency(CTX, "EUR")).toBe("");
    expect(resolveCurrency({ ...CTX, default_currency: "EUR" }, "")).toBe("");
    expect(resolveCurrency(null, "USD")).toBe("");
  });

  it("finds the exchange rate row", () => {
    expect(fxRateFor(CTX, "USD")?.rate).toBe(150.5);
    expect(fxRateFor(CTX, "JPY")).toBeNull();
  });

  it("formats money and returns null for missing values", () => {
    expect(formatMoney(null, "USD")).toBeNull();
    expect(formatMoney("", "USD")).toBeNull();
    expect(formatMoney("abc", "USD")).toBeNull();
    expect(formatMoney("1234.5", "USD")).not.toBeNull();
  });

  it("checks quantity, price and creatable rows", () => {
    expect(isValidQuantity(1)).toBe(true);
    expect(isValidQuantity(0)).toBe(false);
    expect(isValidQuantity(1.5)).toBe(false);
    expect(isValidUnitPrice(10.25)).toBe(true);
    expect(isValidUnitPrice(10.255)).toBe(false);
    expect(isValidUnitPrice(-1)).toBe(false);
    expect(isCreatableItem({ product_name: "Card", quantity: 2, unit_price: 10 })).toBe(true);
    expect(isCreatableItem({ product_name: " ", quantity: 2, unit_price: 10 })).toBe(false);
    expect(isCreatableItem({ product_name: "Card", quantity: 2, unit_price: 0 })).toBe(false);
  });

  it("maps uncomputed reasons to wording keys", () => {
    expect(uncomputedReasonKey("tax_rate")).toBe("apiError.taxRate");
    expect(uncomputedReasonKey("no_such_reason")).toBe("invoiceForm.notComputed");
  });

  it("joins an address into one line", () => {
    expect(addressLine(null)).toBe("");
    expect(
      addressLine({ company_name: null, billing_display_name: null, label: null, postal_code: "10001", address: "1 Main St", city: "New York", state: "NY", country: "US", phone: null }),
    ).toBe("10001 NY New York 1 Main St US");
  });
});
```

### 2-3. frontend/src/pages/invoice-create/useInvoicePreview.ts（新規。全文）

```ts
/**
 * 請求書の試算（POST /invoices/preview）を、入力が止まって 300 ミリ秒後に 1 回だけ取りに行く
 * （invoice-create-portfolio 便D・design.md §3-2）。
 *
 * 合計・税・関税の計算はサーバーだけが行う（画面で足し算しない）。
 * 答えは「どの入力に対する答えか（key）」と組で持ち、入力が変わった瞬間に古い答えは使わない（fresh=false）。
 * request が null のとき（会社・通貨・明細がそろわないとき）は取りに行かない。
 */
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import type { InvoicePreview, InvoicePreviewRequest } from "../../lib/invoiceDraftContext";

const PREVIEW_DELAY_MS = 300;

interface PreviewAnswer {
  key: string;
  data: InvoicePreview | null;
  error: string;
}

export interface InvoicePreviewState {
  /** いまの入力に対する答え。まだ届いていない・入力が変わった直後は null */
  preview: InvoicePreview | null;
  /** いまの入力に対する失敗の文（api が文言にしたもの） */
  error: string;
  /** いまの入力に対する答えが届いているか */
  fresh: boolean;
}

export function useInvoicePreview(request: InvoicePreviewRequest | null): InvoicePreviewState {
  const key = request === null ? "" : JSON.stringify(request);
  const [answer, setAnswer] = useState<PreviewAnswer>({ key: "", data: null, error: "" });
  const seq = useRef(0);

  useEffect(() => {
    if (key === "") return undefined;
    const mine = ++seq.current;
    const timer = setTimeout(() => {
      api
        .post<InvoicePreview>("/invoices/preview", JSON.parse(key) as InvoicePreviewRequest)
        .then((data) => {
          if (seq.current === mine) setAnswer({ key, data, error: "" });
        })
        .catch((e: unknown) => {
          if (seq.current === mine) {
            setAnswer({ key, data: null, error: e instanceof Error ? e.message : String(e) });
          }
        });
    }, PREVIEW_DELAY_MS);
    return () => clearTimeout(timer);
  }, [key]);

  const fresh = key !== "" && answer.key === key;
  return {
    preview: fresh ? answer.data : null,
    error: fresh ? answer.error : "",
    fresh,
  };
}
```

### 2-4. frontend/src/pages/invoice-create/InvoiceShipToSection.tsx（新規。全文）

```tsx
/**
 * 請求書作成ページの「届け先・請求先」の区切り（invoice-create-portfolio 便D・design.md §3-2）。
 *
 * 住所・担当者は会社の画面で登録した値を読んで見せるだけ（この画面では打たない・K1）。
 * 直したいときは会社の画面へ移るボタンを出す。
 * 請求書を出す側の地域（issuer_region）が決まらないときは、作成できない理由と会社の画面への道を出す。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { addressLine, type DraftContext } from "../../lib/invoiceDraftContext";

export interface InvoiceShipToSectionProps {
  companyId: number;
  ctx: DraftContext | null;
  loading: boolean;
  errorText: string;
}

export function InvoiceShipToSection({ companyId, ctx, loading, errorText }: InvoiceShipToSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const openCompany = () => navigate(`/crm/companies/${companyId}`);

  if (errorText !== "") {
    return (
      <div data-testid="invoice-ship-to">
        <Callout variant="warning" title={t("invoiceForm.contextError")}>
          <p data-testid="invoice-context-error">{errorText}</p>
        </Callout>
      </div>
    );
  }
  if (ctx === null) {
    return (
      <div data-testid="invoice-ship-to">
        <p style={{ color: "var(--text-secondary)" }}>{loading ? t("common.loading") : t("invoiceForm.chooseCompany")}</p>
      </div>
    );
  }

  const shipTo = addressLine(ctx.ship_to);
  const billTo = addressLine(ctx.bill_to);
  return (
    <div data-testid="invoice-ship-to">
      {ctx.issuer_region === null && (
        <Callout variant="warning" title={t("apiError.billToCountry")}>
          <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company-for-bill-to">
            {t("invoices.openCompanyForBillTo")}
          </Button>
        </Callout>
      )}
      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "var(--space-2) var(--space-4)", margin: "var(--space-3) 0" }}>
        <dt>{t("invoiceForm.shipTo")}</dt>
        <dd data-testid="invoice-ship-to-address">{shipTo !== "" ? shipTo : t("invoiceForm.noAddress")}</dd>
        <dt>{t("invoiceForm.billTo")}</dt>
        <dd data-testid="invoice-bill-to-address">{billTo !== "" ? billTo : t("invoiceForm.noAddress")}</dd>
        <dt>{t("invoiceForm.contact")}</dt>
        <dd data-testid="invoice-contact-line">
          {[ctx.contact_name, ctx.contact_email].filter((s) => s !== null && s !== "").join(" / ") || t("invoiceForm.noAddress")}
        </dd>
      </dl>
      <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company">
        {t("invoiceForm.openCompany")}
      </Button>
    </div>
  );
}
```

### 2-5. frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx（新規。全文）

```tsx
/**
 * 請求書作成ページの「通貨・支払方法・送料・合計」の区切り（invoice-create-portfolio 便D・design.md §3-2）。
 *
 * 人は選ぶだけ。通貨・支払方法の候補はサーバーの材料（draft-context）だけから出す（直書きしない）。
 * 送料は「送料を請求しない」か、FedEx の見積を出して 1 つ選ぶ（打ち込み欄は置かない・K4）。
 * 合計・税・関税はサーバーの試算（preview）の答えをそのまま見せる。答えが無い所は「未計算」と理由を出す（K5）。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Select } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import { FedExRateModal } from "../../components/FedExRateModal";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  formatMoney,
  fxRateFor,
  paymentKey,
  uncomputedReasonKey,
  type DraftContext,
  type DraftContextPayment,
  type InvoicePreview,
  type ShippingChoice,
} from "../../lib/invoiceDraftContext";

export interface InvoicePaymentTotalsSectionProps {
  ctx: DraftContext | null;
  currencyOptions: string[];
  currency: string;
  onCurrencyChange: (next: string) => void;
  paymentChoices: DraftContextPayment[];
  paymentValue: string;
  onPaymentChange: (next: string) => void;
  notes: string;
  onNotesChange: (next: string) => void;
  shipping: ShippingChoice | null;
  shippingStale: boolean;
  onShippingNone: () => void;
  onShippingClear: () => void;
  quoteOpen: boolean;
  onQuoteOpen: () => void;
  onQuoteClose: () => void;
  onRateSelected: (fee: number, rateCurrency: string, serviceType: string | null, carrier: string) => void;
  totalWeight: number;
  preview: InvoicePreview | null;
  previewError: string;
}

export function InvoicePaymentTotalsSection(props: InvoicePaymentTotalsSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    ctx, currencyOptions, currency, onCurrencyChange, paymentChoices, paymentValue, onPaymentChange,
    notes, onNotesChange, shipping, shippingStale, onShippingNone, onShippingClear,
    quoteOpen, onQuoteOpen, onQuoteClose, onRateSelected, totalWeight, preview, previewError,
  } = props;

  const fx = currency !== "" ? fxRateFor(ctx, currency) : null;
  const paymentLabel = (p: DraftContextPayment) =>
    p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]);
  const canQuote = ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null;
  const shippingSelectValue = shipping === null ? "" : shipping.mode;
  const money = (v: string | null | undefined) => formatMoney(v, currency) ?? t("invoiceForm.notComputed");

  return (
    <div data-testid="invoice-payment-totals">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
        <div>
          <Select
            label={t("invoiceForm.currency")}
            required
            fullWidth
            value={currency}
            onChange={(e) => onCurrencyChange(e.target.value)}
            placeholder={t("invoiceForm.currencyPlaceholder")}
            options={currencyOptions.map((c) => ({ value: c, label: c }))}
            data-testid="invoice-currency-select"
          />
          {currencyOptions.length === 0 && ctx !== null && (
            <p data-testid="invoice-no-currency">{t("invoiceForm.noCurrency")}</p>
          )}
          {fx !== null && (
            <p style={{ color: "var(--text-secondary)" }} data-testid="invoice-fx-line">
              {t("invoiceForm.fxRateLine", { currency: fx.currency, rate: fx.rate, at: fx.fetched_at ?? "-" })}
            </p>
          )}
        </div>
        <div>
          {paymentChoices.length > 0 ? (
            <Select
              label={t("invoiceForm.payment")}
              required
              fullWidth
              value={paymentValue}
              onChange={(e) => onPaymentChange(e.target.value)}
              placeholder={t("invoiceForm.paymentPlaceholder")}
              options={paymentChoices.map((p) => ({ value: paymentKey(p), label: paymentLabel(p) }))}
              data-testid="invoice-payment-select"
            />
          ) : ctx !== null && ctx.issuer_region !== null ? (
            <Callout variant="info" title={t("invoiceForm.noPaymentMethods")}>
              <Button type="button" variant="secondary" size="sm" onClick={() => navigate("/management-center/tenant-profile")} data-testid="invoice-open-tenant-profile">
                {t("invoiceForm.openTenantProfile")}
              </Button>
            </Callout>
          ) : null}
        </div>
      </div>

      <div className="form-group" style={{ marginBottom: "var(--space-4)" }}>
        <label>{t("common.notes")}</label>
        <TextFieldControl value={notes} onChange={(e) => onNotesChange(e.target.value)} data-testid="invoice-notes" />
      </div>

      <div style={{ marginBottom: "var(--space-4)" }}>
        <Select
          label={t("invoiceForm.shipping")}
          required
          value={shippingSelectValue}
          onChange={(e) => {
            if (e.target.value === "none") onShippingNone();
            else onShippingClear();
          }}
          placeholder={t("invoiceForm.shippingPlaceholder")}
          options={[
            { value: "none", label: t("invoiceForm.shippingNone") },
            ...(shipping !== null && shipping.mode === "calculate"
              ? [{ value: "calculate", label: t("invoiceForm.shippingChosen", { carrier: shipping.carrier, service: shipping.service_type ?? "-", fee: formatMoney(shipping.fee, shipping.currency) ?? String(shipping.fee) }) }]
              : []),
          ]}
          data-testid="invoice-shipping-select"
        />
        <div style={{ marginTop: "var(--space-2)" }}>
          <Button type="button" variant="secondary" size="sm" onClick={onQuoteOpen} disabled={!canQuote} data-testid="invoice-shipping-quote">
            {t("invoiceForm.shippingQuote")}
          </Button>
        </div>
        {!canQuote && ctx !== null && (
          <p style={{ color: "var(--text-secondary)" }} data-testid="invoice-shipping-needs-countries">{t("invoiceForm.shippingNeedsCountries")}</p>
        )}
        {shippingStale && (
          <p className="warning-message" data-testid="invoice-shipping-stale">{t("invoiceForm.shippingStale")}</p>
        )}
        {quoteOpen && ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null && (
          <FedExRateModal
            open={quoteOpen}
            onClose={onQuoteClose}
            originCountryCode={ctx.origin_country_code}
            destinationCountryCode={ctx.destination_country_code}
            destinationPostalCode={ctx.destination_postal_code ?? undefined}
            weightKg={totalWeight}
            onSelectRate={(fee, rateCurrency, serviceType, carrier) => onRateSelected(fee, rateCurrency, serviceType, carrier ?? "")}
          />
        )}
      </div>

      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "var(--space-2) var(--space-4)", marginBottom: "var(--space-4)" }}>
        <dt>{t("invoiceForm.totalWeight")}</dt>
        <dd data-testid="invoice-total-weight">{totalWeight.toLocaleString()} kg</dd>
        <dt>{t("invoiceForm.subtotal")}</dt>
        <dd data-testid="invoice-total-subtotal">{preview ? money(preview.subtotal) : t("invoiceForm.notComputed")}</dd>
        <dt>{t("invoiceForm.shippingFee")}</dt>
        <dd data-testid="invoice-total-shipping">{preview ? money(preview.shipping_fee) : t("invoiceForm.notComputed")}</dd>
        <dt>{t("invoiceForm.tax", { rate: preview?.tax_rate_percent ?? "-" })}</dt>
        <dd data-testid="invoice-total-tax">{preview ? money(preview.tax_amount) : t("invoiceForm.notComputed")}</dd>
        <dt>{preview?.duty_label ?? t("invoiceForm.duty")}</dt>
        <dd data-testid="invoice-total-duty">
          {preview ? money(preview.duty_amount) : t("invoiceForm.notComputed")}
          {preview && preview.duty_components.length > 0 && (
            <ul data-testid="invoice-duty-components">
              {preview.duty_components.map((c, i) => (
                <li key={i}>{c.label}: {money(c.amount)}</li>
              ))}
            </ul>
          )}
        </dd>
        <dt>{t("invoiceForm.total")}</dt>
        <dd data-testid="invoice-total-amount" style={{ fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>
          {preview ? money(preview.total_amount) : t("invoiceForm.notComputed")}
        </dd>
      </dl>
      {preview && preview.uncomputed.length > 0 && (
        <Callout variant="warning" title={t("invoiceForm.uncomputedTitle")}>
          <ul data-testid="invoice-uncomputed">
            {preview.uncomputed.map((r) => (
              <li key={r} data-testid={`invoice-uncomputed-${r}`}>{t(uncomputedReasonKey(r))}</li>
            ))}
          </ul>
        </Callout>
      )}
      {previewError !== "" && (
        <p className="error-message" data-testid="invoice-preview-error">{previewError}</p>
      )}
    </div>
  );
}
```

### 2-6. frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（全部書き換え。全文）

```tsx
/**
 * 請求書作成ページ。2 つの導線:
 *   1. 在庫表から: 在庫表でチェックした商品が location.state で渡る（往復対応）。
 *   2. 既存見積から: 承認済み見積を選ぶと、その明細を編集可能なフォームへ読み込む（ADR-093 2026-06-03）。
 *
 * invoice-create-portfolio 便D（design.md §3-2）: 人は金額を打たずに選ぶだけ。
 *   - 届け先・請求先・担当者は会社の画面の登録を読んで見せるだけ（GET /invoices/draft-context）。
 *   - 通貨・支払方法の候補は同じ材料から出す（画面に通貨や支払方法を直書きしない）。
 *   - 送料は「送料を請求しない」か FedEx の見積の 1 つを選ぶ。送料・税の打ち込み欄は置かない。
 *   - 合計・税・関税はサーバーの試算（POST /invoices/preview）の答えを見せる。画面で足し算しない。
 *   - 試算に「未計算」が 1 つでも残る間は作成ボタンを押せない。
 *
 * 明細エディタは QuoteCreatePage と同一仕様。共通ロジックは ../quote-create/quoteDraft。
 */
import { useState, FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import { PageLayout } from "../../components/PageLayout";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import InventorySearchBar, { InventorySearchCandidate } from "../../components/InventorySearchBar";
import { Button } from "../../components/Button";
import {
  type LineItem,
  type QuoteHandoffState,
  blankItem,
  buildInitialItems,
  weightForUnit,
} from "../quote-create/quoteDraft";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock } from "../../components/loading";
import {
  currencyChoices,
  draftContextPath,
  effectivePaymentKey,
  formatMoney,
  isCreatableItem,
  isValidQuantity,
  isValidUnitPrice,
  paymentChoicesFor,
  paymentRefFromKey,
  resolveCurrency,
  type DraftContext,
  type InvoicePreviewRequest,
  type ShippingChoice,
} from "../../lib/invoiceDraftContext";
import { useInvoicePreview } from "./useInvoicePreview";
import { InvoiceShipToSection } from "./InvoiceShipToSection";
import { InvoicePaymentTotalsSection } from "./InvoicePaymentTotalsSection";

interface QuoteSummary {
  id: number;
  quote_code: string;
  company_id: number;
  currency: string;
  total_amount: number | null;
  status: string;
  created_at: string;
}

// GET /quotes/{id}（QuoteDetailResponse）の使用フィールドのみ。
interface QuoteDetail {
  id: number;
  quote_code: string | null;
  company_id: number;
  contact_id: number | null;
  currency: string;
  items: Array<{
    product_id: number | null;
    product_name: string;
    name_en?: string | null;
    condition?: string | null;
    unit?: string | null;
    quantity: number;
    unit_price: number;
    weight: number | null;
  }>;
}

/** 材料の答えが請求書の材料の形（object）のときだけ使う。配列などは「まだ無い」と同じに扱う */
function asDraftContext(data: unknown): DraftContext | null {
  return data !== null && typeof data === "object" && !Array.isArray(data) ? (data as DraftContext) : null;
}

export default function InvoiceCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const handoff = location.state as QuoteHandoffState;
  const draft = handoff?.draft;

  // 見積選択モードで開始（往復フロー廃止）。
  const [mode, setMode] = useState<"inventory" | "quote">("quote");

  // --- 編集フォーム（在庫表から / 見積から編集 で共通） ---
  const [companyId, setCompanyId] = useState<number | null>(draft?.companyId ?? null);
  const [contactId, setContactId] = useState<number | null>(draft?.contactId ?? null);
  const [selectorError, setSelectorError] = useState("");
  // 人か見積が選んだ通貨。使う通貨は材料の候補にあるときだけ（resolveCurrency）。
  const [currencyChoice, setCurrencyChoice] = useState<string>(draft?.currency ?? "");
  const [paymentChoice, setPaymentChoice] = useState("");
  const [shipping, setShipping] = useState<ShippingChoice | null>(null);
  // FedEx の見積を選んだときの総重量。明細の重さが変わったら選び直しを求める。
  const [shippingWeight, setShippingWeight] = useState<number | null>(null);
  const [quoteOpen, setQuoteOpen] = useState(false);
  const [notes, setNotes] = useState(draft?.notes ?? "");
  const [items, setItems] = useState<LineItem[]>(() => buildInitialItems(handoff));
  // #8: どの見積から読み込んだか（編集中の見積コード表示用）。
  const [sourceQuoteCode, setSourceQuoteCode] = useState<string | null>(null);

  // --- 見積選択モード ---
  const quotesQ = useApiQuery<QuoteSummary[]>("/quotes?status=approved", { enabled: mode === "quote" });
  const quotes = quotesQ.data ?? [];
  const quotesLoading = quotesQ.isPending;

  // --- 請求書の材料（会社を選んだときだけ取りに行く） ---
  const ctxQ = useApiQuery<DraftContext>(
    companyId !== null ? draftContextPath(companyId, contactId) : "/invoices/draft-context",
    { enabled: mode === "inventory" && companyId !== null },
  );
  const ctx = companyId !== null ? asDraftContext(ctxQ.data) : null;
  const ctxError = companyId !== null && ctxQ.error ? (ctxQ.error instanceof Error ? ctxQ.error.message : t("common.fetchError")) : "";

  const [error, setError] = useState("");
  const shownError = error || (mode === "quote" && quotesQ.error ? (quotesQ.error instanceof Error ? quotesQ.error.message : t("common.fetchError")) : "");
  const [saving, setSaving] = useState(false);

  const addItem = () => setItems((prev) => [...prev, { ...blankItem }]);
  const removeItem = (index: number) => {
    setItems((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));
  };
  const updateItem = (index: number, field: keyof LineItem, value: unknown) => {
    setItems((prev) => {
      const next = [...prev];
      (next[index] as unknown as Record<string, unknown>)[field] = value;
      return next;
    });
  };
  // 「検索して追加」: 選択商品を新しい明細行として追加（上書きではない）。
  const appendFromSearch = (c: InventorySearchCandidate) => {
    const isOutOfStock = c.stock_quantity !== null && c.stock_quantity <= 0;
    setItems((prev) => [
      ...prev,
      {
        product_id: c.product_id,
        product_name: c.name,
        name_en: c.name_en ?? null,
        condition: null,
        unit: null,
        quantity: isOutOfStock ? 0 : 1,
        unit_price: c.unit_price ?? 0,
        box_weight_kg: c.box_weight_kg ?? null,
        case_weight_kg: c.case_weight_kg ?? null,
        weight: null,
        inventory_id: null,
        zero_stock_warning: isOutOfStock,
      },
    ]);
  };
  // 会社・担当者が変わったら、前の会社に合わせて選んだ送料と支払方法を外す（K3）。
  const changeCompanyContact = (nextCompanyId: number | null, nextContactId: number | null) => {
    if (nextCompanyId !== companyId || nextContactId !== contactId) {
      setShipping(null);
      setShippingWeight(null);
      setPaymentChoice("");
    }
    setCompanyId(nextCompanyId);
    setContactId(nextContactId);
  };
  // #8: 承認済み見積を編集可能な明細としてフォームへ読み込む。
  const loadQuoteForEdit = async (quoteId: number) => {
    setError("");
    setSaving(true);
    try {
      const q = await api.get<QuoteDetail>(`/quotes/${quoteId}`);
      changeCompanyContact(q.company_id, q.contact_id ?? null);
      setCurrencyChoice(q.currency);
      setItems(
        q.items.length > 0
          ? q.items.map((it) => ({
              product_id: it.product_id,
              product_name: it.product_name,
              name_en: it.name_en ?? null,
              condition: it.condition ?? null,
              unit: it.unit ?? null,
              quantity: it.quantity,
              unit_price: it.unit_price,
              weight: it.weight ?? null,
              inventory_id: null,
            }))
          : [{ ...blankItem }],
      );
      setSourceQuoteCode(q.quote_code ?? null);
      setMode("inventory");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setSaving(false);
    }
  };
  // 入れたものを全部消して最初の状態に戻す。
  const clearAll = () => {
    changeCompanyContact(null, null);
    setSelectorError("");
    setCurrencyChoice("");
    setNotes("");
    setItems([{ ...blankItem }]);
    setSourceQuoteCode(null);
    setQuoteOpen(false);
    setError("");
  };

  // 総重量 = Σ(数量 × 行重量)。重量未設定の行は 0 扱い（送料の見積に渡す重さ）。
  const totalWeight = items.reduce((s, it) => s + it.quantity * (it.weight ?? 0), 0);
  const currency = resolveCurrency(ctx, currencyChoice);
  const paymentChoices = paymentChoicesFor(ctx, currency);
  const paymentValue = effectivePaymentKey(paymentChoices, paymentChoice);
  const shippingStale = shipping !== null && shipping.mode === "calculate" && shippingWeight !== totalWeight;
  const effectiveShipping = shippingStale ? null : shipping;
  const itemsValid = items.length > 0 && items.every((i) => isValidQuantity(i.quantity) && isValidUnitPrice(i.unit_price));

  const previewRequest: InvoicePreviewRequest | null =
    mode === "inventory" && ctx !== null && companyId !== null && currency !== "" && itemsValid
      ? {
          company_id: companyId,
          currency,
          items: items.map((i) => ({ quantity: i.quantity, unit_price: i.unit_price })),
          shipping: effectiveShipping,
        }
      : null;
  const { preview, error: previewError, fresh } = useInvoicePreview(previewRequest);

  const canCreate =
    companyId !== null &&
    contactId !== null &&
    ctx !== null &&
    ctx.issuer_region !== null &&
    currency !== "" &&
    items.length > 0 &&
    items.every(isCreatableItem) &&
    effectiveShipping !== null &&
    (paymentChoices.length === 0 || paymentValue !== "") &&
    fresh &&
    preview !== null &&
    preview.uncomputed.length === 0 &&
    !saving;

  const submitInvoice = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSelectorError("");
    if (contactId === null) {
      setSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    if (!items.every(isCreatableItem)) {
      setError(t("quotes.itemsRequired"));
      return;
    }
    if (!canCreate || effectiveShipping === null) return;
    setSaving(true);
    try {
      const inv = await api.post<{ id: number }>("/invoices", {
        company_id: companyId,
        contact_id: contactId,
        currency,
        shipping: effectiveShipping,
        payment_method_ref: paymentRefFromKey(paymentChoices, paymentValue),
        notes: notes || null,
        items: items.map((i) => ({
          product_id: i.product_id,
          product_name: i.product_name,
          name_en: i.name_en ?? null,
          condition: i.condition ?? null,
          unit: i.unit ?? null,
          quantity: i.quantity,
          unit_price: i.unit_price,
          weight: i.weight,
        })),
      });
      navigate(`/invoices/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageLayout
      titleText={t("invoices.createTitle")}
      subtitleKey="invoices.createSubtitle"
      headerAction={
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <Button variant="secondary" size="md" onClick={() => navigate("/management-center/tenant-profile")}>
            {t("nav.tenantProfile")}
          </Button>
        </div>
      }
    >

      {shownError && <div className="error-message" data-testid="invoice-error">{shownError}</div>}

      <div style={{ display: "flex", gap: "var(--space-2)", margin: "var(--space-3) 0" }}>
        <Button variant={mode === "inventory" ? "primary" : "secondary"} size="md"

          onClick={() => setMode("inventory")}
          data-testid="invoice-mode-inventory"
        >
          {t("invoices.fromInventory")}
        </Button>
        <Button variant={mode === "quote" ? "primary" : "secondary"} size="md"

          onClick={() => { setSourceQuoteCode(null); setError(""); setMode("quote"); }}
          data-testid="invoice-mode-quote"
        >
          {t("invoices.fromQuote")}
        </Button>
      </div>

      {mode === "quote" ? (
        <div data-testid="invoice-from-quote">
          <p style={{ color: "var(--text-secondary)" }}>{t("invoices.fromQuoteHelp")}</p>
          {quotesLoading ? (
            <LoadingBlock />
          ) : quotes.length === 0 ? (
            <div className="empty">{t("invoices.noApprovedQuotes")}</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("quotes.quoteCode")}</th>
                  <th>{t("quotes.total")}</th>
                  <th>{t("common.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((q) => (
                  <tr key={q.id} data-testid={`invoice-quote-${q.id}`}>
                    <td>{q.quote_code}</td>
                    <td>{formatMoney(q.total_amount, q.currency) ?? "-"}</td>
                    <td>
                      <Button
                        variant="primary" size="sm"
                        disabled={saving}
                        onClick={() => loadQuoteForEdit(q.id)}
                        data-testid={`invoice-edit-from-quote-${q.id}`}
                      >
                        {t("invoices.editFromThisQuote")}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : (
        <form
          onSubmit={submitInvoice}
          style={{ background: "var(--bg-surface)", padding: "var(--space-6)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)" }}
        >
          {sourceQuoteCode && (
            <div className="info-message" data-testid="invoice-source-quote" style={{ marginBottom: "var(--space-4)" }}>
              {t("invoices.editingFromQuote", { code: sourceQuoteCode })}
            </div>
          )}

          <h3 style={{ marginBottom: "var(--space-3)" }}>{t("invoiceForm.sectionShipTo")}</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
            <CompanyContactSelector
              value={{ companyId, contactId }}
              onChange={({ companyId: c, contactId: ct }) => changeCompanyContact(c, ct)}
              required
              error={selectorError}
            />
          </div>
          {companyId !== null && (
            <div style={{ marginBottom: "var(--space-6)" }}>
              <InvoiceShipToSection companyId={companyId} ctx={ctx} loading={ctxQ.isPending} errorText={ctxError} />
            </div>
          )}

          <h3 style={{ marginBottom: "var(--space-3)" }}>{t("invoiceForm.sectionPaymentTotals")}</h3>
          <div style={{ marginBottom: "var(--space-6)" }}>
            <InvoicePaymentTotalsSection
              ctx={ctx}
              currencyOptions={currencyChoices(ctx)}
              currency={currency}
              onCurrencyChange={(next) => { setCurrencyChoice(next); setPaymentChoice(""); }}
              paymentChoices={paymentChoices}
              paymentValue={paymentValue}
              onPaymentChange={setPaymentChoice}
              notes={notes}
              onNotesChange={setNotes}
              shipping={shipping}
              shippingStale={shippingStale}
              onShippingNone={() => { setShipping({ mode: "none" }); setShippingWeight(null); }}
              onShippingClear={() => { setShipping(null); setShippingWeight(null); }}
              quoteOpen={quoteOpen}
              onQuoteOpen={() => setQuoteOpen(true)}
              onQuoteClose={() => setQuoteOpen(false)}
              onRateSelected={(fee, rateCurrency, serviceType, carrier) => {
                if (carrier === "") return;
                setShipping({
                  mode: "calculate",
                  carrier,
                  service_type: serviceType,
                  fee: Math.round(Number(fee) * 100) / 100,
                  currency: rateCurrency,
                });
                setShippingWeight(totalWeight);
              }}
              totalWeight={totalWeight}
              preview={preview}
              previewError={previewError}
            />
          </div>

          <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
          {/* 明細ゾーン: 行内検索/AND-OR は廃止。商品名は自由記入可。 */}
          <div style={{ overflowX: "auto", marginBottom: "var(--space-4)" }}>
            <table className="data-table" style={{ minWidth: "var(--table-min-width-base)" }}>
              <thead>
                <tr>
                  <th>{t("quotes.titleColumn")}</th>
                  <th>{t("quotes.condition")}</th>
                  <th>{t("quotes.unit")}</th>
                  <th>{t("quotes.quantity")}</th>
                  <th>{t("quotes.unitPrice")}</th>
                  <th>{t("quotes.weight")}</th>
                  <th>{t("quotes.subtotal")}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr key={i} data-testid={`invoice-item-row-${i}`}>
                    <td style={{ minWidth: "var(--table-col-product-name-min-w)" }}>
                      {/* 英語タイトル(name_en)をメイン(太字)、日本語(product_name)を参考表示。 */}
                      <TextFieldControl size="sm"
                        value={item.name_en ?? ""}
                        onChange={(e) => updateItem(i, "name_en", e.target.value || null)}
                        placeholder={t("quotes.titleColumn")}
                        style={{ width: "100%", minWidth: "var(--input-width-product-name)", fontWeight: "var(--font-weight-semi)" }}
                        data-testid={`invoice-item-row-${i}-name-en`}
                      />
                      <TextFieldControl size="sm"
                        value={item.product_name}
                        onChange={(e) => updateItem(i, "product_name", e.target.value)}
                        placeholder={t("quotes.productNamePlaceholder")}
                        style={{ width: "100%", minWidth: "var(--input-width-product-name)", marginTop: "var(--space-1)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}
                        data-testid={`invoice-item-row-${i}-name`}
                      />
                      {item.zero_stock_warning && (
                        <div
                          data-testid={`invoice-item-row-${i}-zero-stock-warning`}
                          className="warning-message"
                          style={{ marginTop: "var(--space-1)", color: "var(--color-warning)", fontSize: "var(--font-sm)" }}
                        >
                          {t("inventory.search.zeroStockWarning", { name: item.product_name })}
                        </div>
                      )}
                    </td>
                    <td>
                      <TextFieldControl size="sm" value={item.condition ?? ""} onChange={(e) => updateItem(i, "condition", e.target.value || null)} placeholder={t("quotes.condition")} style={{ width: "var(--input-width-weight)" }} data-testid={`invoice-item-row-${i}-condition`} />
                    </td>
                    <td>
                      {/* 形態(unit)変更時はマスタ重量を引き込み直す。 */}
                      <TextFieldControl size="sm"
                        value={item.unit ?? ""}
                        onChange={(e) => {
                          const nextUnit = e.target.value || null;
                          updateItem(i, "unit", nextUnit);
                          updateItem(i, "weight", weightForUnit(nextUnit, item.box_weight_kg, item.case_weight_kg, item.weight));
                        }}
                        placeholder={t("quotes.unit")}
                        style={{ width: "var(--input-width-weight)" }}
                        data-testid={`invoice-item-row-${i}-unit`}
                      />
                    </td>
                    <td>
                      <TextFieldControl size="sm" type="number" min="1" step="1" value={item.quantity} onChange={(e) => updateItem(i, "quantity", Number(e.target.value))} style={{ width: "var(--input-width-qty)" }} data-testid={`invoice-item-row-${i}-qty`} />
                    </td>
                    <td>
                      <TextFieldControl size="sm" type="number" min="0" step="0.01" value={item.unit_price} onChange={(e) => updateItem(i, "unit_price", Number(e.target.value))} style={{ width: "var(--input-width-price)" }} data-testid={`invoice-item-row-${i}-price`} />
                    </td>
                    <td>
                      <TextFieldControl size="sm" type="number" min="0" step="0.001" value={item.weight || ""} onChange={(e) => updateItem(i, "weight", e.target.value ? Number(e.target.value) : null)} style={{ width: "var(--input-width-weight)" }} data-testid={`invoice-item-row-${i}-weight`} />
                    </td>
                    <td style={{ fontWeight: "var(--font-weight-semi)", whiteSpace: "nowrap" }}>{(item.quantity * item.unit_price).toLocaleString()}</td>
                    <td>
                      {items.length > 1 && (
                        <Button variant="danger" size="sm" type="button" onClick={() => removeItem(i)}>{t("quotes.removeItem")}</Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ marginBottom: "var(--space-3)" }}>
            <Button type="button" variant="secondary" size="md" onClick={addItem} data-testid="invoice-add-blank">{t("quotes.addItem")}</Button>
          </div>

          <div style={{ width: "min(100%, 40rem)", marginBottom: "var(--space-6)" }}>
            <InventorySearchBar
              onSelect={appendFromSearch}
              testIdPrefix="invoice-add-search"
              placeholder={t("inventory.view.searchPlaceholder")}
            />
          </div>

          <h3 style={{ marginBottom: "var(--space-3)" }}>{t("invoiceForm.sectionActions")}</h3>
          <div className="form-actions">
            <Button type="button" variant="secondary" size="md" onClick={() => navigate("/invoices")}>{t("common.cancel")}</Button>
            <Button type="button" variant="secondary" size="md" onClick={clearAll} data-testid="invoice-clear">{t("invoiceForm.clear")}</Button>
            <Button loading={saving} variant="primary" size="md" type="submit" disabled={!canCreate} data-testid="invoice-create-submit">{t("invoices.createBtn")}</Button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
```

### 2-7. frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx（新規。全文。K1・K2・K3・K4・K5・K8・K10・K12）

```tsx
// invoice-create-portfolio 便D: 請求書作成ページは選ぶだけで作れる（design.md §3-2・§8 K1〜K5・K8・K10・K12）
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from './InvoiceCreatePage';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string, opts?: Record<string, unknown>) => String(instance.t(key, opts));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function view() {
  render(<I18nextProvider i18n={instance}><MemoryRouter initialEntries={['/invoices/new']}><InvoiceCreatePage /><Location /></MemoryRouter></I18nextProvider>);
}

const CTX_PATH = '/invoices/draft-context?company_id=4&contact_id=5';
const summary = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', total_amount: 20, status: 'approved', created_at: '' };
const detail = { id: 7, quote_code: 'Q-7', company_id: 4, contact_id: 5, currency: 'USD', items: [{ product_id: 2, product_name: 'Card', quantity: 2, unit_price: 10, weight: 0.5 }] };
const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
const address = { company_name: 'Buyer Inc', billing_display_name: null, label: null, postal_code: '10001', address: '1 Main St', city: 'New York', state: 'NY', country: 'US', phone: null };
let ctx: Record<string, unknown>;
function baseCtx() {
  return {
    company_id: 4, ship_to: address, bill_to: { ...address, address: '2 Bill St' }, contact_name: 'One Buyer', contact_email: 'buyer@example.com',
    issuer_region: 'JP', origin_country_code: 'JP', destination_country_code: 'US', destination_postal_code: '10001',
    currencies: ['JPY', 'USD'], fx_rates: [{ currency: 'USD', rate: 150, fetched_at: '2026-11-15' }], default_currency: 'USD', currency: null,
    payment_methods: [
      { id: 3, method_type: 'bank', display_name: 'Main bank', wise_currency: null },
      { id: 4, method_type: 'wise', display_name: 'Wise USD', wise_currency: 'USD' },
    ],
    tax_rate_percent: null, incoterms: 'DAP',
  };
}
type PreviewBody = { currency: string; items: Array<{ quantity: number; unit_price: number }>; shipping: { mode: string; fee?: number } | null };
function previewFor(body: PreviewBody) {
  const subtotal = body.items.reduce((s, i) => s + i.quantity * i.unit_price, 0);
  if (body.shipping === null) {
    return { currency: body.currency, subtotal: String(subtotal), shipping_fee: null, tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: null, uncomputed: ['shipping_required'], incoterms: 'DAP' };
  }
  const fee = body.shipping.mode === 'calculate' ? body.shipping.fee ?? 0 : 0;
  return { currency: body.currency, subtotal: String(subtotal), shipping_fee: String(fee), tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: String(subtotal + fee), uncomputed: [], incoterms: 'DAP' };
}
const rate = { carrier: 'FedEx', zone: 'A', fee: 33.333, currency: 'USD', source: 'fedex_live', service_type: 'FEDEX_IP', service_name: 'International Priority', transit_days: 3, delivery_timestamp: null };

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  ctx = baseCtx();
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
    if (url === '/quotes?status=approved') return [summary];
    if (url === '/quotes/7') return detail;
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === CTX_PATH) return ctx;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(async (url: string, body: unknown) => {
    if (url === '/invoices/preview') return previewFor(body as PreviewBody);
    if (url === '/invoices') return { id: 11 };
    if (url === '/shipping/calculate') return { results: [rate], cheapest: rate, live_error: null, rate_precision: 'exact' };
    throw new Error(`Unexpected POST ${url}`);
  });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected patch'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function loadQuote() {
  view();
  fireEvent.click(await screen.findByTestId('invoice-edit-from-quote-7'));
  expect(await screen.findByDisplayValue('Card')).toBeTruthy();
  await screen.findByTestId('invoice-ship-to-address');
}
const optionValues = (testId: string) => Array.from((screen.getByTestId(testId) as HTMLSelectElement).options).map((o) => o.value);
const previewCalls = () => mock.post.mock.calls.filter(([url]) => url === '/invoices/preview').map(([, body]) => body as PreviewBody);
const postedInvoice = () => mock.post.mock.calls.filter(([url]) => url === '/invoices').map(([, body]) => body);

describe('InvoiceCreatePage (invoice-create-portfolio bin D)', () => {
  it('K1: ship-to, bill-to and contact are shown read-only', async () => {
    await loadQuote();
    const shipTo = screen.getByTestId('invoice-ship-to');
    expect(shipTo.querySelectorAll('input, textarea').length).toBe(0);
    expect(within(shipTo).getByTestId('invoice-ship-to-address').textContent).toContain('1 Main St');
    expect(within(shipTo).getByTestId('invoice-bill-to-address').textContent).toContain('2 Bill St');
    expect(within(shipTo).getByTestId('invoice-contact-line').textContent).toContain('buyer@example.com');
  });

  it('K2: currency and payment choices come from draft-context', async () => {
    await loadQuote();
    await waitFor(() => expect(optionValues('invoice-currency-select')).toEqual(['', 'JPY', 'USD']));
    expect((screen.getByTestId('invoice-currency-select') as HTMLSelectElement).value).toBe('USD');
    expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3', 'wise:4']);
    expect(screen.getByTestId('invoice-fx-line').textContent).toContain('150');
  });

  it('K3: switching USD to JPY removes the Wise USD row and clears the choice', async () => {
    await loadQuote();
    await waitFor(() => expect(optionValues('invoice-payment-select')).toContain('wise:4'));
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'wise:4' } });
    expect((screen.getByTestId('invoice-payment-select') as HTMLSelectElement).value).toBe('wise:4');
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'JPY' } });
    await waitFor(() => expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3']));
    expect((screen.getByTestId('invoice-payment-select') as HTMLSelectElement).value).toBe('');
  });

  it('K4/K8: before shipping is chosen the total is not computed and the reason is shown', async () => {
    await loadQuote();
    expect(screen.getByTestId('invoice-total-amount')).toBeTruthy();
    expect(await screen.findByTestId('invoice-uncomputed-shipping_required')).toBeTruthy();
    expect(screen.getByTestId('invoice-total-amount').textContent).toBe(tr('invoiceForm.notComputed'));
    expect(screen.getByTestId('invoice-total-shipping').textContent).toBe(tr('invoiceForm.notComputed'));
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryAllByRole('spinbutton').filter((el) => !(el.getAttribute('data-testid') ?? '').startsWith('invoice-item-row-'))).toEqual([]);
  });

  it('K5: a FedEx quote with locked fields sets carrier, fee and total', async () => {
    await loadQuote();
    await waitFor(() => expect((screen.getByTestId('invoice-shipping-quote') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-shipping-quote'));
    const dialog = await screen.findByRole('dialog');
    const field = (id: string) => dialog.querySelector(`#${id}`) as HTMLInputElement;
    expect(field('fedex-origin').value).toBe('JP');
    expect(field('fedex-dest-cc').value).toBe('US');
    expect(field('fedex-dest-postal').value).toBe('10001');
    expect(Number(field('fedex-weight').value)).toBe(1);
    for (const id of ['fedex-origin', 'fedex-dest-cc', 'fedex-dest-postal', 'fedex-weight']) expect(field(id).readOnly).toBe(true);
    fireEvent.click(within(dialog).getByRole('button', { name: tr('fedexRateModal.getQuote') }));
    fireEvent.click(await within(dialog).findByRole('button', { name: tr('fedexRateModal.selectRate') }));
    expect(mock.post).toHaveBeenCalledWith('/shipping/calculate', expect.objectContaining({ country_code: 'US', weight_kg: 1, origin_country_code: 'JP', destination_postal_code: '10001' }));
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'calculate' && b.shipping.fee === 33.33)).toBe(true));
    await waitFor(() => expect(screen.queryByTestId('invoice-uncomputed')).toBeNull());
    expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed'));
    expect((screen.getByTestId('invoice-shipping-select') as HTMLSelectElement).value).toBe('calculate');
  });

  it('K5: changing item weight after choosing a rate asks to choose again', async () => {
    await loadQuote();
    await waitFor(() => expect((screen.getByTestId('invoice-shipping-quote') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-shipping-quote'));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: tr('fedexRateModal.getQuote') }));
    fireEvent.click(await within(dialog).findByRole('button', { name: tr('fedexRateModal.selectRate') }));
    await waitFor(() => expect((screen.getByTestId('invoice-shipping-select') as HTMLSelectElement).value).toBe('calculate'));
    fireEvent.change(screen.getByTestId('invoice-item-row-0-qty'), { target: { value: '3' } });
    expect(await screen.findByTestId('invoice-shipping-stale')).toBeTruthy();
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
  });

  it('K10: section headings are in the designed order', async () => {
    await loadQuote();
    const headings = Array.from(document.querySelectorAll('form h3')).map((h) => h.textContent);
    expect(headings).toEqual([tr('invoiceForm.sectionShipTo'), tr('invoiceForm.sectionPaymentTotals'), tr('quotes.items'), tr('invoiceForm.sectionActions')]);
  });

  it('K12: "no shipping" + payment creates with the exact body and opens the detail page', async () => {
    await loadQuote();
    await waitFor(() => expect(optionValues('invoice-payment-select')).toContain('bank:3'));
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'bank:3' } });
    fireEvent.change(screen.getByTestId('invoice-shipping-select'), { target: { value: 'none' } });
    await waitFor(() => expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-create-submit'));
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/invoices/11'));
    expect(postedInvoice()).toEqual([{
      company_id: 4, contact_id: 5, currency: 'USD', shipping: { mode: 'none' }, payment_method_ref: { method_type: 'bank', id: 3 }, notes: null,
      items: [{ product_id: 2, product_name: 'Card', name_en: null, condition: null, unit: null, quantity: 2, unit_price: 10, weight: 0.5 }],
    }]);
    const sent = postedInvoice()[0] as Record<string, unknown>;
    expect('shipping_fee' in sent).toBe(false);
    expect('tax_amount' in sent).toBe(false);
  });

  it('no payment destinations: create is allowed without one and the profile link is offered', async () => {
    ctx = { ...baseCtx(), payment_methods: [] };
    await loadQuote();
    expect(await screen.findByTestId('invoice-open-tenant-profile')).toBeTruthy();
    fireEvent.change(screen.getByTestId('invoice-shipping-select'), { target: { value: 'none' } });
    await waitFor(() => expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-create-submit'));
    await waitFor(() => expect(postedInvoice().length).toBe(1));
    expect((postedInvoice()[0] as Record<string, unknown>).payment_method_ref).toBeNull();
  });

  it('issuer region missing: create stays disabled and the company page link is shown', async () => {
    ctx = { ...baseCtx(), issuer_region: null };
    await loadQuote();
    expect(await screen.findByTestId('invoice-open-company-for-bill-to')).toBeTruthy();
    fireEvent.change(screen.getByTestId('invoice-shipping-select'), { target: { value: 'none' } });
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'none')).toBe(true));
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByTestId('invoice-open-company-for-bill-to'));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });

  it('clear resets the form to the starting state', async () => {
    await loadQuote();
    fireEvent.click(screen.getByTestId('invoice-clear'));
    expect(screen.queryByDisplayValue('Card')).toBeNull();
    expect(screen.queryByTestId('invoice-ship-to')).toBeNull();
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
  });
});
```

### 2-8. frontend/src/pages/invoice-detail/InvoicePaymentPicker.tsx（新規。全文）

```tsx
/**
 * 下書きの請求書の支払方法を選び直す（invoice-create-portfolio 便D・design.md §3-2・§6）。
 *
 * 候補は請求書の材料（GET /invoices/draft-context?invoice_id=…）だけから出す。打ち込み欄は置かない。
 * 保存は PATCH /invoices/{id} の payment_method_ref だけ（口座番号などは送らない・持たない）。
 * 出す条件（下書き・作る権限と直す権限の両方）は呼び出し側が決める。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import { Button } from "../../components/Button";
import { Select } from "../../components/Select";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  draftContextPathForInvoice,
  effectivePaymentKey,
  paymentChoicesFor,
  paymentKey,
  paymentRefFromKey,
  type DraftContext,
} from "../../lib/invoiceDraftContext";

export interface InvoicePaymentPickerProps {
  invoiceId: string;
  currency: string;
  onSaved: () => void;
}

export function InvoicePaymentPicker({ invoiceId, currency, onSaved }: InvoicePaymentPickerProps) {
  const { t } = useTranslation();
  const ctxQ = useApiQuery<DraftContext>(draftContextPathForInvoice(invoiceId));
  const rawCtx: unknown = ctxQ.data;
  const ctx = rawCtx !== null && typeof rawCtx === "object" && !Array.isArray(rawCtx) ? (rawCtx as DraftContext) : null;
  const choices = paymentChoicesFor(ctx, currency);
  const [chosen, setChosen] = useState("");
  const value = effectivePaymentKey(choices, chosen);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const ctxError = ctxQ.error ? (ctxQ.error instanceof Error ? ctxQ.error.message : t("common.fetchError")) : "";

  const save = async () => {
    const ref = paymentRefFromKey(choices, value);
    if (ref === null) return;
    setSaving(true);
    setError("");
    try {
      await api.patch(`/invoices/${invoiceId}`, { payment_method_ref: ref });
      setChosen("");
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  if (ctxError !== "") {
    return <p className="error-message" data-testid="invoice-detail-payment-error">{ctxError}</p>;
  }
  if (ctx !== null && choices.length === 0) {
    return <p data-testid="invoice-detail-payment-none">{t("invoiceForm.noPaymentMethods")}</p>;
  }
  return (
    <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end", flexWrap: "wrap" }}>
      <Select
        label={t("invoiceForm.changePayment")}
        value={value}
        onChange={(e) => setChosen(e.target.value)}
        placeholder={t("invoiceForm.paymentPlaceholder")}
        options={choices.map((p) => ({
          value: paymentKey(p),
          label: p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]),
        }))}
        data-testid="invoice-detail-payment-select"
      />
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={save}
        loading={saving}
        disabled={value === "" || saving}
        data-testid="invoice-detail-payment-save"
      >
        {t("common.save")}
      </Button>
      {error !== "" && <p className="error-message" role="alert">{error}</p>}
    </div>
  );
}
```

### 2-9. frontend/src/pages/invoice-detail/InvoicePaymentPicker.test.tsx（新規。全文。K23）

```tsx
// invoice-create-portfolio 便D K23: 下書きの請求書で支払方法を選び直す
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { InvoicePaymentPicker } from './InvoicePaymentPicker';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();

const CTX = {
  company_id: 4, ship_to: null, bill_to: null, contact_name: null, contact_email: null,
  issuer_region: 'JP', origin_country_code: 'JP', destination_country_code: 'US', destination_postal_code: null,
  currencies: ['USD'], fx_rates: [], default_currency: 'USD', currency: 'JPY',
  payment_methods: [
    { id: 3, method_type: 'bank', display_name: 'Main bank', wise_currency: null },
    { id: 4, method_type: 'wise', display_name: 'Wise USD', wise_currency: 'USD' },
  ],
  tax_rate_percent: null, incoterms: 'DAP',
};

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/invoices/draft-context?invoice_id=9') return CTX;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function view(onSaved = vi.fn(), currency = 'JPY') {
  render(<I18nextProvider i18n={instance}><InvoicePaymentPicker invoiceId="9" currency={currency} onSaved={onSaved} /></I18nextProvider>);
  return onSaved;
}

describe('InvoicePaymentPicker (K23)', () => {
  it('offers only the rows that fit the invoice currency and saves the reference only', async () => {
    const onSaved = view();
    const select = (await screen.findByTestId('invoice-detail-payment-select')) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(select.options).map((o) => o.value)).toEqual(['', 'bank:3']));
    expect((screen.getByTestId('invoice-detail-payment-save') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(select, { target: { value: 'bank:3' } });
    fireEvent.click(screen.getByTestId('invoice-detail-payment-save'));
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(mock.patch).toHaveBeenCalledTimes(1);
    expect(mock.patch).toHaveBeenCalledWith('/invoices/9', { payment_method_ref: { method_type: 'bank', id: 3 } });
  });

  it('shows the Wise row when its currency matches', async () => {
    view(vi.fn(), 'USD');
    const select = (await screen.findByTestId('invoice-detail-payment-select')) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(select.options).map((o) => o.value)).toEqual(['', 'bank:3', 'wise:4']));
  });

  it('says there is nothing to choose when no row fits', async () => {
    mock.get.mockImplementation(async () => ({ ...CTX, payment_methods: [] }));
    view();
    expect(await screen.findByTestId('invoice-detail-payment-none')).toBeTruthy();
    expect(screen.queryByTestId('invoice-detail-payment-select')).toBeNull();
  });

  it('shows the save error and does not call onSaved', async () => {
    mock.patch.mockRejectedValue(new Error('Save failed'));
    const onSaved = view();
    const select = (await screen.findByTestId('invoice-detail-payment-select')) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(2));
    fireEvent.change(select, { target: { value: 'bank:3' } });
    fireEvent.click(screen.getByTestId('invoice-detail-payment-save'));
    expect(await screen.findByText('Save failed')).toBeTruthy();
    expect(onSaved).not.toHaveBeenCalled();
  });
});
```

### 2-10. frontend/src/features/secretary/SecretaryDraftInvoice.tsx（全部書き換え。全文）

```tsx
/**
 * 請求書の下書き（ADR-1056 段2）。送る欄は全部見せて、全部直せる。
 * 「作る」は今の請求書の作成画面と同じ口 POST /invoices を、本人のログインで呼ぶ。
 *
 * invoice-create-portfolio 便D（design.md §3-2）: 通貨と支払方法の候補は請求書の材料
 * （GET /invoices/draft-context）から出す（直書きしない）。チャットでは送料の見積を出さないので、
 * 「送料を請求しない」に人がチェックしたときだけ作れる。送料を付けるときは請求書の作成画面で作る。
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  currencyChoices,
  draftContextPath,
  effectivePaymentKey,
  paymentChoicesFor,
  paymentKey,
  paymentRefFromKey,
  resolveCurrency,
  type DraftContext,
} from "../../lib/invoiceDraftContext";
import { Button } from "../../components/Button";
import { Checkbox } from "../../components/Checkbox";
import { Select } from "../../components/Select";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import CompanyContactSelector, {
  type CompanyContactSelectorValue,
} from "../../components/CompanyContactSelector";
import type { Candidates, InvoiceDraftData } from "./secretaryApi";

interface Props {
  draft: InvoiceDraftData;
  candidates: Candidates;
  onCreated: (invoiceId: number) => void;
  onCancel: () => void;
}

interface ItemState {
  name: string;
  quantity: string;
  unitPrice: string;
}

/** 数は整数で 1 以上（口は int・ge=1） */
function isValidQuantity(value: string): boolean {
  return /^\d+$/.test(value.trim()) && Number(value) >= 1;
}

/** 保存側は小数 2 けたまで（backend/app/schemas/invoice.py:35）。"1e-7" のような書き方も 3 けた以上とみなす */
function hasTooManyDecimals(value: string): boolean {
  const trimmed = value.trim();
  return /\.\d{3,}$/.test(trimmed) || /e-/i.test(trimmed);
}

function isValidUnitPrice(value: string): boolean {
  const trimmed = value.trim();
  return trimmed !== "" && Number.isFinite(Number(trimmed)) && Number(trimmed) >= 0 && !hasTooManyDecimals(trimmed);
}

export function SecretaryDraftInvoice({ draft, candidates, onCreated, onCancel }: Props) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ItemState[]>(() =>
    draft.items.map((i) => ({
      name: i.product_name,
      quantity: String(i.quantity),
      unitPrice: i.unit_price === null ? "" : String(i.unit_price),
    })),
  );
  // 秘書が読んだ通貨。使う通貨は材料の候補にあるときだけ（resolveCurrency）。
  const [currencyChoice, setCurrencyChoice] = useState<string>(draft.currency ?? "");
  const [paymentChoice, setPaymentChoice] = useState("");
  const [shippingNone, setShippingNone] = useState(false);
  const [dueDate, setDueDate] = useState(draft.due_date ?? "");
  const [notes, setNotes] = useState(draft.notes ?? "");
  const [changing, setChanging] = useState(false);
  const [customer, setCustomer] = useState<CompanyContactSelectorValue>(() => ({
    companyId: candidates.companies.length === 1 ? candidates.companies[0].id : null,
    contactId: candidates.companies.length === 1 && candidates.contacts.length === 1 ? candidates.contacts[0].id : null,
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // 会社が 1 件に決まり、担当者の候補もあるときだけ候補の選び方。それ以外は今の選択の金型
  const candidateMode = !changing && candidates.companies.length === 1 && candidates.contacts.length >= 1;
  const selectorCompanies =
    !changing && candidates.companies.length >= 1
      ? candidates.companies.map((c) => ({ id: c.id, company_code: "", name: c.name }))
      : undefined;

  const itemsValid =
    items.length > 0 &&
    items.every((i) => i.name.trim() !== "" && isValidQuantity(i.quantity) && isValidUnitPrice(i.unitPrice));
  const priceMissing = items.some((i) => i.unitPrice.trim() === "");
  const priceTooPrecise = items.some((i) => hasTooManyDecimals(i.unitPrice));
  const customerReady = customer.companyId !== null && customer.contactId !== null;

  // 請求書の材料（会社と担当者が決まったときだけ取りに行く）
  const ctxQ = useApiQuery<DraftContext>(
    customerReady ? draftContextPath(customer.companyId as number, customer.contactId) : "/invoices/draft-context",
    { enabled: customerReady },
  );
  const rawCtx: unknown = ctxQ.data;
  const ctx = customerReady && rawCtx !== null && typeof rawCtx === "object" && !Array.isArray(rawCtx) ? (rawCtx as DraftContext) : null;
  const currencyOptions = currencyChoices(ctx);
  const currency = resolveCurrency(ctx, currencyChoice);
  const paymentChoices = paymentChoicesFor(ctx, currency);
  const paymentValue = effectivePaymentKey(paymentChoices, paymentChoice);
  const paymentReady = paymentChoices.length === 0 || paymentValue !== "";
  const canCreate =
    itemsValid && customerReady && ctx !== null && ctx.issuer_region !== null && currency !== "" && paymentReady && shippingNone && !saving;

  const updateItem = (index: number, patch: Partial<ItemState>) =>
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)));

  const submit = async () => {
    if (!canCreate) return;
    setSaving(true);
    setError("");
    try {
      const inv = await api.post<{ id: number }>("/invoices", {
        company_id: customer.companyId,
        contact_id: customer.contactId,
        currency,
        shipping: { mode: "none" },
        payment_method_ref: paymentRefFromKey(paymentChoices, paymentValue),
        due_date: dueDate || null,
        notes: notes || null,
        items: items.map((i) => ({
          product_name: i.name.trim(),
          quantity: Number(i.quantity),
          unit_price: Number(i.unitPrice),
        })),
      });
      onCreated(inv.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
      setSaving(false);
    }
  };

  return (
    <div className="secretary-draft">
      <p className="secretary-draft__title">{t("secretary.invoice.title")}</p>

      {candidateMode ? (
        <div className="secretary-draft__section">
          <p className="secretary-draft__text">
            {t("secretary.invoice.company")}: {candidates.companies[0].name}
          </p>
          <Select
            fullWidth
            label={t("secretary.invoice.contact")}
            value={customer.contactId === null ? "" : String(customer.contactId)}
            onChange={(e) => {
              setPaymentChoice("");
              setCustomer({ companyId: customer.companyId, contactId: e.target.value ? Number(e.target.value) : null });
            }}
            placeholder={t("companyContactSelector.selectContact")}
            options={candidates.contacts.map((c) => ({ value: String(c.id), label: c.name }))}
          />
          <Button variant="ghost" size="sm" onClick={() => setChanging(true)}>
            {t("secretary.invoice.changeCustomer")}
          </Button>
        </div>
      ) : (
        <div className="secretary-draft__section">
          <CompanyContactSelector
            value={customer}
            onChange={(next) => { setPaymentChoice(""); setCustomer(next); }}
            companies={selectorCompanies}
          />
        </div>
      )}

      <div className="secretary-draft__section">
        {items.map((item, index) => (
          <div className="secretary-draft__item" key={index}>
            <TextField
              fullWidth
              label={t("secretary.invoice.itemName")}
              value={item.name}
              onChange={(e) => updateItem(index, { name: e.target.value })}
            />
            <TextField
              fullWidth
              label={t("secretary.invoice.quantity")}
              type="number"
              min={1}
              step={1}
              value={item.quantity}
              onChange={(e) => updateItem(index, { quantity: e.target.value })}
            />
            <TextField
              fullWidth
              label={t("secretary.invoice.unitPrice")}
              type="number"
              min={0}
              step={0.01}
              value={item.unitPrice}
              onChange={(e) => updateItem(index, { unitPrice: e.target.value })}
            />
          </div>
        ))}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setItems((prev) => [...prev, { name: "", quantity: "1", unitPrice: "" }])}
        >
          {t("secretary.invoice.addItem")}
        </Button>
        {priceMissing && <p className="secretary-draft__hint">{t("secretary.priceRequired")}</p>}
        {priceTooPrecise && <p className="secretary-draft__hint">{t("secretary.priceDecimals")}</p>}
      </div>

      <div className="secretary-draft__section">
        {ctx !== null && ctx.issuer_region === null && (
          <p className="secretary-draft__hint" data-testid="secretary-invoice-bill-to">{t("apiError.billToCountry")}</p>
        )}
        <Select
          fullWidth
          required
          label={t("secretary.invoice.currency")}
          value={currency}
          onChange={(e) => { setCurrencyChoice(e.target.value); setPaymentChoice(""); }}
          placeholder={t("invoiceForm.currencyPlaceholder")}
          options={currencyOptions.map((c) => ({ value: c, label: c }))}
          data-testid="secretary-invoice-currency"
        />
        {paymentChoices.length > 0 ? (
          <Select
            fullWidth
            required
            label={t("invoiceForm.payment")}
            value={paymentValue}
            onChange={(e) => setPaymentChoice(e.target.value)}
            placeholder={t("invoiceForm.paymentPlaceholder")}
            options={paymentChoices.map((p) => ({
              value: paymentKey(p),
              label: p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]),
            }))}
            data-testid="secretary-invoice-payment"
          />
        ) : (
          ctx !== null && ctx.issuer_region !== null && (
            <p className="secretary-draft__hint" data-testid="secretary-invoice-no-payment">{t("invoiceForm.noPaymentMethods")}</p>
          )
        )}
        <Checkbox
          label={t("invoiceForm.shippingNone")}
          description={t("secretary.invoice.shippingNoneHelp")}
          checked={shippingNone}
          onChange={(e) => setShippingNone(e.target.checked)}
          data-testid="secretary-invoice-shipping-none"
        />
        <TextField
          fullWidth
          label={t("secretary.invoice.dueDate")}
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
        />
        <Textarea
          fullWidth
          label={t("secretary.invoice.notes")}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      {error && (
        <p className="secretary-draft__error" role="alert">
          {error}
        </p>
      )}
      <div className="secretary-draft__actions">
        <Button variant="secondary" size="sm" onClick={onCancel} disabled={saving}>
          {t("secretary.cancel")}
        </Button>
        <Button size="sm" onClick={submit} disabled={!canCreate} loading={saving}>
          {t("secretary.create")}
        </Button>
      </div>
    </div>
  );
}
```

### 2-11. frontend/src/features/secretary/SecretaryChat.test.tsx（全部書き換え。全文。K19）

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { SecretaryChat } from "./SecretaryChat";

const mock = vi.hoisted(() => ({
  postWithTimeout: vi.fn(),
  post: vi.fn(),
  get: vi.fn(),
  features: new Set<string>(),
  superAdmin: false,
  permissions: new Set<string>(),
}));

vi.mock("../../lib/api", () => ({
  api: { postWithTimeout: mock.postWithTimeout, post: mock.post, get: mock.get },
  ApiError: class ApiError extends Error {
    status: number;
    responseDetail: unknown;
    constructor(message: string, status: number, responseDetail: unknown) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.responseDetail = responseDetail;
    }
  },
}));
vi.mock("../../hooks/useFeatures", () => ({
  useFeatures: () => ({ loading: false, isEnabled: (k: string) => mock.features.has(k) }),
}));
vi.mock("../../hooks/useSuperAdmin", () => ({
  useSuperAdmin: () => ({ loading: false, isSuperAdmin: mock.superAdmin }),
}));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ loading: false, hasPermission: (k: string) => mock.permissions.has(k) }),
}));

import { ApiError } from "../../lib/api";
import { queryClient } from "../../lib/query/apiQuery";
import { apiErrorReasonMessage } from "../../lib/apiErrorReason";

const FAB = "Ask the assistant";

const allowAll = () => {
  mock.features = new Set(["secretary_chat"]);
  mock.superAdmin = true;
  mock.permissions = new Set(["customers.view", "invoices.create"]);
};

const none = { companies: [], contacts: [] };
// invoice-create-portfolio 便D: 会社 1・担当者 2 の請求書の材料（通貨と支払方法の候補の正本）
const DRAFT_CTX_PATH = "/invoices/draft-context?company_id=1&contact_id=2";
const DRAFT_CTX = {
  company_id: 1, ship_to: null, bill_to: null, contact_name: "Taro", contact_email: null,
  issuer_region: "JP", origin_country_code: "JP", destination_country_code: "US", destination_postal_code: null,
  currencies: ["JPY", "USD"], fx_rates: [], default_currency: "JPY", currency: null,
  payment_methods: [{ id: 3, method_type: "bank", display_name: "Main bank", wise_currency: null }],
  tax_rate_percent: null, incoterms: "DAP",
};
let draftCtx: Record<string, unknown> = DRAFT_CTX;
const invoiceReply = (overrides: Record<string, unknown> = {}) => ({
  kind: "invoice",
  draft: {
    company_name: "Acme",
    contact_name: "Taro",
    items: [{ product_name: "Widget", quantity: 2, unit_price: null }],
    due_date: null,
    notes: null,
    currency: "JPY",
    ...overrides,
  },
  candidates: { companies: [{ id: 1, name: "Acme" }], contacts: [{ id: 2, name: "Taro" }] },
});
const eventReply = {
  kind: "event",
  draft: {
    title: "Meeting",
    start: "2026-11-02T10:00:00+09:00",
    end: "2026-11-02T11:00:00+09:00",
    is_all_day: false,
    location: null,
    description: null,
    calendar_type: "personal",
    is_meeting: false,
    add_meet: null,
    meet_available: false,
    ask: null,
    ask_count: 0,
  },
  candidates: none,
};

const renderChat = () =>
  render(
    <MemoryRouter>
      <SecretaryChat isMobile={false} />
    </MemoryRouter>,
  );

async function sendMessage(text = "hello") {
  fireEvent.click(screen.getByRole("button", { name: FAB }));
  const box = await screen.findByLabelText(/Tell me what you need/);
  fireEvent.change(box, { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

beforeEach(async () => {
  vi.clearAllMocks();
  allowAll();
  draftCtx = DRAFT_CTX;
  mock.get.mockImplementation(async (url: string) => (url === DRAFT_CTX_PATH ? draftCtx : []));
  await i18n.changeLanguage("en");
});
afterEach(() => {
  cleanup();
  queryClient.clear();
});

/** 便D: 支払方法を選び「送料を請求しない」にチェックする（チャットで作れる条件） */
async function decideInvoice() {
  const payment = (await screen.findByTestId("secretary-invoice-payment")) as HTMLSelectElement;
  await waitFor(() => expect(Array.from(payment.options).map((o) => o.value)).toEqual(["", "bank:3"]));
  fireEvent.change(payment, { target: { value: "bank:3" } });
  fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
}

describe("SecretaryChat visibility", () => {
  it("shows the button only when the feature and super admin are both on", () => {
    mock.features = new Set();
    const { unmount } = renderChat();
    expect(screen.queryByRole("button", { name: FAB })).toBeNull();
    unmount();

    allowAll();
    mock.superAdmin = false;
    const second = renderChat();
    expect(screen.queryByRole("button", { name: FAB })).toBeNull();
    second.unmount();

    allowAll();
    renderChat();
    expect(screen.getByRole("button", { name: FAB })).toBeTruthy();
  });

  it.each(["customers.view", "invoices.create"])("hides the button without %s", (missing) => {
    mock.permissions.delete(missing);
    renderChat();
    expect(screen.queryByRole("button", { name: FAB })).toBeNull();
  });

  it("hides the button on a 403", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("forbidden", 403, "forbidden"));
    renderChat();
    await sendMessage();
    await waitFor(() => expect(screen.queryByRole("button", { name: FAB })).toBeNull());
  });
});

describe("SecretaryChat sending", () => {
  it("calls postWithTimeout with the 100 second limit", async () => {
    mock.postWithTimeout.mockResolvedValue({ kind: "unknown", draft: { reply: "ok" }, candidates: none });
    renderChat();
    await sendMessage("make something");
    await screen.findByText("ok");
    expect(mock.postWithTimeout).toHaveBeenCalledWith("/assistant/messages", { text: "make something", karte: null }, 100000);
  });

  it("shows the reply as plain text, not HTML", async () => {
    mock.postWithTimeout.mockResolvedValue({ kind: "unknown", draft: { reply: "<b>x</b>" }, candidates: none });
    const { container } = renderChat();
    await sendMessage();
    await screen.findByText("<b>x</b>");
    expect(document.body.querySelector(".comp-chat-bubble b")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
  });

  it("shows the timeout text on AbortError", async () => {
    const abort = new Error("aborted");
    abort.name = "AbortError";
    mock.postWithTimeout.mockRejectedValue(abort);
    renderChat();
    await sendMessage();
    expect(await screen.findByText(/took too long/)).toBeTruthy();
  });

  it("shows the notReady text on 503 not_ready", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 503, { code: "not_ready" }));
    renderChat();
    await sendMessage();
    expect(await screen.findByText("The assistant is not ready yet")).toBeTruthy();
  });

  it("shows the authFailed text on 503 auth_failed, not the rephrase text", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 503, { code: "auth_failed" }));
    renderChat();
    await sendMessage();
    expect(await screen.findByText("The assistant's key no longer works. Please tell your administrator.")).toBeTruthy();
    expect(screen.queryByText(/rephrase/)).toBeNull();
  });

  it("shows the agentFailed text in full on 502 agent_failed, not the generic text", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 502, { code: "agent_failed" }));
    renderChat();
    await sendMessage();
    expect(
      await screen.findByText("Something went wrong. Please wait a moment and send it again."),
    ).toBeTruthy();
    expect(screen.queryByText(/Please try again/)).toBeNull();
  });

  it("shows the rulesTooLong text on 413 rules_too_long", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 413, { code: "rules_too_long" }));
    renderChat();
    await sendMessage();
    expect(
      await screen.findByText("Your message and the company rules are too long together. Shorten the message or remove some rules."),
    ).toBeTruthy();
  });

  it("shows the unreadable text on 502 unreadable", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 502, { code: "unreadable" }));
    renderChat();
    await sendMessage();
    expect(await screen.findByText("I could not understand that. Please rephrase")).toBeTruthy();
  });

  it("shows the generic text for other failures, and error status only on the assistant bubble", async () => {
    mock.postWithTimeout.mockRejectedValue(new Error("network"));
    renderChat();
    await sendMessage("hi");
    expect(await screen.findByText(/Something went wrong/)).toBeTruthy();
    expect(document.body.querySelectorAll(".comp-chat-bubble--outbound.comp-chat-bubble--error").length).toBe(0);
    expect(document.body.querySelectorAll(".comp-chat-bubble--inbound.comp-chat-bubble--error").length).toBe(1);
  });
});

describe("SecretaryChat invoice draft", () => {
  it("blocks Create while a unit price is empty, then sends only the decided fields", async () => {
    mock.postWithTimeout.mockResolvedValue(invoiceReply());
    mock.post.mockResolvedValue({ id: 77 });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect(create.disabled).toBe(true);
    expect(mock.post).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "1500" } });
    expect(create.disabled).toBe(true);
    await decideInvoice();
    expect(create.disabled).toBe(false);
    fireEvent.click(create);

    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post).toHaveBeenCalledWith("/invoices", {
      company_id: 1,
      contact_id: 2,
      currency: "JPY",
      due_date: null,
      notes: null,
      items: [{ product_name: "Widget", quantity: 2, unit_price: 1500 }],
      shipping: { mode: "none" },
      payment_method_ref: { method_type: "bank", id: 3 },
    });
    expect(await screen.findByText(/Invoice created/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open invoice" }).getAttribute("href")).toBe("/invoices/77");
  });

  it("blocks Create and shows the decimals text when the unit price has 3 decimal places", async () => {
    mock.postWithTimeout.mockResolvedValue(invoiceReply());
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "1000.255" } });
    expect(screen.getByText("Unit price can have up to 2 decimal places.")).toBeTruthy();
    expect(create.disabled).toBe(true);
  });

  it.each([1000.5, 1000.25])("sends the unit price %s as is", async (price) => {
    mock.postWithTimeout.mockResolvedValue(invoiceReply());
    mock.post.mockResolvedValue({ id: 78 });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: String(price) } });
    expect(screen.queryByText("Unit price can have up to 2 decimal places.")).toBeNull();
    await decideInvoice();
    expect(create.disabled).toBe(false);
    fireEvent.click(create);
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post).toHaveBeenCalledWith(
      "/invoices",
      expect.objectContaining({ items: [{ product_name: "Widget", quantity: 2, unit_price: price }] }),
    );
  });

  it("keeps a drafted unit price of 1000.255 as is, shows the decimals text and blocks Create", async () => {
    mock.postWithTimeout.mockResolvedValue(
      invoiceReply({ items: [{ product_name: "Widget", quantity: 2, unit_price: 1000.255 }] }),
    );
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect((screen.getByLabelText("Unit price") as HTMLInputElement).value).toBe("1000.255");
    expect(screen.getByText("Unit price can have up to 2 decimal places.")).toBeTruthy();
    expect(create.disabled).toBe(true);
  });

  it("blocks Create until company and contact are decided", async () => {
    mock.postWithTimeout.mockResolvedValue({
      ...invoiceReply({ items: [{ product_name: "Widget", quantity: 1, unit_price: 100 }] }),
      candidates: none,
    });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect(create.disabled).toBe(true);
  });

  it.each(["0", "1.5"])("blocks Create when the quantity is %s", async (qty) => {
    mock.postWithTimeout.mockResolvedValue(
      invoiceReply({ items: [{ product_name: "Widget", quantity: 1, unit_price: 100 }] }),
    );
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    await decideInvoice();
    expect(create.disabled).toBe(false);
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: qty } });
    expect(create.disabled).toBe(true);
  });
});

describe("SecretaryChat invoice draft (invoice-create-portfolio bin D)", () => {
  const ready = () => invoiceReply({ items: [{ product_name: "Widget", quantity: 1, unit_price: 100 }] });

  it("K2: currency and payment choices come from draft-context, not a fixed list", async () => {
    mock.postWithTimeout.mockResolvedValue(ready());
    renderChat();
    await sendMessage();
    const currency = (await screen.findByTestId("secretary-invoice-currency")) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(currency.options).map((o) => o.value)).toEqual(["", "JPY", "USD"]));
    expect(currency.value).toBe("JPY");
    expect(mock.get).toHaveBeenCalledWith(DRAFT_CTX_PATH);
  });

  it("K19: Create stays disabled until \"Do not charge shipping\" is ticked, and the body has no tax or shipping fee", async () => {
    mock.postWithTimeout.mockResolvedValue(ready());
    mock.post.mockResolvedValue({ id: 80 });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    const payment = (await screen.findByTestId("secretary-invoice-payment")) as HTMLSelectElement;
    await waitFor(() => expect(payment.options.length).toBe(2));
    fireEvent.change(payment, { target: { value: "bank:3" } });
    expect(create.disabled).toBe(true);
    fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
    expect(create.disabled).toBe(false);
    fireEvent.click(create);
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    const body = mock.post.mock.calls[0][1] as Record<string, unknown>;
    expect(body.shipping).toEqual({ mode: "none" });
    expect("tax_amount" in body).toBe(false);
    expect("shipping_fee" in body).toBe(false);
  });

  it("K19: a 409 duty_needs_carrier shows the Japanese wording, not the code, and creates nothing", async () => {
    await i18n.changeLanguage("ja");
    const wording = apiErrorReasonMessage("duty_needs_carrier");
    expect(wording).toBeTruthy();
    expect(wording).not.toBe("duty_needs_carrier");
    mock.postWithTimeout.mockResolvedValue(ready());
    mock.post.mockRejectedValue(new ApiError(wording as string, 409, "duty_needs_carrier"));
    renderChat();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("secretary.open") }));
    const box = await screen.findByLabelText(i18n.t("secretary.placeholder"));
    fireEvent.change(box, { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("secretary.send") }));
    await decideInvoice();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("secretary.create") }));
    expect(await screen.findByText(wording as string)).toBeTruthy();
    expect(screen.queryByText("duty_needs_carrier")).toBeNull();
    expect(screen.queryByRole("link", { name: i18n.t("secretary.link.invoice") })).toBeNull();
  });

  it("no payment destinations: Create is allowed without one and the hint is shown", async () => {
    draftCtx = { ...DRAFT_CTX, payment_methods: [] };
    mock.postWithTimeout.mockResolvedValue(ready());
    mock.post.mockResolvedValue({ id: 81 });
    renderChat();
    await sendMessage();
    expect(await screen.findByTestId("secretary-invoice-no-payment")).toBeTruthy();
    fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
    const create = screen.getByRole("button", { name: "Create" }) as HTMLButtonElement;
    expect(create.disabled).toBe(false);
    fireEvent.click(create);
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect((mock.post.mock.calls[0][1] as Record<string, unknown>).payment_method_ref).toBeNull();
  });

  it("issuer region missing: the bill-to hint is shown and Create stays disabled", async () => {
    draftCtx = { ...DRAFT_CTX, issuer_region: null };
    mock.postWithTimeout.mockResolvedValue(ready());
    renderChat();
    await sendMessage();
    expect(await screen.findByTestId("secretary-invoice-bill-to")).toBeTruthy();
    fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
    expect((screen.getByRole("button", { name: "Create" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("SecretaryChat event draft", () => {
  it("starts as personal and only mentions the whole company when shared", async () => {
    mock.postWithTimeout.mockResolvedValue(eventReply);
    renderChat();
    await sendMessage();
    const select = (await screen.findByLabelText("Visibility")) as HTMLSelectElement;
    expect(select.value).toBe("personal");
    expect(screen.queryByText("Visible to everyone in your company")).toBeNull();

    fireEvent.change(select, { target: { value: "shared" } });
    const note = screen.getByText("Visible to everyone in your company");
    expect(note.textContent).not.toMatch(/Google/i);
  });

  it("posts the event to /calendar/events without category", async () => {
    mock.postWithTimeout.mockResolvedValue(eventReply);
    mock.post.mockResolvedValue({});
    renderChat();
    await sendMessage();
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    const [path, body] = mock.post.mock.calls[0];
    expect(path).toBe("/calendar/events");
    expect(body).toMatchObject({ title: "Meeting", is_all_day: false, calendar_type: "personal" });
    expect(body).not.toHaveProperty("category");
  });

  it("asks one missing field, then sends the karte back on the next message", async () => {
    const askReply = {
      ...eventReply,
      draft: { ...eventReply.draft, end: null, is_meeting: true, ask: "end", ask_count: 1 },
    };
    mock.postWithTimeout.mockResolvedValueOnce(askReply).mockResolvedValueOnce(eventReply);
    renderChat();
    await sendMessage("meeting tomorrow at 10");
    expect(await screen.findByText(i18n.t("secretary.ask.end"))).toBeTruthy();
    expect(screen.getByText("Meeting")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Create" })).toBeNull();

    const box = screen.getByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "until 11" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByRole("button", { name: "Create" });
    const [, body] = mock.postWithTimeout.mock.calls[1];
    expect(body.karte).toMatchObject({ title: "Meeting", end: null, is_meeting: true, asked: "end", asked_count: 1 });
  });

  it("cannot create while a time is empty", async () => {
    mock.postWithTimeout.mockResolvedValue({ ...eventReply, draft: { ...eventReply.draft, end: null } });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect(create.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-11-02" } });
    expect(create.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("End time"), { target: { value: "11:00" } });
    expect(create.disabled).toBe(false);
  });

  it("shows the Meet checkbox only when Meet is available and sends add_meet when checked", async () => {
    mock.postWithTimeout.mockResolvedValue({ ...eventReply, draft: { ...eventReply.draft, meet_available: true, add_meet: true } });
    mock.post.mockResolvedValue({});
    renderChat();
    await sendMessage();
    const meet = (await screen.findByLabelText(i18n.t("schedule.addMeet"))) as HTMLInputElement;
    expect(meet.checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post.mock.calls[0][1]).toMatchObject({ add_meet: true });
  });

  it("hides the Meet checkbox and never sends add_meet when Meet is not available", async () => {
    mock.postWithTimeout.mockResolvedValue(eventReply);
    mock.post.mockResolvedValue({});
    renderChat();
    await sendMessage();
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(screen.queryByLabelText(i18n.t("schedule.addMeet"))).toBeNull();
    expect(mock.post.mock.calls[0][1]).not.toHaveProperty("add_meet");
  });
});
```

### 2-12. frontend/src/components/FedExRateModal.tsx（全部書き換え。全文）

```tsx
/**
 * FedEx ライブ見積もり比較モーダル（ADR-125 D6）
 *
 * FedEx Rates and Transit Times API から取得したリアルタイム送料を表示し、
 * テナントが希望のサービスタイプを選択できる。
 *
 * ADR-125 D5（暗黙フォールバック禁止）:
 * - ライブ取得に成功した場合のみ「ライブ」バッジを表示
 * - live_error が返ってきた場合は明示的なエラーメッセージを表示
 * - FedEx 未連携の場合は連携設定ページへの導線を提供
 *
 * ADR-027: 全文字列は t("key") 経由
 *
 * 変更履歴:
 *   2026-06-09: 初版（ADR-125 Phase C）
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { TextField } from "./TextField";
import { api } from "../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

interface FedExRateResult {
  carrier: string;
  zone: string;
  fee: number;
  currency: string;
  source: "static" | "fedex_live";
  service_type: string | null;
  service_name: string | null;
  transit_days: number | null;
  delivery_timestamp: string | null;
}

interface ShippingCalcResponse {
  results: FedExRateResult[];
  cheapest: FedExRateResult | null;
  live_error: string | null;
  rate_precision: "exact" | "approximate" | null;
}

interface Props {
  /** モーダルの開閉 */
  open: boolean;
  onClose: () => void;
  /** 宛先国コード（省略時はモーダル内で入力）*/
  destinationCountryCode?: string;
  /**
   * 発送元国コード。渡したときは請求書の材料から決まった値として、発送元・宛先・郵便番号・重量を
   * 読むだけにする（invoice-create-portfolio 便D。省略時は今まで通りモーダル内で入力）
   */
  originCountryCode?: string;
  /** 宛先郵便番号（省略時はモーダル内で入力）*/
  destinationPostalCode?: string;
  /** 重量（kg）*/
  weightKg: number;
  /** 選択した料金を受け取るコールバック（4 つ目は送料の会社） */
  onSelectRate: (fee: number, currency: string, serviceType: string | null, carrier?: string) => void;
}

// ---------------------------------------------------------------------------
// SourceBadge: ライブ / 静的 バッジ
// ---------------------------------------------------------------------------

function SourceBadge({ source }: { source: "static" | "fedex_live" }) {
  const { t } = useTranslation();
  if (source === "fedex_live") {
    return (
      <span
        style={{
          display: "inline-block",
          padding: "2px 6px",
          borderRadius: "4px",
          fontSize: "11px",
          fontWeight: 600,
          backgroundColor: "var(--info-bg)",
          color: "var(--info-text)",
        }}
      >
        {t("fedexRateModal.sourceLive")}
      </span>
    );
  }
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 6px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: 600,
        backgroundColor: "var(--bg-subtle)",
        color: "var(--text-secondary)",
      }}
    >
      {t("fedexRateModal.sourceStatic")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// FedExRateModal 本体
// ---------------------------------------------------------------------------

export function FedExRateModal({
  open,
  onClose,
  destinationCountryCode: destinationCountryCodeProp,
  originCountryCode: originCountryCodeProp,
  destinationPostalCode: destinationPostalCodeProp,
  weightKg,
  onSelectRate,
}: Props) {
  const { t } = useTranslation();
  // 発送元を渡されたときは、材料から決まった値を読むだけにする（打ち直させない）
  const locked = originCountryCodeProp !== undefined;
  const [originCountryCode, setOriginCountryCode] = useState(originCountryCodeProp ?? "JP");
  const [destCC, setDestCC] = useState(destinationCountryCodeProp ?? "");
  const [internalWeightKg, setInternalWeightKg] = useState(weightKg);
  const [destinationPostalCode, setDestinationPostalCode] = useState(destinationPostalCodeProp ?? "");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ShippingCalcResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const handleGetQuote = async () => {
    setLoading(true);
    setFetchError(null);
    setResponse(null);

    try {
      const data = await api.post<ShippingCalcResponse>("/shipping/calculate", {
        country_code: destCC,
        weight_kg: internalWeightKg,
        carrier: "fedex",
        origin_country_code: originCountryCode || "JP",
        ...(destinationPostalCode ? { destination_postal_code: destinationPostalCode } : {}),
      });
      setResponse(data);
    } catch (e) {
      setFetchError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setResponse(null);
    setFetchError(null);
    onClose();
  };

  // エラーメッセージの整形（ADR-125 D5）
  // 未連携 / アカウント番号未設定 / API エラーの3種を区別して表示
  // eslint-disable-next-line local/no-japanese-literal -- backend API error string
  const isNotConnected = response?.live_error?.includes("未連携") ?? false;
  const liveErrorMessage = response?.live_error
    ? isNotConnected
      ? t("fedexRateModal.errorNotConnected")
      // eslint-disable-next-line local/no-japanese-literal -- backend API error string
      : response.live_error.includes("アカウント番号")
        ? t("fedexRateModal.errorAccountNumber")
        : `${t("fedexRateModal.errorApiFailure")}: ${response.live_error}`
    : null;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={t("fedexRateModal.title")}
      size="lg"
    >
      {/* 発送元 / 宛先 国コード入力 */}
      <div style={{ marginBottom: "var(--space-3)" }}>
        <div style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap" }}>
          <TextField
            label={t("fedexRateModal.originLabel")}
            id="fedex-origin"
            type="text"
            value={originCountryCode}
            maxLength={3}
            placeholder={t("fedexRateModal.originPlaceholder")}
            onChange={(e) => setOriginCountryCode(e.target.value.toUpperCase())}
            readOnly={locked}
            style={{ width: "var(--input-width-country-code)" }}
          />
          <TextField
            label={t("fedexRateModal.destinationLabel")}
            id="fedex-dest-cc"
            type="text"
            value={destCC}
            maxLength={3}
            placeholder={t("fedexRateModal.destinationPlaceholder")}
            onChange={(e) => setDestCC(e.target.value.toUpperCase())}
            readOnly={locked}
            style={{ width: "var(--input-width-country-code)" }}
          />
          <TextField
            label={t("fedexRateModal.weightLabel")}
            id="fedex-weight"
            type="number"
            min="0"
            step="0.001"
            value={internalWeightKg}
            onChange={(e) => setInternalWeightKg(Number(e.target.value))}
            readOnly={locked}
            style={{ width: "var(--input-width-shipping-weight)" }}
          />
        </div>
        <Button
          variant="primary"
          loading={loading}
          onClick={handleGetQuote}
          disabled={loading || !originCountryCode || !destCC}
        >
          {t("fedexRateModal.getQuote")}
        </Button>
      </div>

      {/* 宛先郵便番号（任意）— rate_precision 制御用 */}
      <TextField
        label={t("fedexRateModal.postalCodeLabel")}
        id="fedex-dest-postal"
        type="text"
        value={destinationPostalCode}
        maxLength={20}
        placeholder={t("fedexRateModal.postalCodePlaceholder")}
        onChange={(e) => setDestinationPostalCode(e.target.value)}
        readOnly={locked}
        style={{ width: "var(--field-w-sm)" }}
      />

      {/* API エラー（fetch 自体の失敗） */}
      {fetchError && (
        <div
          role="alert"
          style={{
            padding: "12px",
            borderRadius: "6px",
            backgroundColor: "var(--danger-bg)",
            color: "var(--danger-text)",
            marginBottom: "12px",
          }}
        >
          {fetchError}
        </div>
      )}

      {/* 未連携状態（ADR-125 D5 + PO C1判断: FedEx 未連携時は設定ページへ誘導） */}
      {isNotConnected && (
        <div
          role="alert"
          style={{
            padding: "16px",
            borderRadius: "6px",
            backgroundColor: "var(--warning-bg)",
            color: "var(--warning-text)",
            marginBottom: "12px",
          }}
        >
          <p style={{ marginBottom: "8px" }}>{t("fedexRateModal.errorNotConnected")}</p>
          <a
            href="/integrations/fedex"
            style={{ color: "var(--link)", textDecoration: "underline", fontSize: "14px" }}
          >
            {t("fedexRateModal.goToIntegrationSettings")}
          </a>
        </div>
      )}

      {/* live_error（未連携以外: アカウント番号未設定 / API エラー） */}
      {liveErrorMessage && !isNotConnected && (
        <div
          role="alert"
          style={{
            padding: "12px",
            borderRadius: "6px",
            backgroundColor: "var(--warning-bg)",
            color: "var(--warning-text)",
            marginBottom: "12px",
          }}
        >
          {liveErrorMessage}
        </div>
      )}

      {/* 見積もり結果テーブル */}
      {response && !liveErrorMessage && (
        <>
          {/* 概算バッジ（郵便番号未指定時）— ADR-125 仕様追補 2026-06-10 */}
          {response.rate_precision === "approximate" && (
            <div
              role="note"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 10px",
                borderRadius: "6px",
                backgroundColor: "var(--warning-bg)",
                color: "var(--warning-text)",
                fontSize: "12px",
                marginBottom: "10px",
              }}
            >
              <span style={{ fontWeight: 600 }}>{t("fedexRateModal.badgeApproximate")}</span>
            </div>
          )}
          {response.results.length === 0 ? (
            <p style={{ color: "var(--text-secondary)" }}>{t("fedexRateModal.noResults")}</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--border)" }}>
                  <th style={{ textAlign: "left", padding: "8px 4px" }}>{t("fedexRateModal.colSource")}</th>
                  <th style={{ textAlign: "left", padding: "8px 4px" }}>{t("fedexRateModal.colCarrier")}</th>
                  <th style={{ textAlign: "left", padding: "8px 4px" }}>{t("fedexRateModal.colService")}</th>
                  <th style={{ textAlign: "right", padding: "8px 4px" }}>{t("fedexRateModal.colTransitDays")}</th>
                  <th style={{ textAlign: "right", padding: "8px 4px" }}>{t("fedexRateModal.colFee")}</th>
                  <th style={{ textAlign: "center", padding: "8px 4px" }}>{t("fedexRateModal.colCurrency")}</th>
                  <th style={{ textAlign: "center", padding: "8px 4px" }} />
                </tr>
              </thead>
              <tbody>
                {response.results.map((r, i) => (
                  <tr
                    key={i}
                    style={{ borderBottom: "1px solid var(--border)" }}
                  >
                    <td style={{ padding: "8px 4px" }}>
                      <SourceBadge source={r.source} />
                    </td>
                    <td style={{ padding: "8px 4px" }}>{r.carrier}</td>
                    <td style={{ padding: "8px 4px" }}>
                      {r.service_name ?? r.service_type ?? r.zone}
                    </td>
                    <td style={{ textAlign: "right", padding: "8px 4px" }}>
                      {r.transit_days != null
                        ? `${r.transit_days}${t("fedexRateModal.days")}`
                        : "—"}
                    </td>
                    <td style={{ textAlign: "right", padding: "8px 4px", fontWeight: 600 }}>
                      {Number(r.fee).toLocaleString()}
                    </td>
                    <td style={{ textAlign: "center", padding: "8px 4px" }}>
                      {r.currency}
                    </td>
                    <td style={{ textAlign: "center", padding: "8px 4px" }}>
                      <Button
                        variant="outline"
                        onClick={() => {
                          onSelectRate(r.fee, r.currency, r.service_type, r.carrier);
                          handleClose();
                        }}
                      >
                        {t("fedexRateModal.selectRate")}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {/* フッター */}
      <div style={{ marginTop: "16px", textAlign: "right" }}>
        <Button variant="secondary" onClick={handleClose}>
          {t("fedexRateModal.cancel")}
        </Button>
      </div>
    </Modal>
  );
}
```

### 2-13. frontend/src/components/BillToCountryGuidance.test.tsx（全部書き換え。全文）

```tsx
// ADR-1061 便2-2c2a: 請求先の国が無くて請求書を作れなかったとき、取引先の画面へ移るボタンを出す
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import QuoteDetailPage from '../pages/quote-detail/QuoteDetailPage';
import en from '../locales/en.json';
import { ApiError } from '../lib/api';
import { queryClient } from '../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}<Location /></MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }

const summary = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', total_amount: 10, status: 'approved', created_at: '' };
const detail = { id: 7, quote_code: 'Q-7', company_id: 4, contact_id: 5, currency: 'USD', items: [{ product_id: 2, product_name: 'Card', quantity: 1, unit_price: 10, weight: null }] };
const approvedQuote = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', subtotal: 10, shipping_fee: null, tax_amount: null, total_amount: 10, status: 'approved', validity_date: null, notes: null, created_at: '', items: [] };
const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
// invoice-create-portfolio 便D: 作成画面は請求書の材料の issuer_region が無いときに案内を出す（作る前に分かる）
const draftCtx = (issuerRegion: string | null) => ({
  company_id: 4, ship_to: null, bill_to: null, contact_name: null, contact_email: null,
  issuer_region: issuerRegion, origin_country_code: issuerRegion, destination_country_code: null, destination_postal_code: null,
  currencies: ['USD'], fx_rates: [], default_currency: 'USD', currency: null, payment_methods: [], tax_rate_percent: null, incoterms: 'DAP',
});
let issuer: string | null = null;

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
    if (url === '/quotes?status=approved') return [summary];
    if (url === '/quotes/7') return detail;
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === '/invoices/draft-context?company_id=4&contact_id=5') return draftCtx(issuer);
    throw new Error(`Unexpected GET ${url}`);
  });
  issuer = null;
  mock.post.mockImplementation(async (url: string) => {
    if (url === '/invoices/preview') return { currency: 'USD', subtotal: '10', shipping_fee: null, tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: null, uncomputed: ['shipping_required'], incoterms: 'DAP' };
    throw new Error(`Unexpected post ${url}`);
  });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function loadQuoteIntoCreatePage() {
  render(wrap(<InvoiceCreatePage />));
  fireEvent.click(await screen.findByTestId('invoice-edit-from-quote-7'));
  expect(await screen.findByDisplayValue('Card')).toBeTruthy();
  expect(await screen.findByRole('option', { name: /Buyer/ })).toBeTruthy();
}

describe('bill-to country guidance (ADR-1061 bin2-2c2a)', () => {
  it('create page: without a bill-to country it shows the reason and a button that opens the customer page', async () => {
    issuer = null;
    await loadQuoteIntoCreatePage();
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    expect((screen.getByRole('button', { name: tr('invoices.createBtn') }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });

  it('create page: with a bill-to country the button is not shown', async () => {
    issuer = 'JP';
    await loadQuoteIntoCreatePage();
    expect(await screen.findByTestId('invoice-ship-to-address')).toBeTruthy();
    expect(screen.queryByRole('button', { name: tr('invoices.openCompanyForBillTo') })).toBeNull();
    expect(mock.post).not.toHaveBeenCalledWith('/invoices', expect.anything());
  });

  it('quote detail: converting shows the reason and a button that opens the customer page', async () => {
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions: ['invoices.create'] };
      if (url === '/quotes/7') return approvedQuote;
      throw new Error(`Unexpected GET ${url}`);
    });
    mock.post.mockRejectedValue(new ApiError(tr('apiError.billToCountry'), 422, 'bill_to_country'));
    render(routed(<QuoteDetailPage />, '/quotes/:id', ['/quotes/7']));
    fireEvent.click(await screen.findByRole('button', { name: tr('quotes.convertToInvoice') }));
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect((await screen.findByTestId('location')).textContent).toBe('/crm/companies/4');
  });
});
```

### 2-14. frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx（4 か所。Edit ツール）

(1) 変更前:
```tsx
import { LoadingBlock, Spinner } from "../../components/loading";
```
変更後:
```tsx
import { LoadingBlock, Spinner } from "../../components/loading";
import { InvoicePaymentPicker } from "./InvoicePaymentPicker";
```

(2) 変更前（interface InvoiceDetail の中）:
```tsx
  payment_method: string | null;
```
変更後:
```tsx
  payment_method: string | null;
  payment_method_display_name?: string | null;
  payment_method_type?: string | null;
```

(3) 変更前:
```tsx
          <div><strong>{t("invoices.paymentMethod")}:</strong> {invoice.payment_method || "-"}</div>
```
変更後:
```tsx
          <div><strong>{t("invoices.paymentMethod")}:</strong> {invoice.payment_method_display_name || invoice.payment_method || "-"}</div>
```

(4) 変更前:
```tsx
          {invoice.notes && <div style={{ gridColumn: "1 / -1" }}><strong>{t("common.notes")}:</strong> {invoice.notes}</div>}
```
変更後:
```tsx
          {invoice.notes && <div style={{ gridColumn: "1 / -1" }}><strong>{t("common.notes")}:</strong> {invoice.notes}</div>}
          {invoice.status === "draft" && hasPermission("invoices.create") && hasPermission("invoices.update") && (
            <div style={{ gridColumn: "1 / -1" }} data-testid="invoice-detail-payment-picker">
              <InvoicePaymentPicker invoiceId={String(invoice.id)} currency={invoice.currency} onSaved={load} />
            </div>
          )}
```

### 2-15. frontend/src/components/FedExRateModal.test.tsx（2 か所。Edit ツール）

(1) 変更前:
```tsx
        "fedexRateModal.colCurrency": "Currency",
```
変更後:
```tsx
        "fedexRateModal.colCurrency": "Currency",
        "fedexRateModal.colCarrier": "Carrier",
```

(2) 変更前:
```tsx
    expect(onSelectRate).toHaveBeenCalledWith(5000, "JPY", "FEDEX_IP");
```
変更後:
```tsx
    expect(onSelectRate).toHaveBeenCalledWith(5000, "JPY", "FEDEX_IP", "FedEx");
```

### 2-16. frontend/src/locales/ja.json（3 か所。Edit ツール）

(1) 変更前（最上位の請求書の区切りの始まり。この行の前に足す）:
```json
  "invoices": {
```
変更後:
```json
  "invoiceForm": {
    "sectionShipTo": "届け先・請求先",
    "sectionPaymentTotals": "通貨・支払方法・送料・合計",
    "sectionActions": "作成",
    "chooseCompany": "会社を選ぶと、会社の画面に登録した届け先と請求先が出ます。",
    "contextError": "請求書の材料を読めませんでした",
    "shipTo": "届け先",
    "billTo": "請求先",
    "contact": "担当者",
    "noAddress": "登録がありません",
    "openCompany": "会社の画面で住所を直す",
    "currency": "通貨",
    "currencyPlaceholder": "通貨を選んでください",
    "noCurrency": "選べる通貨がありません。会社の画面と為替の登録を確かめてください。",
    "fxRateLine": "為替 {{currency}}: {{rate}}（{{at}} 時点）",
    "payment": "支払方法",
    "paymentPlaceholder": "支払方法を選んでください",
    "noPaymentMethods": "この通貨で使える支払方法が登録されていません",
    "openTenantProfile": "会社情報の画面で支払方法を登録する",
    "changePayment": "支払方法を選び直す",
    "method_bank": "銀行振込",
    "method_wise": "Wise",
    "method_paypal": "PayPal",
    "shipping": "送料",
    "shippingPlaceholder": "送料の扱いを選んでください",
    "shippingNone": "送料を請求しない",
    "shippingChosen": "{{carrier}} {{service}}（{{fee}}）",
    "shippingQuote": "送料の見積を出して選ぶ",
    "shippingNeedsCountries": "発送元か届け先の国が決まっていないため、送料の見積を出せません。会社情報の画面と会社の画面の住所を確かめてください。",
    "shippingStale": "品物の重さが変わったため、送料をもう一度選んでください。",
    "totalWeight": "総重量",
    "subtotal": "小計",
    "shippingFee": "送料",
    "tax": "消費税（{{rate}}%）",
    "duty": "関税",
    "total": "合計",
    "notComputed": "未計算",
    "uncomputedTitle": "まだ計算できない項目があるため、作成できません",
    "clear": "入力を全部消す"
  },
  "invoices": {
```

(2) 変更前（fedexRateModal の中）:
```json
    "colCurrency": "通貨",
```
変更後:
```json
    "colCurrency": "通貨",
    "colCarrier": "送料の会社",
```

(3) 変更前（secretary.invoice の中）:
```json
      "dueDate": "支払期限",
```
変更後:
```json
      "dueDate": "支払期限",
      "shippingNoneHelp": "チャットでは送料の見積を出せません。送料を付けるときは請求書の作成画面で作ってください。",
```

### 2-17. frontend/src/locales/en.json（3 か所。Edit ツール）

(1) 変更前:
```json
  "invoices": {
```
変更後:
```json
  "invoiceForm": {
    "sectionShipTo": "Ship to / Bill to",
    "sectionPaymentTotals": "Currency, payment, shipping and totals",
    "sectionActions": "Create",
    "chooseCompany": "Choose a company to show the ship-to and bill-to addresses registered on the company page.",
    "contextError": "Could not load the invoice details",
    "shipTo": "Ship to",
    "billTo": "Bill to",
    "contact": "Contact",
    "noAddress": "Not registered",
    "openCompany": "Fix the address on the company page",
    "currency": "Currency",
    "currencyPlaceholder": "Choose a currency",
    "noCurrency": "No currency can be chosen. Check the company page and the exchange rates.",
    "fxRateLine": "Exchange rate {{currency}}: {{rate}} (as of {{at}})",
    "payment": "Payment method",
    "paymentPlaceholder": "Choose a payment method",
    "noPaymentMethods": "No payment method is registered for this currency",
    "openTenantProfile": "Register a payment method on the company profile page",
    "changePayment": "Choose the payment method again",
    "method_bank": "Bank transfer",
    "method_wise": "Wise",
    "method_paypal": "PayPal",
    "shipping": "Shipping",
    "shippingPlaceholder": "Choose how to handle shipping",
    "shippingNone": "Do not charge shipping",
    "shippingChosen": "{{carrier}} {{service}} ({{fee}})",
    "shippingQuote": "Get shipping quotes and choose one",
    "shippingNeedsCountries": "Shipping quotes are not available because the origin or destination country is not set. Check the company profile page and the company address.",
    "shippingStale": "The item weight changed. Choose the shipping again.",
    "totalWeight": "Total weight",
    "subtotal": "Subtotal",
    "shippingFee": "Shipping",
    "tax": "Consumption tax ({{rate}}%)",
    "duty": "Duty",
    "total": "Total",
    "notComputed": "Not calculated",
    "uncomputedTitle": "Some amounts cannot be calculated yet, so the invoice cannot be created",
    "clear": "Clear all input"
  },
  "invoices": {
```

(2) 変更前:
```json
    "colCurrency": "Currency",
```
変更後:
```json
    "colCurrency": "Currency",
    "colCarrier": "Carrier",
```

(3) 変更前:
```json
      "dueDate": "Due date",
```
変更後:
```json
      "dueDate": "Due date",
      "shippingNoneHelp": "Shipping quotes are not available in chat. To charge shipping, create the invoice on the invoice page.",
```

## 3. 手順

手順D1 枝と便 C のコミットを確かめる（枝を取り直さない。card-C.md 手順10 の続き）
    cd ~/sa && git branch --show-current | tail -1
    cd ~/sa && git log --oneline -1 | tail -1
    cd ~/sa && git status --short | wc -l
  期待: 1行目 `release/invoice-create-portfolio-bin-cd`。2行目の題に `invoice-create-portfolio bin C`。3行目 0。外れたら `BLOCKED: 手順D1`。

手順D2 実装前点検 Q1〜Q6 と変更前の文を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls frontend/src/lib/invoiceDraftContext.ts frontend/src/lib/invoiceDraftContext.test.ts frontend/src/pages/invoice-create/useInvoicePreview.ts frontend/src/pages/invoice-create/InvoiceShipToSection.tsx frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx frontend/src/pages/invoice-detail/InvoicePaymentPicker.tsx frontend/src/pages/invoice-detail/InvoicePaymentPicker.test.tsx 2>&1 | grep -c "No such file or directory"
    cd ~/sa && git hash-object frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/features/secretary/SecretaryDraftInvoice.tsx frontend/src/components/FedExRateModal.tsx frontend/src/features/secretary/SecretaryChat.test.tsx frontend/src/components/BillToCountryGuidance.test.tsx | tail -5
    cd ~/sa && grep -c '"/invoices/draft-context"' backend/app/routers/invoices.py
    cd ~/sa && grep -c '"/invoices/preview"' backend/app/routers/invoices.py
    cd ~/sa && grep -c '"taxRate"' frontend/src/locales/ja.json
    cd ~/sa && grep -c '"invoiceForm"' frontend/src/locales/ja.json frontend/src/locales/en.json | tail -2
    cd ~/sa && grep -c -x -F 'import { LoadingBlock, Spinner } from "../../components/loading";' frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
    cd ~/sa && grep -c -x -F '  payment_method: string | null;' frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
    cd ~/sa && grep -c -x -F '          <div><strong>{t("invoices.paymentMethod")}:</strong> {invoice.payment_method || "-"}</div>' frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
    cd ~/sa && grep -c -x -F '          {invoice.notes && <div style={{ gridColumn: "1 / -1" }}><strong>{t("common.notes")}:</strong> {invoice.notes}</div>}' frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
    cd ~/sa && grep -c -x -F '        "fedexRateModal.colCurrency": "Currency",' frontend/src/components/FedExRateModal.test.tsx
    cd ~/sa && grep -c -x -F '    expect(onSelectRate).toHaveBeenCalledWith(5000, "JPY", "FEDEX_IP");' frontend/src/components/FedExRateModal.test.tsx
    cd ~/sa && grep -c -x -F '  "invoices": {' frontend/src/locales/ja.json frontend/src/locales/en.json | tail -2
    cd ~/sa && grep -c -x -F '    "colCurrency": "通貨",' frontend/src/locales/ja.json
    cd ~/sa && grep -c -x -F '    "colCurrency": "Currency",' frontend/src/locales/en.json
    cd ~/sa && grep -c -x -F '      "dueDate": "支払期限",' frontend/src/locales/ja.json
    cd ~/sa && grep -c -x -F '      "dueDate": "Due date",' frontend/src/locales/en.json
  期待: 2行目 8。3行目は上から `a2635433740012bde73d665c65889a71c4557c69`・`8ac4490f3893c3e1b1dc73934f55866f76e0e319`・`dd673984cd00033d9e859be352c4742833b97c6a`・`33efe1087f87cb90f61cd0983bc7de3b2983d823`・`284ea2bf4ac3fe88d5f1ff0e5234baea075211d3`。4〜6行目 1。7行目は2ファイルとも `:0`。8〜13行目 1。14行目は2ファイルとも `:1`。15〜18行目 1。

手順D3 §2 の変更をする（2-1 から順に。新規の 8 ファイルと全部書き換えの 5 ファイルは Write ツールで全文、2-14〜2-17 は Edit ツール）

手順D4 言葉のファイルの形と画面の決まり
    cd ~/sa/frontend && node -e 'for (const f of ["src/locales/ja.json","src/locales/en.json"]) { const j = JSON.parse(require("fs").readFileSync(f,"utf8")); console.log(f, Object.keys(j.invoiceForm).length, j.fedexRateModal.colCarrier ? 1 : 0, j.secretary.invoice.shippingNoneHelp ? 1 : 0); }' | tail -2
    cd ~/sa && grep -c "ui-allow" frontend/src/lib/invoiceDraftContext.ts frontend/src/pages/invoice-create/useInvoicePreview.ts frontend/src/pages/invoice-create/InvoiceShipToSection.tsx frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-detail/InvoicePaymentPicker.tsx frontend/src/features/secretary/SecretaryDraftInvoice.tsx frontend/src/components/FedExRateModal.tsx | tail -8
    cd ~/sa && grep -c "<input\|<textarea\|<select" frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-create/InvoiceShipToSection.tsx frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx frontend/src/pages/invoice-detail/InvoicePaymentPicker.tsx | tail -4
  期待: 1本目は2行とも `38 1 1`（JSON として読めること）。2本目・3本目はどれも `:0`。

手順D5 型の点検（便 C と便 D を合わせた形で通ること）
    cd ~/sa/frontend && npx tsc -b 2>&1 | tail -30
  期待: 何も出ない（終了 0）。

手順D6 言葉と画面の決まりの点検
    cd ~/sa/frontend && npm run check:all 2>&1 | tail -30
  期待: 最後まで通り、失敗の行が無い（終了 0）。

手順D7 新しい試験と、触ったファイルの試験
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/invoiceDraftContext.test.ts src/pages/invoice-create/InvoiceCreatePage.test.tsx src/pages/invoice-detail/InvoicePaymentPicker.test.tsx 2>&1 | tail -25
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/secretary/SecretaryChat.test.tsx src/components/BillToCountryGuidance.test.tsx src/components/FedExRateModal.test.tsx src/lib/apiErrorReason.test.ts 2>&1 | tail -25
  期待: どちらも failed 0（Test Files と Tests の行をそのまま書く）。

手順D8 同じ部品を使う今の試験（変えていないファイル。落ちたら §4 の決まった直し方だけ）
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query/batch3aPages.test.tsx src/lib/query/batch3cPages.test.tsx src/components/AllLegacyButtonDynamicMigration.test.tsx src/components/AllLegacyButtonOperationMigration.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/components/CommerceSubmitButtonMigration.test.tsx 2>&1 | tail -25
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit 2>&1 | tail -15
  期待: 1本目は failed 0。2本目（unit の全部）は failed 0（本数はそのまま書く。時間がかかってよい）。1本目で落ちたファイルが §1 の 18 に当たるときだけ §4 の直し方をして、もう一度同じ行を流す。

手順D9 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -40
    cd ~/sa && git diff --stat | tail -25
  期待: §1 のファイルだけ（新規の 8 ファイルは `??` で各1行。既存は 9 ファイル。§1 の 18 を直したときはそのファイルも）。

手順D10 記録と送り出し
    cd ~/sa && git add frontend/src/lib/invoiceDraftContext.ts frontend/src/lib/invoiceDraftContext.test.ts frontend/src/pages/invoice-create/useInvoicePreview.ts frontend/src/pages/invoice-create/InvoiceShipToSection.tsx frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx && git status --short | tail -40
    cd ~/sa && git add frontend/src/pages/invoice-detail/InvoicePaymentPicker.tsx frontend/src/pages/invoice-detail/InvoicePaymentPicker.test.tsx frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx frontend/src/features/secretary/SecretaryDraftInvoice.tsx frontend/src/features/secretary/SecretaryChat.test.tsx && git status --short | tail -40
    cd ~/sa && git add frontend/src/components/FedExRateModal.tsx frontend/src/components/FedExRateModal.test.tsx frontend/src/components/BillToCountryGuidance.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json && git status --short | tail -40
  §1 の 18 を直したときだけ、次の 1 行も流す（変えていないファイルは add しても何も起きない）。
    cd ~/sa && git add frontend/src/lib/query/batch3aPages.test.tsx frontend/src/lib/query/batch3cPages.test.tsx frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx frontend/src/components/AllLegacyButtonOperationMigration.test.tsx frontend/src/components/CommerceNavigationButtonMigration.test.tsx frontend/src/components/CommerceSubmitButtonMigration.test.tsx && git status --short | tail -40
 最後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoices): let people pick ship-to, currency, payment and shipping instead of typing amounts (invoice-create-portfolio bin D)" && git log --oneline -2 | tail -2
    cd ~/sa && git push -u origin release/invoice-create-portfolio-bin-cd 2>&1 | tail -5
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && git ls-remote origin refs/heads/release/invoice-create-portfolio-bin-cd | tail -1
  期待: log の 2 行が上から便 D・便 C。push は拒否の行が無い。最後の 2 行の 40 桁が同じ。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - 手順D1 の期待が外れた・Q1〜Q6 のどれかが外れた → `BLOCKED: 手順D1` か `BLOCKED: Q番号`。特に Q3 の hash が違うとき（基準の後で誰かが変えた）は全部書き換えをせずに停止する。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 手順D4 の数が期待と違う・JSON として読めない → 出力を貼って `BLOCKED: 手順D4`。
  - 手順D5（tsc）・手順D6（check:all）で失敗の行が出た → 直さず最後の 30 行を貼って `BLOCKED: 手順D5` か `BLOCKED: 手順D6`。ただしカードからの書き写し間違い（字・字下げ・抜け）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。便 C 側のファイルの型の誤りが出たときも直さずに止める（Opus が便 C のカードを直す）。
  - 手順D7 で failed が 1 件でも出た → 試験を直さず最後の 25 行を貼って `BLOCKED: 手順D7`。書き写し間違いの扱いは手順D5 と同じ。
  - 手順D8 の 1 本目で、下の決まった直し方に当たらない理由で落ちた・直してもまだ落ちる → 最後の 25 行を貼って `BLOCKED: 手順D8`。2 本目で §1 に無いファイルが落ちた → 直さずに、そのファイルの名前と最後の 15 行を貼って `BLOCKED: 手順D8 範囲外`。
  - push が拒否された → 出力を貼って `BLOCKED: push`（force はしない）。
- 決まった直し方（手順D8 の 1 本目だけ）: 落ちた理由の行に `/invoices/draft-context` の GET が「Unexpected GET」などで投げられたと出ているときは、その試験のファイルの GET の作り物（mock の中で URL ごとに返す所）に、その URL へ次の値を返す 1 件を足す。ほかの行は変えない。
```ts
{ company_id: 1, ship_to: null, bill_to: null, contact_name: null, contact_email: null, issuer_region: "overseas", origin_country_code: "JP", destination_country_code: "US", destination_postal_code: null, currencies: ["JPY", "USD"], fx_rates: [], default_currency: null, currency: null, payment_methods: [], tax_rate_percent: null, incoterms: "DAP" }
```
  足す前に、frontend/src/lib/invoiceDraftContext.ts の `DraftContext` の型と項目が合っているかを見る。合わない項目があれば足さずに `BLOCKED: 手順D8 型` で停止する。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - vitest や npm が警告（warn）を出す → そのまま書く。
  - 手順D8 の 2 本目が時間切れになった → 最後の 15 行を貼って続ける（CI で全部を流す）。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。card-C.md の報告の後ろに続ける。
- 便 D の 1 行目: `RECEIVED invoice-create-portfolio-D HEAD=…`。2 行目: 「本報告はカード 便D 請求書の作成画面を「選ぶだけ」にする の実行結果である」。
- 手順D1・D2・D4〜D10 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行（実行全体の最後の行）: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規と全部書き換えのファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
