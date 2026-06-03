/**
 * 請求書作成ページ。2 つの導線:
 *   1. 在庫表から: 在庫表でチェックした商品が location.state で渡る（往復対応）。
 *      会社/担当を選び明細を調整して POST /invoices（直接作成）。
 *   2. 既存見積から: 承認済み見積を選ぶと、その明細を編集可能なフォームへ読み込み、
 *      数量・金額を修正して POST /invoices（直接作成）できる（ADR-093 2026-06-03）。
 *
 * 明細エディタは QuoteCreatePage と同一仕様（行内検索/AND-OR を廃し、自由記入＋
 * 「検索して追加」「在庫表から(往復)」の追加方法）。共通ロジックは ../quote-create/quoteDraft。
 */
import { useState, useEffect, FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import InventorySearchBar, { InventorySearchCandidate } from "../../components/InventorySearchBar";
import {
  type LineItem,
  type QuoteDraft,
  type QuoteHandoffState,
  blankItem,
  buildInitialItems,
} from "../quote-create/quoteDraft";

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
    quantity: number;
    unit_price: number;
    weight: number | null;
  }>;
}

function fmtAmount(n: number | null, ccy: string): string {
  if (n == null) return "-";
  try {
    return n.toLocaleString("ja-JP", { style: "currency", currency: ccy });
  } catch {
    return `${ccy} ${Math.round(n).toLocaleString()}`;
  }
}

export default function InvoiceCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const handoff = location.state as QuoteHandoffState;
  const draft = handoff?.draft;
  const hasHandoff = !!(
    (handoff?.selectedProducts && handoff.selectedProducts.length > 0) || draft
  );

  // 在庫表から（往復含む）来た場合は inventory（編集フォーム）モード、そうでなければ見積選択モード。
  const [mode, setMode] = useState<"inventory" | "quote">(hasHandoff ? "inventory" : "quote");

  // --- 編集フォーム（在庫表から / 見積から編集 で共通） ---
  const [companyId, setCompanyId] = useState<number | null>(draft?.companyId ?? null);
  const [contactId, setContactId] = useState<number | null>(draft?.contactId ?? null);
  const [selectorError, setSelectorError] = useState("");
  const [currency, setCurrency] = useState(draft?.currency ?? "USD");
  const [shippingFee, setShippingFee] = useState(draft?.shippingFee ?? "");
  const [taxAmount, setTaxAmount] = useState(draft?.taxAmount ?? "");
  const [notes, setNotes] = useState(draft?.notes ?? "");
  const [items, setItems] = useState<LineItem[]>(() => buildInitialItems(handoff));
  const [addMode, setAddMode] = useState<"inventory" | "search">("search");
  // #8: どの見積から読み込んだか（編集中の見積コード表示用）。
  const [sourceQuoteCode, setSourceQuoteCode] = useState<string | null>(null);

  // --- 見積選択モード ---
  const [quotes, setQuotes] = useState<QuoteSummary[]>([]);
  const [quotesLoading, setQuotesLoading] = useState(false);

  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode !== "quote") return;
    setQuotesLoading(true);
    setError("");
    api
      .get<QuoteSummary[]>("/quotes?status=approved")
      .then(setQuotes)
      .catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setQuotesLoading(false));
  }, [mode, t]);

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
        quantity: isOutOfStock ? 0 : 1,
        unit_price: c.unit_price ?? 0,
        weight: null,
        inventory_id: null,
        zero_stock_warning: isOutOfStock,
      },
    ]);
  };
  // 「在庫表から」: ドラフトを持って在庫表へ。在庫表で選択して戻ると反映される。
  const goToInventory = () => {
    const currentDraft: QuoteDraft = { items, companyId, contactId, currency, notes, shippingFee, taxAmount };
    navigate("/inventory", {
      state: {
        fromQuote: true,
        returnTo: "/invoices/new",
        draft: currentDraft,
        preselectedInventoryIds: items.filter((i) => i.inventory_id != null).map((i) => i.inventory_id),
      },
    });
  };

  // #8: 承認済み見積を編集可能な明細としてフォームへ読み込む。
  const loadQuoteForEdit = async (quoteId: number) => {
    setError("");
    setSaving(true);
    try {
      const q = await api.get<QuoteDetail>(`/quotes/${quoteId}`);
      setCompanyId(q.company_id);
      setContactId(q.contact_id ?? null);
      setCurrency(q.currency);
      setItems(
        q.items.length > 0
          ? q.items.map((it) => ({
              product_id: it.product_id,
              product_name: it.product_name,
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

  const subtotal = items.reduce((s, it) => s + it.quantity * it.unit_price, 0);
  const shipping = shippingFee ? Number(shippingFee) : 0;
  const tax = taxAmount ? Number(taxAmount) : 0;
  const total = subtotal + shipping + tax;

  const submitInvoice = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSelectorError("");
    if (contactId === null) {
      setSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    if (items.some((i) => !i.product_name || i.unit_price <= 0 || i.quantity <= 0)) {
      setError(t("quotes.itemsRequired"));
      return;
    }
    setSaving(true);
    try {
      const inv = await api.post<{ id: number }>("/invoices", {
        company_id: companyId,
        contact_id: contactId,
        currency,
        shipping_fee: shipping || null,
        tax_amount: tax || null,
        notes: notes || null,
        items: items.map((i) => ({
          product_id: i.product_id,
          product_name: i.product_name,
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

  // 在庫表起点で開いた場合のキャンセルは在庫表へ。
  const cameFromInventory = hasHandoff;

  return (
    <div className="page">
      <div className="page-header">
        {/* eslint-disable-next-line no-restricted-syntax -- 作成ページ(route param 無し)は navKey 制約対象外 */}
        <h2>{t("invoices.createTitle")}</h2>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <button className="btn-secondary" onClick={() => navigate("/management-center/tenant-profile")}>
            {t("nav.tenantProfile")}
          </button>
          <button className="btn-secondary" onClick={() => navigate("/invoices")}>
            {t("common.back")}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div style={{ display: "flex", gap: "var(--space-2)", margin: "var(--space-3) 0" }}>
        <button
          className={mode === "inventory" ? "btn-primary" : "btn-secondary"}
          onClick={() => setMode("inventory")}
          data-testid="invoice-mode-inventory"
        >
          {t("invoices.fromInventory")}
        </button>
        <button
          className={mode === "quote" ? "btn-primary" : "btn-secondary"}
          onClick={() => { setSourceQuoteCode(null); setMode("quote"); }}
          data-testid="invoice-mode-quote"
        >
          {t("invoices.fromQuote")}
        </button>
      </div>

      {mode === "quote" ? (
        <div data-testid="invoice-from-quote">
          <p style={{ color: "var(--text-secondary)" }}>{t("invoices.fromQuoteHelp")}</p>
          {quotesLoading ? (
            <div className="loading">{t("common.loading")}</div>
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
                    <td>{fmtAmount(q.total_amount, q.currency)}</td>
                    <td>
                      <button
                        className="btn-sm btn-primary"
                        disabled={saving}
                        onClick={() => loadQuoteForEdit(q.id)}
                        data-testid={`invoice-edit-from-quote-${q.id}`}
                      >
                        {t("invoices.editFromThisQuote")}
                      </button>
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
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
            <CompanyContactSelector
              value={{ companyId, contactId }}
              onChange={({ companyId: c, contactId: ct }) => { setCompanyId(c); setContactId(ct); }}
              required
              error={selectorError}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-6)" }}>
            <div className="form-group">
              <label>{t("common.currency")}</label>
              <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
                <option value="JPY">JPY</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
              </select>
            </div>
            <div className="form-group">
              <label>{t("common.notes")}</label>
              <input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>

          <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
          {/* 明細ゾーン: 行内検索/AND-OR は廃止。商品名は自由記入可。 */}
          <div style={{ overflowX: "auto", marginBottom: "var(--space-4)" }}>
            <table className="data-table" style={{ minWidth: "var(--table-min-width-base)" }}>
              <thead>
                <tr>
                  <th>{t("quotes.product")}</th>
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
                      <input value={item.product_name} onChange={(e) => updateItem(i, "product_name", e.target.value)} placeholder={t("quotes.productNamePlaceholder")} style={{ width: "100%", minWidth: "var(--input-width-product-name)" }} data-testid={`invoice-item-row-${i}-name`} />
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
                      <input type="number" min="1" value={item.quantity} onChange={(e) => updateItem(i, "quantity", Number(e.target.value))} style={{ width: "var(--input-width-qty)" }} />
                    </td>
                    <td>
                      <input type="number" min="0" step="0.01" value={item.unit_price} onChange={(e) => updateItem(i, "unit_price", Number(e.target.value))} style={{ width: "var(--input-width-year)" }} />
                    </td>
                    <td>
                      <input type="number" min="0" step="0.001" value={item.weight || ""} onChange={(e) => updateItem(i, "weight", e.target.value ? Number(e.target.value) : null)} style={{ width: "var(--input-width-weight)" }} />
                    </td>
                    <td style={{ fontWeight: "var(--font-weight-semi)", whiteSpace: "nowrap" }}>{(item.quantity * item.unit_price).toLocaleString()}</td>
                    <td>
                      {items.length > 1 && (
                        <button type="button" className="btn-sm btn-danger" onClick={() => removeItem(i)}>{t("quotes.removeItem")}</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 明細の追加方法（見積作成と同仕様）: [在庫表から(往復)] / [検索して追加・新規追加] */}
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap", marginBottom: "var(--space-3)" }}>
            {addMode === "search" ? (
              <button type="button" className="btn-secondary" onClick={addItem} data-testid="invoice-add-blank">{t("quotes.addItem")}</button>
            ) : (
              <button type="button" className="btn-secondary" onClick={goToInventory} data-testid="invoice-add-from-inventory">{t("quotes.addFromInventory")}</button>
            )}
            <div role="radiogroup" aria-label={t("quotes.addMethod")} style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                <input type="radio" name="invoice-add-mode" data-testid="invoice-add-mode-inventory" checked={addMode === "inventory"} onChange={() => setAddMode("inventory")} />
                {t("quotes.addModeInventory")}
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                <input type="radio" name="invoice-add-mode" data-testid="invoice-add-mode-search" checked={addMode === "search"} onChange={() => setAddMode("search")} />
                {t("quotes.addModeSearch")}
              </label>
            </div>
          </div>

          {addMode === "search" && (
            <div style={{ width: "min(100%, 40rem)", marginBottom: "var(--space-6)" }}>
              <InventorySearchBar onSelect={appendFromSearch} testIdPrefix="invoice-add-search" />
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-6)" }}>
            <div className="form-group">
              <label>{t("quotes.shippingFee")}</label>
              <input type="number" min="0" step="1" value={shippingFee} onChange={(e) => setShippingFee(e.target.value)} />
            </div>
            <div className="form-group">
              <label>{t("quotes.tax")}</label>
              <input type="number" min="0" step="1" value={taxAmount} onChange={(e) => setTaxAmount(e.target.value)} />
            </div>
            <div className="form-group">
              <label>{t("quotes.total")}</label>
              <div style={{ padding: "var(--space-2) var(--space-3)", fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>{total.toLocaleString()} {currency}</div>
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate(cameFromInventory ? "/inventory" : "/invoices")}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? t("common.saving") : t("invoices.createBtn")}</button>
          </div>
        </form>
      )}
    </div>
  );
}
