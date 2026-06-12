/**
 * 請求書詳細ページ。
 * ステータスアクション（発行/入金/無効化）+ 明細表示。
 *
 * 変更履歴:
 *   2026-04-17: 初版作成（Phase 2）
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { getStatusPresentation } from "../../utils/statusPresentation";

interface InvoiceItem {
  id: number;
  product_name: string;
  name_en: string | null;
  condition: string | null;
  unit: string | null;
  quantity: number;
  unit_price: number;
  weight: number | null;
  subtotal: number;
}

interface AddressSnapshot {
  company_name?: string;
  contact_name?: string;
  label?: string;
  postal_code?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  tax_id?: string;
  phone?: string;
  email?: string;
}

interface FxRateSnapshot {
  currency: string;
  rate: number;
  fetched_at?: string;
}

interface InvoiceDetail {
  id: number;
  invoice_number: string | null;
  quote_id: number | null;
  // Step 5d: 旧 customer_id を撤去、company_id を必須化
  company_id: number;
  currency: string;
  subtotal: number | null;
  shipping_fee: number | null;
  tax_amount: number | null;
  total_amount: number | null;
  exchange_rate_jpy: number | null;
  exchange_rate_usd: number | null;
  amount_jpy: number | null;
  amount_usd: number | null;
  payment_method: string | null;
  status: string;
  branch_number: number | null;
  erp_key: string | null;
  issued_at: string | null;
  due_date: string | null;
  paid_at: string | null;
  voided_at: string | null;
  void_reason: string | null;
  notes: string | null;
  created_at: string;
  items: InvoiceItem[];
  // C-6: スナップショット列
  ship_to_snapshot: AddressSnapshot | null;
  bill_to_snapshot: AddressSnapshot | null;
  duty_amount: number | null;
  fx_rate_snapshot: FxRateSnapshot | null;
  // ADR-101 PayPal mode1: 決済リンク
  paypal_order_id: string | null;
  paypal_approval_url: string | null;
  payment_fee: number | null;
  // ADR-101改訂(2) Inc1: 発行者ビュー（原本ワンクリック）
  paypal_invoicer_view_url: string | null;
}

export default function InvoiceDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [voidReason, setVoidReason] = useState("");
  const [showVoidForm, setShowVoidForm] = useState(false);

  const load = async () => {
    try {
      const data = await api.get<InvoiceDetail>(`/invoices/${id}`);
      setInvoice(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [id]);

  const doAction = async (action: string, body: unknown = {}) => {
    try {
      await api.post(`/invoices/${id}/${action}`, body);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };

  const handleVoid = async () => {
    if (!voidReason.trim()) { setError(t("invoices.voidReasonRequired")); return; }
    await doAction("void", { reason: voidReason });
    setShowVoidForm(false);
    setVoidReason("");
  };

  const handleDownloadPdf = () => {
    window.open(`/api/invoices/${id}/pdf`, "_blank");
  };

  const handleDownloadCopyPdf = () => {
    window.open(`/api/invoices/${id}/paypal-copy-pdf`, "_blank");
  };

  const fmt = (n: number | null) => n != null ? n.toLocaleString() : "-";

  const renderAddressSnapshot = (snap: AddressSnapshot | null, label: string) => {
    if (!snap) return null;
    const lines = [
      snap.company_name,
      snap.contact_name,
      snap.address,
      [snap.city, snap.state].filter(Boolean).join(", "),
      snap.country,
      snap.tax_id ? `Tax ID: ${snap.tax_id}` : null,
      snap.phone ? `TEL: ${snap.phone}` : null,
    ].filter(Boolean);
    if (lines.length === 0) return null;
    return (
      <div>
        <strong>{label}</strong>
        <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
          {lines.map((line, idx) => <div key={idx}>{line}</div>)}
        </div>
      </div>
    );
  };

  if (loading) return <div className="page"><div className="loading">{t("common.loading")}</div></div>;
  if (!invoice) return <div className="page"><div className="error-message">{error || t("common.fetchError")}</div></div>;

  // 総重量 = Σ(数量 × 行重量)。
  const invoiceTotalWeight = invoice.items.reduce((s, it) => s + it.quantity * (it.weight ?? 0), 0);

  return (
    <div className="page">
      <div className="page-header">
        {/* eslint-disable-next-line no-restricted-syntax */}
        <h2>{t("invoices.title")} — {invoice.invoice_number || `#${invoice.id}`}</h2>
        <div className="actions" style={{ display: "flex", gap: "var(--space-2)" }}>
          {invoice.status === "draft" && hasPermission("invoices.create") && (
            <button className="btn-primary" onClick={() => doAction("issue")}>{t("invoices.issueAction")}</button>
          )}
          {(invoice.status === "issued" || invoice.status === "overdue") && hasPermission("invoices.update") && (
            <button className="btn-primary" onClick={() => doAction("pay")}>{t("invoices.payAction")}</button>
          )}
          {(invoice.status === "issued" || invoice.status === "overdue") && hasPermission("invoices.update") && !invoice.paypal_approval_url && (
            <button className="btn-secondary" onClick={() => doAction("paypal-link")}>{t("invoices.paypal.issueLink")}</button>
          )}
          {(invoice.status === "issued" || invoice.status === "overdue") && hasPermission("invoices.update") && invoice.paypal_approval_url && (
            <button className="btn-primary" onClick={() => doAction("paypal-confirm")}>{t("invoices.paypal.confirm")}</button>
          )}
          {invoice.status !== "voided" && hasPermission("invoices.void") && (
            <button className="btn-danger" onClick={() => setShowVoidForm(true)}>{t("invoices.voidAction")}</button>
          )}
          <button className="btn-secondary" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</button>
          <button className="btn-secondary" onClick={() => navigate("/invoices/new")}>{t("common.back")}</button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {invoice.paypal_approval_url && invoice.status !== "paid" && (
        <div style={{ border: "1px solid var(--border)", padding: "var(--space-3)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-4)" }}>
          <div style={{ fontWeight: "var(--font-weight-semi)", marginBottom: "var(--space-1)" }}>{t("invoices.paypal.linkTitle")}</div>
          <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>{t("invoices.paypal.linkHint")}</div>
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
            <input readOnly value={invoice.paypal_approval_url} style={{ flex: 1, padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", fontSize: "var(--font-sm)" }} />
            <a className="btn-secondary" href={invoice.paypal_approval_url} target="_blank" rel="noopener noreferrer">{t("invoices.paypal.openLink")}</a>
          </div>
        </div>
      )}

      {invoice.paypal_order_id && (
        <div style={{ border: "1px solid var(--border)", padding: "var(--space-3)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-4)" }}>
          <div style={{ fontWeight: "var(--font-weight-semi)", marginBottom: "var(--space-2)" }}>{t("invoices.paypal.recordTitle")}</div>
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap" }}>
            {invoice.paypal_invoicer_view_url && (
              <a className="btn-secondary" href={invoice.paypal_invoicer_view_url} target="_blank" rel="noopener noreferrer">{t("invoices.paypal.openOriginal")}</a>
            )}
            <button className="btn-secondary" onClick={handleDownloadCopyPdf}>{t("invoices.paypal.downloadCopyPdf")}</button>
          </div>
        </div>
      )}

      {showVoidForm && (
        <div style={{ background: "var(--danger-bg)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-4)" }}>
          <label style={{ display: "block", marginBottom: "var(--space-2)", fontWeight: "var(--font-weight-semi)", color: "var(--danger-text)" }}>{t("invoices.voidReasonLabel")} *</label>
          <input style={{ width: "100%", padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}
                 value={voidReason} onChange={(e) => setVoidReason(e.target.value)} placeholder={t("invoices.voidReasonPlaceholder")} />
          <div style={{ marginTop: "var(--space-2)", display: "flex", gap: "var(--space-2)" }}>
            <button className="btn-secondary" onClick={() => setShowVoidForm(false)}>{t("common.cancel")}</button>
            <button className="btn-danger" onClick={handleVoid}>{t("invoices.voidExecute")}</button>
          </div>
        </div>
      )}

      <div style={{ background: "var(--bg-surface)", padding: "var(--space-6)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)", marginBottom: "var(--space-6)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-4)" }}>
          <div><strong>{t("common.status")}:</strong> <span className={`badge badge-${getStatusPresentation("invoice", invoice.status).badgeVariant}`}>{t(`invoices.status_${invoice.status}`)}</span></div>
          <div><strong>{t("common.currency")}:</strong> {invoice.currency}</div>
          <div><strong>{t("invoices.paymentMethod")}:</strong> {invoice.payment_method || "-"}</div>
          <div><strong>{t("invoices.issuedAt")}:</strong> {invoice.issued_at ? new Date(invoice.issued_at).toLocaleDateString() : "-"}</div>
          <div><strong>{t("invoices.dueDate")}:</strong> {invoice.due_date || "-"}</div>
          <div><strong>{t("invoices.paidAt")}:</strong> {invoice.paid_at ? new Date(invoice.paid_at).toLocaleDateString() : "-"}</div>
          <div><strong>{t("invoices.exchangeRateJpy")}:</strong> {invoice.exchange_rate_jpy ?? "-"}</div>
          <div><strong>{t("invoices.exchangeRateUsd")}:</strong> {invoice.exchange_rate_usd ?? "-"}</div>
          <div><strong>ERP Key:</strong> <span className="mono">{invoice.erp_key || "-"}</span></div>
          {invoice.void_reason && <div style={{ gridColumn: "1 / -1" }}><strong>{t("invoices.voidReasonLabel")}:</strong> {invoice.void_reason}</div>}
          {invoice.notes && <div style={{ gridColumn: "1 / -1" }}><strong>{t("common.notes")}:</strong> {invoice.notes}</div>}
        </div>
      </div>

      {/* C-6: スナップショット表示 */}
      {(invoice.ship_to_snapshot || invoice.bill_to_snapshot) && (
        <div style={{ background: "var(--bg-surface)", padding: "var(--space-6)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)", marginBottom: "var(--space-6)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
            {renderAddressSnapshot(invoice.bill_to_snapshot, t("invoices.snapshot.billTo"))}
            {renderAddressSnapshot(invoice.ship_to_snapshot, t("invoices.snapshot.shipTo"))}
          </div>
        </div>
      )}

      <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
      <table className="data-table" style={{ marginBottom: "var(--space-6)" }}>
        <thead>
          <tr><th>{t("quotes.titleColumn")}</th><th>{t("quotes.condition")}</th><th>{t("quotes.unit")}</th><th>{t("quotes.quantity")}</th><th>{t("quotes.unitPrice")}</th><th>{t("quotes.weight")}</th><th>{t("quotes.subtotal")}</th></tr>
        </thead>
        <tbody>
          {invoice.items.map((item) => (
            <tr key={item.id}>
              <td>
                {/* 英語タイトルをメイン(太字)、日本語を参考表示。英語が無ければ日本語のみ。 */}
                {item.name_en ? (
                  <>
                    <div style={{ fontWeight: "var(--font-weight-semi)" }}>{item.name_en}</div>
                    <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{item.product_name}</div>
                  </>
                ) : (
                  item.product_name
                )}
              </td>
              <td>{item.condition || "-"}</td>
              <td>{item.unit || "-"}</td>
              <td>{item.quantity}</td>
              <td>{fmt(item.unit_price)}</td>
              <td>{item.weight != null ? `${item.weight}kg` : "-"}</td>
              <td style={{ fontWeight: "var(--font-weight-semi)" }}>{fmt(item.subtotal)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr><td colSpan={6} style={{ textAlign: "right", fontWeight: "var(--font-weight-semi)" }}>{t("quotes.subtotal")}</td><td style={{ fontWeight: "var(--font-weight-semi)" }}>{fmt(invoice.subtotal)}</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right" }}>{t("quotes.totalWeight")}</td><td>{invoiceTotalWeight.toLocaleString()} kg</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right" }}>{t("quotes.shippingFee")}</td><td>{fmt(invoice.shipping_fee)}</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right" }}>{t("quotes.tax")}</td><td>{fmt(invoice.tax_amount)}</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right", fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>{t("quotes.total")}</td><td style={{ fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>{fmt(invoice.total_amount)} {invoice.currency}</td></tr>
          {invoice.amount_jpy != null && <tr><td colSpan={6} style={{ textAlign: "right", color: "var(--text-muted)" }}>{t("invoices.jpyEquiv")}</td><td style={{ color: "var(--text-muted)" }}>¥{invoice.amount_jpy.toLocaleString()}</td></tr>}
          {invoice.amount_usd != null && <tr><td colSpan={6} style={{ textAlign: "right", color: "var(--text-muted)" }}>{t("invoices.usdConvert")}</td><td style={{ color: "var(--text-muted)" }}>${invoice.amount_usd.toLocaleString()}</td></tr>}
        </tfoot>
      </table>
    </div>
  );
}
