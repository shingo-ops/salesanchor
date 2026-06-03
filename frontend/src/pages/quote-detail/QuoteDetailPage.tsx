/**
 * 見積もり詳細ページ。
 * 見積ヘッダー + 明細表示、ステータスアクション（送付/承認/却下/請求書変換）。
 *
 * 変更履歴:
 *   2026-04-17: 初版作成（Phase 2）
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";

interface QuoteItem {
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

interface QuoteDetail {
  id: number;
  quote_code: string | null;
  deal_id: number | null;
  // Step 5d: 旧 customer_id を撤去、company_id を必須化
  company_id: number;
  currency: string;
  subtotal: number | null;
  shipping_fee: number | null;
  tax_amount: number | null;
  total_amount: number | null;
  status: string;
  validity_date: string | null;
  notes: string | null;
  created_at: string;
  items: QuoteItem[];
}

export default function QuoteDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [quote, setQuote] = useState<QuoteDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await api.get<QuoteDetail>(`/quotes/${id}`);
      setQuote(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const doAction = async (action: string) => {
    try {
      await api.post(`/quotes/${id}/${action}`, {});
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };

  const convertToInvoice = async () => {
    try {
      const result = await api.post<{ id: number }>(`/invoices/from-quote/${id}`, {});
      navigate(`/invoices/${result.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };

  const fmt = (n: number | null) => {
    if (n == null) return "-";
    return n.toLocaleString();
  };

  if (loading) return <div className="page"><div className="loading">{t("common.loading")}</div></div>;
  if (!quote) return <div className="page"><div className="error-message">{error || t("common.fetchError")}</div></div>;

  // 総重量 = Σ(数量 × 行重量)。
  const quoteTotalWeight = quote.items.reduce((s, it) => s + it.quantity * (it.weight ?? 0), 0);

  return (
    <div className="page">
      <div className="page-header">
        {/* eslint-disable-next-line no-restricted-syntax */}
        <h2>{t("quotes.title")} — {quote.quote_code || `#${quote.id}`}</h2>
        <div className="actions" style={{ display: "flex", gap: "var(--space-2)" }}>
          {quote.status === "draft" && hasPermission("quotes.update") && (
            <button className="btn-primary" onClick={() => doAction("send")}>{t("quotes.send")}</button>
          )}
          {quote.status === "sent" && hasPermission("quotes.approve") && (
            <>
              <button className="btn-primary" onClick={() => doAction("approve")}>{t("quotes.approve")}</button>
              <button className="btn-danger" onClick={() => doAction("reject")}>{t("quotes.reject")}</button>
            </>
          )}
          {quote.status === "approved" && hasPermission("invoices.create") && (
            <button className="btn-primary" onClick={convertToInvoice}>{t("quotes.convertToInvoice")}</button>
          )}
          <button className="btn-secondary" onClick={() => navigate("/quotes")}>{t("common.back")}</button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div style={{ background: "var(--bg-surface)", padding: "var(--space-6)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)", marginBottom: "var(--space-6)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-4)" }}>
          <div><strong>{t("common.status")}:</strong> <span className={`badge badge-${quote.status === "approved" ? "won" : quote.status === "rejected" ? "lost" : "pending"}`}>{t(`quotes.status_${quote.status}`)}</span></div>
          <div><strong>{t("common.currency")}:</strong> {quote.currency}</div>
          <div><strong>{t("quotes.validityDate")}:</strong> {quote.validity_date || "-"}</div>
          <div><strong>{t("common.createdAt")}:</strong> {new Date(quote.created_at).toLocaleDateString()}</div>
          <div><strong>{t("common.notes")}:</strong> {quote.notes || "-"}</div>
        </div>
      </div>

      <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
      <table className="data-table" style={{ marginBottom: "var(--space-6)" }}>
        <thead>
          <tr>
            <th>{t("quotes.titleColumn")}</th>
            <th>{t("quotes.condition")}</th>
            <th>{t("quotes.unit")}</th>
            <th>{t("quotes.quantity")}</th>
            <th>{t("quotes.unitPrice")}</th>
            <th>{t("quotes.weight")}</th>
            <th>{t("quotes.subtotal")}</th>
          </tr>
        </thead>
        <tbody>
          {quote.items.map((item) => (
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
          <tr><td colSpan={6} style={{ textAlign: "right", fontWeight: "var(--font-weight-semi)" }}>{t("quotes.subtotal")}</td><td style={{ fontWeight: "var(--font-weight-semi)" }}>{fmt(quote.subtotal)}</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right" }}>{t("quotes.totalWeight")}</td><td>{quoteTotalWeight.toLocaleString()} kg</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right" }}>{t("quotes.shippingFee")}</td><td>{fmt(quote.shipping_fee)}</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right" }}>{t("quotes.tax")}</td><td>{fmt(quote.tax_amount)}</td></tr>
          <tr><td colSpan={6} style={{ textAlign: "right", fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>{t("quotes.total")}</td><td style={{ fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>{fmt(quote.total_amount)} {quote.currency}</td></tr>
        </tfoot>
      </table>
    </div>
  );
}
