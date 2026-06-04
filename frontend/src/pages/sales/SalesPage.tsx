/**
 * SalesPage — 売上管理ページ（区切り4 / ADR-021 改修）。
 *
 * 受注ごとの売上・原価・粗利・粗利率を一覧 + 全体集計で表示する。
 * 旧 OrdersTable から分離した「売上 / 粗利 / 粗利率」列の専用ビュー。
 *
 * データ取得:
 *   - GET /financials/orders — 受注 × order_financials の LEFT JOIN 集計
 *     （items[] + 全体集計）。権限は orders.view 流用（sales.view 未定義のため）。
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";
import OrderFinancialPanel from "../../components/OrderFinancialPanel";

interface SalesOrderItem {
  order_id: number;
  order_number: string;
  company_name: string | null;
  contact_display_name: string | null;
  currency: string | null;
  created_at: string;
  revenue_amount: number | null;
  cost_total: number | null;
  gross_profit: number | null;
  gross_profit_rate: number | null;
}

interface SalesListDto {
  items: SalesOrderItem[];
  count: number;
  revenue_total: number;
  cost_total: number;
  gross_profit_total: number;
  gross_profit_rate: number | null;
}

/** 金額を日本円フォーマットで表示 */
const fmt = (n: number) =>
  n.toLocaleString("ja-JP", { style: "currency", currency: "JPY" });

/** 粗利率を小数 1 桁 % 表示 */
const fmtRate = (n: number | null | undefined) => {
  if (n === null || n === undefined) return "-";
  return `${(n * 100).toFixed(1)}%`;
};

export default function SalesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const canEdit = hasPermission("orders.update");
  const [data, setData] = useState<SalesListDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // 売上編集モーダルの対象受注（null のとき非表示）。
  const [editing, setEditing] = useState<SalesOrderItem | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const dto = await api.get<SalesListDto>("/financials/orders");
      setData(dto);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <PageLayout navKey="nav.sales" subtitleKey="sales.subtitle">
      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <>
          {/* 集計サマリー */}
          {data && (
            <fieldset style={{ marginBottom: "var(--space-4)" }}>
              <legend>{t("sales.summaryLegend")}</legend>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-6)" }}>
                <span data-testid="sales-count">
                  {t("sales.count")}: <strong>{data.count}</strong>
                </span>
                <span data-testid="sales-revenue-total">
                  {t("sales.revenueTotal")}: <strong>{fmt(data.revenue_total)}</strong>
                </span>
                <span data-testid="sales-cost-total">
                  {t("sales.costTotal")}: <strong>{fmt(data.cost_total)}</strong>
                </span>
                <span data-testid="sales-gross-total">
                  {t("sales.grossProfitTotal")}: <strong>{fmt(data.gross_profit_total)}</strong>
                </span>
                <span data-testid="sales-rate-total">
                  {t("sales.grossProfitRate")}: <strong>{fmtRate(data.gross_profit_rate)}</strong>
                </span>
              </div>
            </fieldset>
          )}

          <table className="data-table">
            <thead>
              <tr>
                <th>{t("orders.orderNumber")}</th>
                <th>{t("common.name")}</th>
                <th>{t("sales.revenue")}</th>
                <th>{t("sales.cost")}</th>
                <th>{t("sales.grossProfit")}</th>
                <th>{t("sales.grossProfitRate")}</th>
                <th>{t("common.createdAt")}</th>
                {canEdit && <th>{t("common.actions")}</th>}
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((o) => (
                <tr key={o.order_id}>
                  <td>{o.order_number}</td>
                  <td>{o.contact_display_name ?? o.company_name ?? "-"}</td>
                  <td data-testid={`sales-revenue-${o.order_id}`}>
                    {o.revenue_amount !== null ? fmt(o.revenue_amount) : "-"}
                  </td>
                  <td>{o.cost_total !== null ? fmt(o.cost_total) : "-"}</td>
                  <td data-testid={`sales-gross-${o.order_id}`}>
                    {o.gross_profit !== null ? fmt(o.gross_profit) : "-"}
                  </td>
                  <td data-testid={`sales-rate-${o.order_id}`}>
                    {fmtRate(o.gross_profit_rate)}
                  </td>
                  <td>{new Date(o.created_at).toLocaleDateString("ja-JP")}</td>
                  {canEdit && (
                    <td>
                      <button
                        type="button"
                        className="btn-sm"
                        data-testid={`sales-edit-${o.order_id}`}
                        onClick={() => setEditing(o)}
                      >
                        {t("sales.editFinancial")}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
              {(!data || data.items.length === 0) && (
                <tr>
                  <td colSpan={canEdit ? 8 : 7} className="empty">{t("sales.noData")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}

      {editing && (
        <OrderFinancialPanel
          orderId={editing.order_id}
          orderNumber={editing.order_number}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void load();
          }}
        />
      )}
    </PageLayout>
  );
}
