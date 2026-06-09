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

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>{t("orders.orderNumber")}</th>
          <th>{t("common.name")}</th>
          <th>{t("orders.shippingTo")}</th>
          <th>{t("common.currency")}</th>
          <th>{t("common.amount")}</th>
          <th>{t("orders.flowColumn")}</th>
          <th>{t("common.status")}</th>
          <th>{t("common.createdAt")}</th>
          <th>{t("common.actions")}</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((o) => {
          const ship = shippings[o.id] ?? null;
          const pur = purchases[o.id] ?? null;
          const phase = orderPhase(o, pur, ship);
          const name = o.contact_display_name ?? o.company_name ?? `#${o.company_id}`;
          return (
            <tr key={o.id}>
              <td>{o.order_number}</td>
              <td>
                {canLinkCustomer ? (
                  <NavLink to={`/crm/companies/${o.company_id}`}>{name}</NavLink>
                ) : (
                  name
                )}
              </td>
              <td data-testid={`ship-cell-to-${o.id}`}>{shippingTo(o)}</td>
              <td>{o.currency ?? "-"}</td>
              <td>{o.total_amount !== null ? fmtCurrency(o.total_amount, o.currency) : "-"}</td>
              <td data-testid={`flow-cell-${o.id}`}>
                <span className={`badge badge-${getStatusPresentation("order", phase).badgeVariant}`}>{PHASE_LABELS[phase] ?? phase}</span>
              </td>
              <td>
                <span className={`badge badge-${getStatusPresentation("order", o.status).badgeVariant}`}>
                  {STATUS_LABELS[o.status] || o.status}
                </span>
              </td>
              <td>{new Date(o.created_at).toLocaleDateString("ja-JP")}</td>
              <td className="actions">
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
              </td>
            </tr>
          );
        })}
        {orders.length === 0 && (
          <tr>
            <td colSpan={9} className="empty">{t("orders.noOrders")}</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
