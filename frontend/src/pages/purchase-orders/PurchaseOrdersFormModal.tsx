/**
 * 発注新規作成モーダル (QA r6 PO-02 対応)。
 *
 * 機能:
 *  - 仕入先選択 (suppliers から GET)
 *  - 明細行: 商品検索 (InventorySearchBar) + 数量 + 単価
 *  - 明細の複数行追加 / 削除
 *  - 備考
 *  - 保存で POST /purchase-orders (draft 状態で作成)
 */
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import InventoryPicker, { PickedProduct } from "../../components/InventoryPicker";
import { Modal } from "../../components/Modal";

interface Supplier {
  id: number;
  name: string;
  is_active: boolean;
}

export interface POLineItem {
  product_id: number | null;
  product_name: string;
  quantity: number;
  unit_cost: number;
}

const emptyLine = (): POLineItem => ({ product_id: null, product_name: "", quantity: 1, unit_cost: 0 });

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  /** 在庫表からの前埋め: 仕入元 ID（ADR-093 Phase 2b）。 */
  initialSupplierId?: number | "";
  /** 在庫表からの前埋め: 明細行（ADR-093 Phase 2b）。 */
  initialItems?: POLineItem[];
  /** 在庫表から前埋めした場合は商品が確定済みのため、商品選択列・明細追加を出さない。 */
  pickerless?: boolean;
}

export default function PurchaseOrdersFormModal({ open, onClose, onCreated, initialSupplierId, initialItems, pickerless }: Props) {
  const { t } = useTranslation();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplierId, setSupplierId] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<POLineItem[]>([emptyLine()]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setError("");
    // 在庫表からの前埋めがあれば採用、無ければ空（新規発注ボタン経由）。
    setSupplierId(initialSupplierId ?? "");
    setNotes("");
    setItems(initialItems && initialItems.length > 0 ? initialItems : [emptyLine()]);
    // P1/P2: 在庫表と同じ中央カタログ(public.suppliers)を仕入元プルダウンの源にする。
    // 返る id は public.suppliers.id。発注作成時に backend が tenant.suppliers へ解決する。
    api.get<Supplier[]>("/suppliers/catalog").then((rows) =>
      setSuppliers(rows.filter((s) => s.is_active)),
    ).catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")));
  }, [open, t, initialSupplierId, initialItems]);

  if (!open) return null;

  const onPickProduct = (index: number, c: PickedProduct) => {
    setItems((prev) => {
      const next = [...prev];
      next[index] = {
        product_id: c.product_id,
        product_name: c.name,
        quantity: 1,
        unit_cost: c.unit_price ?? 0,
      };
      return next;
    });
  };

  const updateItem = (i: number, field: keyof POLineItem, value: unknown) => {
    setItems((prev) => {
      const next = [...prev];
      (next[i] as unknown as Record<string, unknown>)[field] = value;
      return next;
    });
  };

  const addItem = () => setItems((prev) => [...prev, emptyLine()]);
  const removeItem = (i: number) => {
    if (items.length <= 1) return;
    setItems((prev) => prev.filter((_, idx) => idx !== i));
  };

  const total = items.reduce((s, it) => s + it.quantity * it.unit_cost, 0);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!supplierId) {
      setError(t("purchaseOrders.supplierRequired"));
      return;
    }
    if (items.some((it) => it.product_id === null || it.quantity <= 0 || it.unit_cost < 0)) {
      setError(t("purchaseOrders.itemsRequired"));
      return;
    }
    setSaving(true);
    try {
      await api.post("/purchase-orders", {
        supplier_id: supplierId,
        notes: notes || null,
        items: items.map((it) => ({
          product_id: it.product_id,
          quantity: it.quantity,
          unit_cost: it.unit_cost,
        })),
      });
      onCreated();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setSaving(false);
    }
  };

  const footer = (
    <>
      <span style={{ marginRight: "auto" }}>
        {t("common.amount")}: <strong>¥{total.toLocaleString()}</strong>
      </span>
      <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>
        {t("common.cancel")}
      </button>
      <button form="po-form" type="submit" className="btn-primary" disabled={saving}>
        {saving ? t("common.saving") : t("common.save")}
      </button>
    </>
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("purchaseOrders.newPO")}
      size="xl"
      footer={footer}
    >
      {error && <div className="error-message">{error}</div>}
      <form id="po-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label>{t("purchaseOrders.supplier")} *</label>
          <select required value={supplierId} onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">{t("common.pleaseSelect")}</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>{t("quotes.items")} *</label>
          <table className="data-table">
            <thead>
              <tr>
                {!pickerless && <th style={{ minWidth: "var(--table-col-min-width)" }}>{t("quotes.selectProduct")}</th>}
                <th>{t("quotes.product")}</th>
                <th>{t("quotes.quantity")}</th>
                <th>{t("products.unitPrice")}</th>
                <th>{t("quotes.subtotal")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} data-testid={`po-item-row-${i}`}>
                  {!pickerless && (
                    <td style={{ minWidth: "var(--table-col-min-width)" }}>
                      <InventoryPicker
                        onSelect={(c) => onPickProduct(i, c)}
                        testIdPrefix={`po-inventory-search-${i}`}
                      />
                    </td>
                  )}
                  <td>
                    <input value={item.product_name} onChange={(e) => updateItem(i, "product_name", e.target.value)} readOnly style={{ minWidth: "var(--min-width-input-sm)" }} />
                  </td>
                  <td>
                    <input type="number" min="1" value={item.quantity} onChange={(e) => updateItem(i, "quantity", Number(e.target.value))} style={{ width: "var(--input-width-qty)" }} />
                  </td>
                  <td>
                    <input type="number" min="0" step="0.01" value={item.unit_cost} onChange={(e) => updateItem(i, "unit_cost", Number(e.target.value))} style={{ width: "var(--input-width-year)" }} />
                  </td>
                  <td style={{ fontWeight: "var(--font-weight-semi)", whiteSpace: "nowrap" }}>
                    ¥{(item.quantity * item.unit_cost).toLocaleString()}
                  </td>
                  <td>
                    {items.length > 1 && (
                      <button type="button" className="btn-sm btn-danger" onClick={() => removeItem(i)}>{t("quotes.removeItem")}</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!pickerless && (
            <button type="button" className="btn-secondary" onClick={addItem} style={{ marginTop: "var(--space-2)" }}>{t("quotes.addItem")}</button>
          )}
        </div>

        <div className="form-group">
          <label>{t("common.notes")}</label>
          <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </form>
    </Modal>
  );
}
