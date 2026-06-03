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
const FILTER_STATUSES = ["draft", "sent", "expired"];

// テーブルのステータスバッジと同じ配色をフィルタボタンにも使う（見た目を揃える）。
const badgeVariant = (status: string): string =>
  status === "approved" ? "won"
    : status === "rejected" ? "lost"
      : status === "expired" ? "cancelled"
        : status === "sent" ? "negotiating"
          : "pending";

// 各列ソート用の値抽出（クライアントサイド）。
const SORT_VALUE: Record<string, (q: Quote) => string | number> = {
  quote_code: (q) => q.quote_code ?? "",
  customer: (q) => `${q.company_name ?? ""}${q.contact_name ?? ""}`,
  sales_rep: (q) => q.created_by_name ?? "",
  currency: (q) => q.currency ?? "",
  total: (q) => q.total_amount ?? Number.NEGATIVE_INFINITY,
  status: (q) => q.status ?? "",
  validity_date: (q) => q.validity_date ?? "",
  created_at: (q) => q.created_at ?? "",
};

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
  const onSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortField(field); setSortDir("asc"); }
  };
  const sortArrow = (field: string) =>
    sortField === field ? (sortDir === "asc" ? t("common.sortAsc") : t("common.sortDesc")) : t("common.sortNone");
  const sortedQuotes = useMemo(() => {
    const getv = SORT_VALUE[sortField] ?? SORT_VALUE.created_at;
    const dir = sortDir === "asc" ? 1 : -1;
    return [...quotes].sort((a, b) => {
      const av = getv(a);
      const bv = getv(b);
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv), "ja") * dir;
    });
  }, [quotes, sortField, sortDir]);

  // ソート可能な見出しセル（関数で返す＝nested-component を避ける）。
  const sortTh = (labelKey: string, field: string) => (
    <th>
      <button
        type="button"
        onClick={() => onSort(field)}
        data-testid={`quotes-sort-${field}`}
        style={{ background: "none", border: "none", cursor: "pointer", font: "inherit", fontWeight: "var(--font-weight-semi)", color: "inherit", display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}
      >
        {t(labelKey)}
        <span aria-hidden="true" style={{ fontSize: "var(--font-xs)", color: sortField === field ? "var(--accent)" : "var(--text-muted)" }}>
          {sortArrow(field)}
        </span>
      </button>
    </th>
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
              <span className={`badge badge-${badgeVariant(s)}`}>{t(`quotes.status_${s}`)}</span>
            </button>
          );
        })}
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              {sortTh("quotes.quoteCode", "quote_code")}
              {sortTh("quotes.customer", "customer")}
              {sortTh("quotes.salesRep", "sales_rep")}
              {sortTh("common.currency", "currency")}
              {sortTh("quotes.total", "total")}
              {sortTh("common.status", "status")}
              {sortTh("quotes.validityDate", "validity_date")}
              {sortTh("common.createdAt", "created_at")}
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {sortedQuotes.map((q) => (
              <tr key={q.id}>
                <td className="mono">{q.quote_code || "-"}</td>
                <td>
                  <div>{q.company_name || "-"}</div>
                  {q.contact_name && (
                    <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{q.contact_name}</div>
                  )}
                </td>
                <td>{q.created_by_name || "-"}</td>
                <td>{q.currency}</td>
                <td>{fmt(q.total_amount, q.currency)}</td>
                <td><span className={`badge badge-${badgeVariant(q.status)}`}>
                  {t(`quotes.status_${q.status}`) || q.status}
                </span></td>
                <td>{q.validity_date || "-"}</td>
                <td>{new Date(q.created_at).toLocaleDateString()}</td>
                <td className="actions">
                  <button className="btn-sm" onClick={() => navigate(`/quotes/${q.id}`)}>{t("common.detail")}</button>
                </td>
              </tr>
            ))}
            {sortedQuotes.length === 0 && <tr><td colSpan={9} className="empty">{t("quotes.noQuotes")}</td></tr>}
          </tbody>
        </table>
      )}
    </PageLayout>
  );
}
