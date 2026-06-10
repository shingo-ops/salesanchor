/**
 * 見積もり一覧ページ。
 * ステータスフィルター + 見積一覧テーブル。新規作成はQuoteCreatePageに遷移。
 *
 * 変更履歴:
 *   2026-04-17: 初版作成（Phase 2）
 */

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { sortQuotes } from "./quotesSort";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn, SortDir } from "../../components/DataTable";

interface Quote {
  id: number;
  quote_code: string | null;
  deal_id: number | null;
  // Step 5d: 旧 customer_id を撤去、company_id を必須化
  company_id: number;
  contact_id: number | null;
  currency: string;
  subtotal: number | null;
  total_amount: number | null;
  status: string;
  validity_date: string | null;
  created_at: string;
  // 一覧表示用（backend が JOIN で付与）: 顧客名・担当者名・営業担当(起票者)名
  company_name: string | null;
  contact_name: string | null;
  created_by_name: string | null;
}

// 絞り込みに出すステータス（承認済 approved / 却下 rejected は除外）。
// 配色・ソートの純関数は ./quotesSort に分離（ユニットテスト対象）。
const FILTER_STATUSES = ["draft", "sent", "expired"];

export default function QuotesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const params = statusFilter ? `?status=${statusFilter}` : "";
      const data = await api.get<Quote[]>(`/quotes${params}`);
      setQuotes(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [statusFilter]);

  const fmt = (n: number | null, ccy: string) => {
    if (n == null) return "-";
    try { return n.toLocaleString("ja-JP", { style: "currency", currency: ccy }); }
    catch { return `${ccy} ${n.toLocaleString()}`; }
  };

  // 全列ソート: 同列クリックで asc⇔desc、別列は asc から。表示中の一覧を並べ替える。
  const handleSort = (field: string, dir: SortDir) => {
    setSortField(field);
    setSortDir(dir);
  };
  const sortedQuotes = useMemo(
    () => sortQuotes(quotes, sortField, sortDir),
    [quotes, sortField, sortDir],
  );

  return (
    <PageLayout
      navKey="nav.quotesInvoices"
      subtitleKey="quotes.subtitle"
      headerAction={hasPermission("quotes.create") ? (
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => navigate("/quotes/new")}>{t("quotes.newQuote")}</button>
        </div>
      ) : undefined}
    >
      <nav className="tab-nav">
        <button className="tab-active">{t("nav.quoteHistory")}</button>
        <button onClick={() => navigate("/invoices")}>{t("nav.invoices")}</button>
      </nav>

      {/* ステータス絞り込み: プルダウンを廃止し、表と同じバッジをボタン化。
          押すと該当ステータスのみ表示（再度押すと全件に戻す）。承認済/却下は対象外。 */}
      <div className="filter-bar" style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center" }}>
        <button
          type="button"
          className={statusFilter === "" ? "btn-primary btn-sm" : "btn-secondary btn-sm"}
          data-testid="quotes-filter-all"
          aria-pressed={statusFilter === ""}
          onClick={() => setStatusFilter("")}
        >
          {t("quotes.allStatuses")}
        </button>
        {FILTER_STATUSES.map((s) => {
          const active = statusFilter === s;
          return (
            <button
              key={s}
              type="button"
              data-testid={`quotes-filter-${s}`}
              aria-pressed={active}
              onClick={() => setStatusFilter(active ? "" : s)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 0,
                // 単一ステータス選択中は非選択を淡く表示して選択を強調
                opacity: statusFilter === "" || active ? 1 : 0.4,
                outline: active ? "2px solid var(--accent)" : "none",
                outlineOffset: "2px",
                borderRadius: "var(--radius-pill)",
              }}
            >
              <span className={`badge badge-${getStatusPresentation("quote", s).badgeVariant}`}>{t(`quotes.status_${s}`)}</span>
            </button>
          );
        })}
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (() => {
        const columns: DataTableColumn<Quote>[] = [
          { key: "quote_code", header: t("quotes.quoteCode"), sortable: true, renderCell: (q) => <span className="mono">{q.quote_code || "-"}</span> },
          { key: "customer", header: t("quotes.customer"), sortable: true, renderCell: (q) => (
            <>
              <div>{q.company_name || "-"}</div>
              {q.contact_name && (
                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{q.contact_name}</div>
              )}
            </>
          )},
          { key: "sales_rep", header: t("quotes.salesRep"), sortable: true, renderCell: (q) => q.created_by_name || "-" },
          { key: "currency", header: t("common.currency"), sortable: true },
          { key: "total", header: t("quotes.total"), sortable: true, renderCell: (q) => fmt(q.total_amount, q.currency) },
          { key: "status", header: t("common.status"), sortable: true, renderCell: (q) => (
            <span className={`badge badge-${getStatusPresentation("quote", q.status).badgeVariant}`}>
              {t(`quotes.status_${q.status}`) || q.status}
            </span>
          )},
          { key: "validity_date", header: t("quotes.validityDate"), sortable: true, renderCell: (q) => q.validity_date || "-" },
          { key: "created_at", header: t("common.createdAt"), sortable: true, renderCell: (q) => new Date(q.created_at).toLocaleDateString() },
          { key: "actions", header: t("common.actions"), renderCell: (q) => (
            <button className="btn-sm" onClick={() => navigate(`/quotes/${q.id}`)}>{t("common.detail")}</button>
          )},
        ];
        return (
          <DataTable<Quote>
            columns={columns}
            data={sortedQuotes}
            rowKey={(q) => String(q.id)}
            sortKey={sortField}
            sortDir={sortDir}
            onSort={handleSort}
            emptyState={t("quotes.noQuotes")}
          />
        );
      })()}
    </PageLayout>
  );
}
