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
