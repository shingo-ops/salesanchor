/**
 * /own-inventory — 自社在庫 (A在庫) 管理ページ（ADR SA-04/05）。
 *
 * テナント専用スキーマ（own_inventory）のCRUD + 2段階引当（引当/解除/発送確定）。
 * B在庫（public.inventory の仕入元オファー）とは完全分離。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import ConfirmModal from "../../components/ConfirmModal";

interface OwnInventoryRow {
  id: number;
  tenant_id: number;
  product_id: number;
  physical_qty: number;
  reserved_qty: number;
  available_qty: number | null;
  unit_price: number | null;
  condition: string | null;
  status: string;
  note_ja: string | null;
  note_en: string | null;
  antique_ledger_id: number | null;
  created_at: string;
  updated_at: string;
}

type ActionKind = "reserve" | "release" | "ship";

interface PendingAction {
  row: OwnInventoryRow;
  kind: ActionKind;
  qty: number;
}

const PER_PAGE = 20;

export default function OwnInventoryPage() {
  const { t } = useTranslation();

  const [items, setItems] = useState<OwnInventoryRow[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [qtyInput, setQtyInput] = useState("1");
  const [actionError, setActionError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<OwnInventoryRow[]>(
        `/own-inventory?page=${page}&per_page=${PER_PAGE}`,
      );
      setItems(res);
    } catch {
      setError(t("ownInventory.loadError"));
    } finally {
      setLoading(false);
    }
  }, [page, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const openAction = (row: OwnInventoryRow, kind: ActionKind) => {
    setQtyInput("1");
    setActionError("");
    setPendingAction({ row, kind, qty: 1 });
  };

  const confirmAction = async () => {
    if (!pendingAction) return;
    const qty = parseInt(qtyInput, 10);
    if (!Number.isFinite(qty) || qty < 1) {
      setActionError(t("ownInventory.invalidQty"));
      return;
    }
    try {
      await api.post(
        `/own-inventory/${pendingAction.row.id}/${pendingAction.kind}`,
        { qty },
      );
      setPendingAction(null);
      void load();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("ownInventory.actionError");
      setActionError(detail);
    }
  };

  const availableQty = (row: OwnInventoryRow): number =>
    row.available_qty ?? row.physical_qty - row.reserved_qty;

  const actionLabel = (kind: ActionKind): string => {
    if (kind === "reserve") return t("ownInventory.reserve");
    if (kind === "release") return t("ownInventory.release");
    return t("ownInventory.ship");
  };

  return (
    <PageLayout navKey="nav.ownInventory" subtitleKey="ownInventory.subtitle">
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <p className="loading-text">{t("common.loading")}</p>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("ownInventory.col.productId")}</th>
                  <th>{t("ownInventory.col.condition")}</th>
                  <th>{t("ownInventory.physicalQty")}</th>
                  <th>{t("ownInventory.reservedQty")}</th>
                  <th>{t("ownInventory.availableQty")}</th>
                  <th>{t("ownInventory.col.unitPrice")}</th>
                  <th>{t("ownInventory.col.status")}</th>
                  <th>{t("ownInventory.col.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="empty-cell">
                      {t("ownInventory.noResults")}
                    </td>
                  </tr>
                ) : (
                  items.map((row) => (
                    <tr key={row.id}>
                      <td>{row.product_id}</td>
                      <td>{row.condition ?? "-"}</td>
                      <td className="qty-cell">{row.physical_qty}</td>
                      <td className="qty-cell">{row.reserved_qty}</td>
                      <td className="qty-cell qty-available">
                        {availableQty(row)}
                      </td>
                      <td>
                        {row.unit_price != null
                          ? row.unit_price.toLocaleString()
                          : "-"}
                      </td>
                      <td>
                        <span className={`status-badge status-${row.status}`}>
                          {t(`ownInventory.status.${row.status}`, {
                            defaultValue: row.status,
                          })}
                        </span>
                      </td>
                      <td className="actions-cell">
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          onClick={() => openAction(row, "reserve")}
                          aria-label={t("ownInventory.reserve")}
                        >
                          {t("ownInventory.reserve")}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-secondary"
                          onClick={() => openAction(row, "release")}
                          aria-label={t("ownInventory.release")}
                        >
                          {t("ownInventory.release")}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => openAction(row, "ship")}
                          aria-label={t("ownInventory.ship")}
                        >
                          {t("ownInventory.ship")}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* ページング */}
          <div className="pagination">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              aria-label={t("common.prevPage")}
            >
              {"<"}
            </button>
            <span>{t("common.page", { page })}</span>
            <button
              type="button"
              disabled={items.length < PER_PAGE}
              onClick={() => setPage((p) => p + 1)}
              aria-label={t("common.nextPage")}
            >
              {">"}
            </button>
          </div>
        </>
      )}

      {/* 引当・解除・発送確定 確認モーダル */}
      {pendingAction && (
        <ConfirmModal
          open
          title={actionLabel(pendingAction.kind)}
          message={
            <div>
              <p>
                {t("ownInventory.confirmMessage", {
                  action: actionLabel(pendingAction.kind),
                  productId: pendingAction.row.product_id,
                })}
              </p>
              <label>
                {t("ownInventory.qty")}
                <input
                  type="number"
                  min={1}
                  value={qtyInput}
                  onChange={(e) => {
                    setQtyInput(e.target.value);
                    setActionError("");
                  }}
                  className="qty-input"
                  aria-label={t("ownInventory.qty")}
                />
              </label>
              {actionError && (
                <p className="modal-error" role="alert">
                  {actionError}
                </p>
              )}
            </div>
          }
          confirmLabel={actionLabel(pendingAction.kind)}
          danger={pendingAction.kind === "ship"}
          onConfirm={() => void confirmAction()}
          onCancel={() => setPendingAction(null)}
        />
      )}
    </PageLayout>
  );
}
