/**
 * 見積もり作成ページ。
 * 顧客選択 + 明細行追加 + 送料自動計算 → draft で保存。
 *
 * 変更履歴:
 *   2026-04-17: 初版作成（Phase 2）
 *   2026-04-25: Phase 1-B-2 Step 5c-3 — 顧客セレクタを CompanyContactSelector に置換。
 *   2026-05-22: Sprint 7 / F7 — 商品選択を InventorySearchBar に置換。
 *   2026-06-03: ADR-093 明細 UX 刷新 — 行内検索/AND-OR を廃止。明細追加は
 *     [在庫表から(往復)] / [検索して追加・新規追加(自由記入可)] のモード切替に。
 *     在庫表往復ではドラフト全体（顧客・通貨・明細・送料等）を保持する。
 *     在庫表起点で開いた場合、キャンセルは在庫表へ戻る。
 */

import { useState, FormEvent } from "react";
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
} from "./quoteDraft";

export default function QuoteCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const handoff = location.state as QuoteHandoffState;
  const draft = handoff?.draft;
  // 在庫表起点（新規 or 往復）かどうか。キャンセル先の判定に使う。
  const cameFromInventory = !!(
    handoff?.fromInventory ||
    handoff?.draft ||
    (handoff?.selectedProducts && handoff.selectedProducts.length > 0)
  );

  const [companyId, setCompanyId] = useState<number | null>(draft?.companyId ?? null);
  const [contactId, setContactId] = useState<number | null>(draft?.contactId ?? null);
  const [selectorError, setSelectorError] = useState("");
  const [currency, setCurrency] = useState(draft?.currency ?? "JPY");
  const [shippingFee, setShippingFee] = useState(draft?.shippingFee ?? "");
  const [taxAmount, setTaxAmount] = useState(draft?.taxAmount ?? "");
  const [notes, setNotes] = useState(draft?.notes ?? "");
  const [items, setItems] = useState<LineItem[]>(() => buildInitialItems(handoff));
  // 明細の追加方法: 在庫表から（往復） / 検索して追加・新規追加。
  const [addMode, setAddMode] = useState<"inventory" | "search">("search");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // 自由記入の空行を追加（マスタに無い商品も入力できる）。
  const addItem = () => {
    setItems((prev) => [...prev, { ...blankItem }]);
  };

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

  // 「検索して追加」: InventorySearchBar の選択商品を新しい明細行として追加する（上書きではなく追加）。
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

  // 「在庫表から」: ドラフト全体を持って在庫表へ移動。在庫表で追加選択して
  // 「見積書作成」を押すと、選択が反映された状態でここへ戻る。
  const goToInventory = () => {
    const currentDraft: QuoteDraft = { items, companyId, contactId, currency, notes, shippingFee, taxAmount };
    navigate("/inventory", {
      state: {
        fromQuote: true,
        returnTo: "/quotes/new",
        draft: currentDraft,
        preselectedInventoryIds: items
          .filter((i) => i.inventory_id != null)
          .map((i) => i.inventory_id),
      },
    });
  };

  const subtotal = items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0);
  const shipping = shippingFee ? Number(shippingFee) : 0;
  const tax = taxAmount ? Number(taxAmount) : 0;
  const total = subtotal + shipping + tax;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSelectorError("");
    if (contactId === null) { setSelectorError(t("companyContactSelector.contactRequired")); return; }
    if (items.some((i) => !i.product_name || i.unit_price <= 0 || i.quantity <= 0)) {
      setError(t("quotes.itemsRequired"));
      return;
    }
    setSaving(true);
    try {
      await api.post("/quotes", {
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
      navigate("/quotes");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        {/* eslint-disable-next-line no-restricted-syntax */}
        <h2>{t("quotes.newQuote")}</h2>
      </div>

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit} style={{ background: "var(--bg-surface)", padding: "var(--space-6)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
          <CompanyContactSelector
            value={{ companyId, contactId }}
            onChange={({ companyId: c, contactId: ct }) => {
              setCompanyId(c);
              setContactId(ct);
            }}
            required
            error={selectorError}
          />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-6)" }}>
          <div className="form-group"><label>{t("common.currency")}</label>
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="JPY">JPY</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div className="form-group"><label>{t("common.notes")}</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
        {/* 明細表示ゾーン: 行内検索/AND-OR は廃止。商品名は自由記入可（マスタに無い商品も入力できる）。 */}
        <div style={{ overflowX: "auto", marginBottom: "var(--space-4)" }}>
          <table className="data-table" style={{ minWidth: 'var(--table-min-width-base)' }}>
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
                <tr key={i} data-testid={`quote-item-row-${i}`}>
                  <td style={{ minWidth: 'var(--table-col-product-name-min-w)' }}>
                    <input value={item.product_name} onChange={(e) => updateItem(i, "product_name", e.target.value)} placeholder={t("quotes.productNamePlaceholder")} style={{ width: "100%", minWidth: 'var(--input-width-product-name)' }} data-testid={`quote-item-row-${i}-name`} />
                    {item.zero_stock_warning && (
                      <div
                        data-testid={`quote-item-row-${i}-zero-stock-warning`}
                        className="warning-message"
                        style={{ marginTop: "var(--space-1)", color: "var(--color-warning)", fontSize: "var(--font-sm)" }}
                      >
                        {t("inventory.search.zeroStockWarning", { name: item.product_name })}
                      </div>
                    )}
                  </td>
                  <td>
                    <input type="number" min="1" value={item.quantity} onChange={(e) => updateItem(i, "quantity", Number(e.target.value))} style={{ width: 'var(--input-width-qty)' }} />
                  </td>
                  <td>
                    <input type="number" min="0" step="0.01" value={item.unit_price} onChange={(e) => updateItem(i, "unit_price", Number(e.target.value))} style={{ width: 'var(--input-width-year)' }} />
                  </td>
                  <td>
                    <input type="number" min="0" step="0.001" value={item.weight || ""} onChange={(e) => updateItem(i, "weight", e.target.value ? Number(e.target.value) : null)} style={{ width: 'var(--input-width-weight)' }} />
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

        {/* 明細の追加方法: [在庫表から(往復)] / [検索して追加・新規追加]。 */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap", marginBottom: "var(--space-3)" }}>
          {addMode === "search" ? (
            <button type="button" className="btn-secondary" onClick={addItem} data-testid="quote-add-blank">{t("quotes.addItem")}</button>
          ) : (
            <button type="button" className="btn-secondary" onClick={goToInventory} data-testid="quote-add-from-inventory">{t("quotes.addFromInventory")}</button>
          )}
          <div role="radiogroup" aria-label={t("quotes.addMethod")} style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
              <input type="radio" name="quote-add-mode" data-testid="quote-add-mode-inventory" checked={addMode === "inventory"} onChange={() => setAddMode("inventory")} />
              {t("quotes.addModeInventory")}
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
              <input type="radio" name="quote-add-mode" data-testid="quote-add-mode-search" checked={addMode === "search"} onChange={() => setAddMode("search")} />
              {t("quotes.addModeSearch")}
            </label>
          </div>
        </div>

        {/* 「検索して追加」モード: 幅広の検索窓。選択すると明細ゾーンに行が追加される。 */}
        {addMode === "search" && (
          <div style={{ width: "min(100%, 40rem)", marginBottom: "var(--space-6)" }}>
            <InventorySearchBar onSelect={appendFromSearch} testIdPrefix="quote-add-search" />
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-6)" }}>
          <div className="form-group"><label>{t("quotes.shippingFee")}</label>
            <input type="number" min="0" step="1" value={shippingFee} onChange={(e) => setShippingFee(e.target.value)} />
          </div>
          <div className="form-group"><label>{t("quotes.tax")}</label>
            <input type="number" min="0" step="1" value={taxAmount} onChange={(e) => setTaxAmount(e.target.value)} />
          </div>
          <div className="form-group"><label>{t("quotes.total")}</label>
            <div style={{ padding: "var(--space-2) var(--space-3)", fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>{total.toLocaleString()} {currency}</div>
          </div>
        </div>

        <div className="form-actions">
          {/* 在庫表起点で開いた場合のキャンセルは在庫表へ戻す（請求書一覧に飛ばさない）。 */}
          <button type="button" className="btn-secondary" onClick={() => navigate(cameFromInventory ? "/inventory" : "/quotes")}>{t("common.cancel")}</button>
          <button type="submit" className="btn-primary" disabled={saving}>{saving ? t("common.saving") : t("quotes.saveDraft")}</button>
        </div>
      </form>
    </div>
  );
}
