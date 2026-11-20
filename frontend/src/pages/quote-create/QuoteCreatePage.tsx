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
 *   2026-11-20: invoice-create-portfolio 便R7 — 商品行を請求書と同じ LineItemsTable に替えた
 *     （在庫の道・為替の道 GET /fx-rates/{通貨}。自由記入の行と検索で足す欄は廃止。design-v2 §3-8-1・K16）。
 */

import { useEffect, useState, FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import { PageLayout } from "../../components/PageLayout";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import { FedExRateModal } from "../../components/FedExRateModal";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import type { LineItem, QuoteHandoffState } from "./quoteDraft";
import { LineItemsTable } from "./LineItemsTable";
import { allRowsReady, filledRows, handoffRows, reconvertPrices, rowSubtotal, toInvoiceItem, totalWeight } from "./lineItems";
import { useDraftInventory } from "./useDraftInventory";
import { TextFieldControl } from "../../components/TextField";

export default function QuoteCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const handoff = location.state as QuoteHandoffState;
  const draft = handoff?.draft;
  const [companyId, setCompanyId] = useState<number | null>(draft?.companyId ?? null);
  const [contactId, setContactId] = useState<number | null>(draft?.contactId ?? null);
  const [selectorError, setSelectorError] = useState("");
  // 既定通貨は USD（往復ドラフトがあればその通貨を引き継ぐ）。
  const [currency, setCurrency] = useState(draft?.currency ?? "USD");
  const [shippingFee, setShippingFee] = useState(draft?.shippingFee ?? "");
  const [taxAmount, setTaxAmount] = useState(draft?.taxAmount ?? "");
  const [notes, setNotes] = useState(draft?.notes ?? "");
  // 商品行は請求書と同じ形（在庫表の画面から持ってきた商品が先頭の行・12行まで空の行。design-v2 §3-8-1）
  const [rows, setRows] = useState<LineItem[]>(() => handoffRows(handoff));
  const [showErrors, setShowErrors] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [showFedExModal, setShowFedExModal] = useState(false);

  // 在庫は請求書と同じ道（GET /invoices/draft-inventory。K23）
  const inventory = useDraftInventory();
  // 為替は今ある道 GET /fx-rates/{通貨}（請求書の draft-context と同じ表の最新の1行）。円は読まない。読めない・404 は為替なし（単価 0。design-v2 §8）
  const fxQ = useApiQuery<{ currency: string; rate_jpy: number }>(`/fx-rates/${currency}`, { enabled: currency !== "JPY" });
  const rate = currency !== "JPY" && fxQ.data !== undefined && fxQ.data.rate_jpy > 0 ? fxQ.data.rate_jpy : null;

  // 通貨（または為替）が変わったら、単価を手で直していない行だけ入れ直す（PO 2026-11-18「1」）
  useEffect(() => {
    setRows((prev) => reconvertPrices(prev, currency, rate));
  }, [currency, rate]);

  const subtotal = filledRows(rows).reduce((sum, row) => sum + rowSubtotal(row), 0);
  // 総重量 = 商品の入った行の 重さ×数量 の和（lineItems.ts totalWeight）
  const totalWeightKg = totalWeight(rows);
  const shipping = shippingFee ? Number(shippingFee) : 0;
  const tax = taxAmount ? Number(taxAmount) : 0;
  const total = subtotal + shipping + tax;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSelectorError("");
    if (contactId === null) { setSelectorError(t("companyContactSelector.contactRequired")); return; }
    if (!allRowsReady(rows)) {
      setShowErrors(true);
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
        items: filledRows(rows).map(toInvoiceItem),
      });
      navigate("/quotes");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageLayout titleText={t("quotes.newQuote")} subtitleKey="quotes.createSubtitle">

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
            <SelectControl fullWidth value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="JPY">JPY</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </SelectControl>
          </div>
          <div className="form-group"><label>{t("common.notes")}</label>
            <TextFieldControl value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
        {/* 商品行は請求書と同じ表（#・カテゴリ・商品・状態・数量・重さ・単価・小計・×。design-v2 §3-8-1・K16）。値段・在庫・重さは在庫の道の値だけ。 */}
        <div style={{ marginBottom: "var(--space-6)" }}>
          <LineItemsTable
            rows={rows}
            onChange={setRows}
            inventory={inventory}
            currency={currency}
            rate={rate}
            showErrors={showErrors}
            disabled={saving}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-6)" }}>
          <div className="form-group"><label>{t("quotes.shippingFee")}</label>
            <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
              <TextFieldControl type="number" min="0" step="1" value={shippingFee} onChange={(e) => setShippingFee(e.target.value)} data-testid="shipping-fee-input" />
              <Button type="button" variant="secondary" size="sm" onClick={() => setShowFedExModal(true)} data-testid="fedex-estimate-btn">{t("quotes.fedexEstimate")}</Button>
            </div>
          </div>
          <div className="form-group"><label>{t("quotes.tax")}</label>
            <TextFieldControl type="number" min="0" step="1" value={taxAmount} onChange={(e) => setTaxAmount(e.target.value)} />
          </div>
          <div className="form-group"><label>{t("quotes.total")}</label>
            <div style={{ padding: "var(--space-2) var(--space-3)", fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>{total.toLocaleString()} {currency}</div>
          </div>
          <div className="form-group"><label>{t("quotes.totalWeight")}</label>
            <div style={{ padding: "var(--space-2) var(--space-3)", fontWeight: "var(--font-weight-semi)" }} data-testid="quote-total-weight">{totalWeightKg.toLocaleString()} kg</div>
          </div>
        </div>

        <div className="form-actions">
          <Button type="button" variant="secondary" size="md" onClick={() => navigate("/quotes")}>{t("common.cancel")}</Button>
          <Button loading={saving} type="submit" variant="primary" size="md" disabled={saving}>{t("quotes.saveDraft")}</Button>
        </div>
      </form>
      <FedExRateModal
        open={showFedExModal}
        onClose={() => setShowFedExModal(false)}
        weightKg={totalWeightKg}
        onSelectRate={(fee) => setShippingFee(String(Math.round(fee)))}
      />
    </PageLayout>
  );
}
