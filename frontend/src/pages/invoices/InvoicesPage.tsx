/**
 * 請求書一覧ページ。
 *
 * 変更履歴:
 *   2026-04-17: 初版作成（Phase 2）
 *   2026-06-09: 独自テーブルを標準 DataTable へ置換（ADR-122 Phase E パイロット）
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { DataTable, DataTableColumn } from "../../components/DataTable";
import { PageLayout } from "../../components/PageLayout";
import { getStatusPresentation } from "../../utils/statusPresentation";

interface Invoice {
  id: number;
  invoice_number: string | null;
  // Step 5d: 旧 customer_id を撤去、company_id を必須化
  company_id: number;
  currency: string;
  total_amount: number | null;
  amount_jpy: number | null;
  status: string;
  issued_at: string | null;
  due_date: string | null;
  paid_at: string | null;
  created_at: string;
}

const INVOICE_STATUSES = ["draft", "sent", "paid", "overdue", "cancelled"];

const fmt = (n: number | null, ccy: string) => {
  if (n == null) return "-";
  try { return n.toLocaleString("ja-JP", { style: "currency", currency: ccy }); }
  catch { return `${ccy} ${n.toLocaleString()}`; }
};

export default function InvoicesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const params = statusFilter ? `?status=${statusFilter}` : "";
      const data = await api.get<Invoice[]>(`/invoices${params}`);
      setInvoices(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [statusFilter]);

  const columns: DataTableColumn<Invoice>[] = [
    {
      key: "invoice_number",
      header: t("invoices.invoiceCode"),
      renderCell: (inv) => <span className="mono">{inv.invoice_number || "-"}</span>,
    },
    {
      key: "currency",
      header: t("common.currency"),
    },
    {
      key: "total_amount",
      header: t("common.amount"),
      renderCell: (inv) => fmt(inv.total_amount, inv.currency),
    },
    {
      key: "amount_jpy",
      header: t("invoices.jpyEquiv"),
      renderCell: (inv) => inv.amount_jpy != null ? `¥${inv.amount_jpy.toLocaleString()}` : "-",
    },
    {
      key: "status",
      header: t("common.status"),
      renderCell: (inv) => (
        <span className={`badge badge-${getStatusPresentation("invoice", inv.status).badgeVariant}`}>
          {t(`invoices.status_${inv.status}`) || inv.status}
        </span>
      ),
    },
    {
      key: "issued_at",
      header: t("invoices.issuedAt"),
      renderCell: (inv) => inv.issued_at ? new Date(inv.issued_at).toLocaleDateString() : "-",
    },
    {
      key: "due_date",
      header: t("invoices.dueDate"),
      renderCell: (inv) => inv.due_date || "-",
    },
    {
      key: "paid_at",
      header: t("invoices.paidAt"),
      renderCell: (inv) => inv.paid_at ? new Date(inv.paid_at).toLocaleDateString() : "-",
    },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: (inv) => (
        <button className="btn-sm" onClick={() => navigate(`/invoices/${inv.id}`)}>
          {t("common.detail")}
        </button>
      ),
    },
  ];

  return (
    <PageLayout
      navKey="nav.quotesInvoices"
      subtitleKey="invoices.subtitle"
      headerAction={
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => navigate("/invoices/new")}>
            {t("invoices.createTitle")}
          </button>
        </div>
      }
    >
      <nav className="tab-nav">
        <button onClick={() => navigate("/quotes")}>{t("nav.quoteHistory")}</button>
        <button className="tab-active">{t("nav.invoices")}</button>
      </nav>

      <div className="filter-bar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">{t("invoices.allStatuses")}</option>
          {INVOICE_STATUSES.map((s) => <option key={s} value={s}>{t(`invoices.status_${s}`)}</option>)}
        </select>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <DataTable<Invoice>
          columns={columns}
          data={invoices}
          rowKey={(inv) => String(inv.id)}
          emptyState={<span className="empty">{t("invoices.noInvoices")}</span>}
        />
      )}
    </PageLayout>
  );
}
