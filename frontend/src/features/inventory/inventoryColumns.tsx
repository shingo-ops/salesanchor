/**
 * 在庫表（/inventory）の DataTable 列定義（ADR-093 / 便2 載せ替え）。
 * 列 key は API の sort 値（backend inventory_offers.py の sort）と一致させる。
 * 隠せる列は hidden_columns の id（colVisible に渡す）で絞る。
 */
import type { TFunction } from "i18next";
import { Badge } from "../../components/Badge";
import type { DataTableColumn } from "../../components/DataTable";
import { conditionBadgeVariant } from "./conditionBadge";
import "./inventoryColumns.css";

export interface InventoryRow {
  id: string;
  product_id: number;
  product_name: string | null;
  name_en: string | null;
  category: string | null;
  mark: string | null;
  condition: string;
  unit: string | null;
  offer_type: string | null;
  status: string | null;
  note_ja: string | null;
  ship_ja: string | null;
  merged_count: number;
  /** 行の元になった extraction_items.id（まとめた行は組の全件）。解析パネル用 */
  extraction_item_ids: string[];
  posted_at: string | null;
  ship_timing: string | null;
  supplier_id: number;
  supplier_name: string | null;
  unit_price: number;
  quantity: number | null;
  tcg_type: string | null;
  offered_at: string;
  release_date: string | null;
}

interface BuildArgs {
  t: TFunction;
  /** hidden_columns の id が表示対象か */
  colVisible: (hiddenId: string) => boolean;
  /** 掲載時間の整形 */
  fmtOfferedAt: (iso: string) => string;
}

export function buildInventoryColumns({ t, colVisible, fmtOfferedAt }: BuildArgs): DataTableColumn<InventoryRow>[] {
  const all: { hideId: string | null; col: DataTableColumn<InventoryRow> }[] = [
    {
      hideId: "mark",
      col: {
        key: "mark",
        header: t("inventory.col.mark"),
        sortable: true,
        mobileHidden: true,
        renderCell: (it) => it.mark ?? "-",
      },
    },
    {
      hideId: null,
      col: {
        key: "name",
        header: t("inventory.col.title"),
        sortable: true,
        stickyLeft: true,
        mobileOrder: 1,
        renderCell: (it) => (
          <>
            <div className="inventory-cell__title">{it.product_name ?? `#${it.product_id}`}</div>
            {it.name_en && <div className="inventory-cell__sub">{it.name_en}</div>}
          </>
        ),
      },
    },
    {
      hideId: "condition",
      col: {
        key: "condition",
        header: t("inventory.col.condition"),
        sortable: true,
        mobileOrder: 2,
        renderCell: (it) => <Badge variant={conditionBadgeVariant(it.condition)}>{it.condition}</Badge>,
      },
    },
    {
      hideId: "unit",
      col: {
        key: "unit",
        header: t("inventory.col.unit"),
        sortable: true,
        mobileHidden: true,
        renderCell: (it) => it.unit ?? "-",
      },
    },
    {
      hideId: "offerType",
      col: {
        key: "offer_type",
        header: t("inventory.col.offerType"),
        sortable: true,
        mobileHidden: true,
        renderCell: (it) => (
          <>
            {it.offer_type === null ? (
              (it.status ?? "-")
            ) : it.offer_type === "pre_order" ? (
              <Badge variant="info" appearance="soft">{t("inventory.offerType.pre_order")}</Badge>
            ) : (
              t("inventory.offerType.in_stock")
            )}
            {it.offer_type === "pre_order" && it.ship_timing && (
              <div className="inventory-cell__sub">
                {t(`inventory.shipTiming.${it.ship_timing}`, { defaultValue: it.ship_timing })}
              </div>
            )}
          </>
        ),
      },
    },
    {
      hideId: "quantity",
      col: {
        key: "quantity",
        header: t("inventory.col.quantity"),
        sortable: true,
        align: "right",
        mobileOrder: 4,
        renderCell: (it) => (
          <>
            {it.quantity ?? ""}
            {it.merged_count >= 2 && (
              <div data-testid={`inventory-row-${it.id}-merged`} className="inventory-cell__sub">
                {t("inventory.mergedCount", { count: it.merged_count })}
              </div>
            )}
          </>
        ),
      },
    },
    {
      hideId: "unitPrice",
      col: {
        key: "unit_price",
        header: t("inventory.col.unitPrice"),
        sortable: true,
        align: "right",
        mobileOrder: 3,
        renderCell: (it) => `¥${it.unit_price.toLocaleString()}`,
      },
    },
    {
      hideId: "supplier",
      col: {
        key: "supplier",
        header: t("inventory.col.supplier"),
        sortable: true,
        mobileOrder: 7,
        renderCell: (it) => (
          <>
            <div>{it.supplier_name ?? `#${it.supplier_id}`}</div>
            <div className="inventory-cell__sub">{fmtOfferedAt(it.offered_at)}</div>
          </>
        ),
      },
    },
    {
      hideId: "note",
      col: {
        key: "note",
        header: t("inventory.col.note"),
        mobileOrder: 5,
        renderCell: (it) => it.note_ja ?? "",
      },
    },
    {
      hideId: "ship",
      col: {
        key: "ship",
        header: t("inventory.col.ship"),
        mobileOrder: 6,
        renderCell: (it) => it.ship_ja ?? "",
      },
    },
    {
      hideId: null,
      col: {
        key: "release_date",
        header: t("inventory.col.releaseDate"),
        sortable: true,
        mobileHidden: true,
        renderCell: (it) => it.release_date ?? "-",
      },
    },
  ];
  return all.filter((c) => c.hideId === null || colVisible(c.hideId)).map((c) => c.col);
}
