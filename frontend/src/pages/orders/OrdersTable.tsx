/**
 * 受注管理 — データテーブル（区切り4 / ADR-021 改修）。
 *
 * 改修内容（区切り4 / 2026-06-04）:
 *   ③ ヘッダ整理: 「顧客情報/顧客」表記を「名前」に集約 + その右に「発送先」列、
 *      金額の前に「通貨」列を追加。
 *   ④ ステータスフロー: 各受注のフェーズ（支払い待ち/仕入れ中/発送待ち/完了/
 *      トラブル/キャンセル）を判定表示し、フェーズ別に操作ボタンを出し分ける。
 *   ⑤ 顧客名ハイパーリンク: 名前セルを会社詳細ページ（/crm/companies/:id）へリンク。
 *
 * 売上 / 粗利 / 粗利率 列は売上管理ページ（/sales）へ、報酬列は報酬管理ページ
 * （/commissions）へ分離したため本テーブルからは削除済み。
 *
 * fmt は useOrdersState からエクスポートされたユーティリティを使用。
 * 通貨フォーマット fmtCurrency も同モジュールからインポートする。
 */

import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { usePermissions } from "../../hooks/usePermissions";
import type { OrderListItem } from "./orders.types";
import type { ShippingDetailDto } from "../../components/ShippingDetailPanel";
import type { PurchaseDetailDto } from "../../components/PurchaseDetailPanel";
import { fmtCurrency, orderPhase } from "./useOrdersState";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";

interface PanelOpeners {
  setShippingTarget: (o: OrderListItem) => void;
  setPurchaseTarget: (o: OrderListItem) => void;
}

interface Props {
  orders: OrderListItem[];
  shippings: Record<number, ShippingDetailDto | null>;
  purchases: Record<number, PurchaseDetailDto | null>;
  panelOpeners: PanelOpeners;
  STATUS_LABELS: Record<string, string>;
  handleEdit: (o: OrderListItem) => void;
  setDeleteTarget: (o: OrderListItem) => void;
  setPaidOrder: (o: OrderListItem, paid: boolean) => void;
}

/** 発送先（都市 + 国コード）を簡易表示。両方無ければ "-"。 */
function shippingTo(o: OrderListItem): string {
  const parts = [o.shipping_city, o.shipping_country_code].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "-";
}

export function OrdersTable({
  orders, shippings, purchases,
  panelOpeners, STATUS_LABELS, handleEdit, setDeleteTarget, setPaidOrder,
}: Props) {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const { setShippingTarget, setPurchaseTarget } = panelOpeners;
  const canLinkCustomer = hasPermission("customers.view");

  const PHASE_LABELS: Record<string, string> = {
    awaiting_payment: t("orders.phaseAwaitingPayment"),
    sourcing: t("orders.phaseSourcing"),
    awaiting_shipping: t("orders.phaseAwaitingShipping"),
    completed: t("orders.phaseCompleted"),
    trouble: t("orders.phaseTrouble"),
    cancelled: t("orders.phaseCancelled"),
    unknown: t("orders.phaseUnknown"),
  };

  const columns: DataTableColumn<OrderListItem>[] = [
    {
      key: "order_number",
      header: t("orders.orderNumber"),
    },
    {
      key: "name",
      header: t("common.name"),
      renderCell: (o) => {
        const name = o.contact_display_name ?? o.company_name ?? `#${o.company_id}`;
        return canLinkCustomer ? (
          <NavLink to={`/crm/companies/${o.company_id}`}>{name}</NavLink>
        ) : (
          name
        );
      },
    },
    {
      key: "shippingTo",
      header: t("orders.shippingTo"),
      renderCell: (o) => <span data-testid={`ship-cell-to-${o.id}`}>{shippingTo(o)}</span>,
    },
    {
      key: "currency",
      header: t("common.currency"),
      renderCell: (o) => o.currency ?? "-",
    },
    {
      key: "total_amount",
      header: t("common.amount"),
      renderCell: (o) => o.total_amount !== null ? fmtCurrency(o.total_amount, o.currency) : "-",
    },
    {
      key: "phase",
      header: t("orders.flowColumn"),
      renderCell: (o) => {
        const ship = shippings[o.id] ?? null;
        const pur = purchases[o.id] ?? null;
        const phase = orderPhase(o, pur, ship);
        return (
          <span data-testid={`flow-cell-${o.id}`}>
            <span className={`badge badge-${getStatusPresentation("order", phase).badgeVariant}`}>{PHASE_LABELS[phase] ?? phase}</span>
          </span>
        );
      },
    },
    {
      key: "status",
      header: t("common.status"),
      renderCell: (o) => (
        <span className={`badge badge-${getStatusPresentation("order", o.status).badgeVariant}`}>
          {STATUS_LABELS[o.status] || o.status}
        </span>
      ),
    },
    {
      key: "created_at",
      header: t("common.createdAt"),
      renderCell: (o) => new Date(o.created_at).toLocaleDateString("ja-JP"),
    },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: (o) => {
        const ship = shippings[o.id] ?? null;
        const pur = purchases[o.id] ?? null;
        const phase = orderPhase(o, pur, ship);
        return (
          <span className="actions">
            <button className="btn-sm" onClick={() => handleEdit(o)}>{t("common.edit")}</button>

            {/* フェーズ別の主要操作 */}
            {phase === "awaiting_payment" && (
              <button
                className="btn-sm"
                onClick={() => setPaidOrder(o, true)}
                data-testid={`mark-paid-${o.id}`}
              >
                {t("orders.markPaid")}
              </button>
            )}
            {phase === "sourcing" && (
              <button
                className="btn-sm"
                onClick={() => setPurchaseTarget(o)}
                data-testid={`mark-purchased-${o.id}`}
              >
                {t("orders.markPurchased")}
              </button>
            )}
            {phase === "awaiting_shipping" && (
              <button
                className="btn-sm"
                onClick={() => setShippingTarget(o)}
                data-testid={`issue-label-${o.id}`}
              >
                {t("orders.issueLabel")}
              </button>
            )}
            {/* 支払済を取り消したい場合（支払い待ち以外で paid_at 有） */}
            {o.paid_at && phase !== "completed" && phase !== "cancelled" && phase !== "trouble" && (
              <button
                className="btn-sm"
                onClick={() => setPaidOrder(o, false)}
                data-testid={`mark-unpaid-${o.id}`}
              >
                {t("orders.markUnpaid")}
              </button>
            )}

            {/* 補助操作（発送 / 仕入 詳細パネル）は常時参照可 */}
            <button className="btn-sm" onClick={() => setShippingTarget(o)} data-testid={`open-shipping-${o.id}`}>
              {t("orders.shipping")}
            </button>
            <button className="btn-sm" onClick={() => setPurchaseTarget(o)} data-testid={`open-purchase-${o.id}`}>
              {t("orders.purchase")}
            </button>
            <button className="btn-sm btn-danger" onClick={() => setDeleteTarget(o)}>
              {t("common.delete")}
            </button>
          </span>
        );
      },
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={orders}
      rowKey={(o) => String(o.id)}
      emptyState={<span className="empty">{t("orders.noOrders")}</span>}
    />
  );
}
