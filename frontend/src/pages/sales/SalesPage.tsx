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
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { Card } from "../../components/Card";

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
            <Card variant="metric" style={{ marginBottom: "var(--space-4)" }}>
              <h3 style={{ fontSize: "var(--font-sm)", fontWeight: "var(--font-weight-semi)", color: "var(--text-muted)", margin: "0 0 var(--space-3)" }}>{t("sales.summaryLegend")}</h3>
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
            </Card>
          )}

          {(() => {
            const baseColumns: DataTableColumn<SalesOrderItem>[] = [
              {
                key: "order_number",
                header: t("orders.orderNumber"),
                renderCell: (o) => <>{o.order_number}</>,
              },
              {
                key: "name",
                header: t("common.name"),
                renderCell: (o) => <>{o.contact_display_name ?? o.company_name ?? "-"}</>,
              },
              {
                key: "revenue_amount",
                header: t("sales.revenue"),
                renderCell: (o) => (
                  <span data-testid={`sales-revenue-${o.order_id}`}>
                    {o.revenue_amount !== null ? fmt(o.revenue_amount) : "-"}
                  </span>
                ),
              },
              {
                key: "cost_total",
                header: t("sales.cost"),
                renderCell: (o) => <>{o.cost_total !== null ? fmt(o.cost_total) : "-"}</>,
              },
              {
                key: "gross_profit",
                header: t("sales.grossProfit"),
                renderCell: (o) => (
                  <span data-testid={`sales-gross-${o.order_id}`}>
                    {o.gross_profit !== null ? fmt(o.gross_profit) : "-"}
                  </span>
                ),
              },
              {
                key: "gross_profit_rate",
                header: t("sales.grossProfitRate"),
                renderCell: (o) => (
                  <span data-testid={`sales-rate-${o.order_id}`}>
                    {fmtRate(o.gross_profit_rate)}
                  </span>
                ),
              },
              {
                key: "created_at",
                header: t("common.createdAt"),
                renderCell: (o) => <>{new Date(o.created_at).toLocaleDateString("ja-JP")}</>,
              },
            ];
            const actionsCol: DataTableColumn<SalesOrderItem> = {
              key: "actions",
              header: t("common.actions"),
              renderCell: (o) => (
                <button
                  type="button"
                  className="btn-sm"
                  data-testid={`sales-edit-${o.order_id}`}
                  onClick={() => setEditing(o)}
                >
                  {t("sales.editFinancial")}
                </button>
              ),
            };
            const columns = [...baseColumns, ...(canEdit ? [actionsCol] : [])];
            return (
              <DataTable<SalesOrderItem>
                columns={columns}
                data={data?.items ?? []}
                rowKey={(o) => String(o.order_id)}
                emptyState={<span>{t("sales.noData")}</span>}
              />
            );
          })()}
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
