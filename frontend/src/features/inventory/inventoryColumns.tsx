/**
 * 在庫表（/inventory）の DataTable 列定義（ADR-093 / 便2 載せ替え）。
 * 列 key は API の sort 値（backend inventory_offers.py の sort）と一致させる。
 * 隠せる列は hidden_columns の id（colVisible に渡す）で絞る。
 */
import type { TFunction } from "i18next";
import type { DataTableColumn } from "../../components/DataTable";
import { Button } from "../../components/Button";
import { HoverCard } from "../../components/HoverCard";
import { PAGE_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { BlockValue } from "./blockBadges";
import { conditionBadgeVariant } from "./conditionBadge";
import { supplierLabel } from "./inventoryFormat";
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
  /** 同じ商品のまとまり（絞り込み後・ページ前）で最安／在庫最多か。無いときは付けない（ADR-1014 改訂） */
  badge_cheapest?: boolean;
  badge_most_stock?: boolean;
  /** 行の元になった extraction_items.id（まとめた行は組の全件）。解析パネル用 */
  extraction_item_ids: string[];
  posted_at: string | null;
  ship_timing: string | null;
  supplier_id: number;
  supplier_name: string | null;
  unit_price: number;
  quantity: number | null;
  work_code: string | null;
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
      hideId: null,
      col: {
        key: "offer_type",
        header: t("inventory.col.status"),
        sortable: true,
        stickyLeft: true,
        mobileHidden: true,
        renderCell: (it) => (
          <>
            {it.offer_type === null ? (
              <span className="inventory-cell__nowrap">{it.status ?? "-"}</span>
            ) : it.offer_type === "pre_order" ? (
              <span className="inventory-cell__nowrap inventory-cell__offer--preorder">
                {t("inventory.offerType.pre_order")}
              </span>
            ) : (
              <span className="inventory-cell__nowrap inventory-cell__offer--instock">
                {t("inventory.offerType.in_stock")}
              </span>
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
      hideId: "mark",
      col: {
        key: "mark",
        header: t("inventory.col.mark"),
        sortable: true,
        mobileHidden: true,
        renderCell: (it) => <span className="inventory-cell__nowrap">{it.mark ?? "-"}</span>,
      },
    },
    {
      hideId: null,
      col: {
        key: "name",
        header: t("inventory.col.title"),
        sortable: true,
        mobileOrder: 1,
        renderCell: (it) => (
          <HoverCard title={it.product_name ?? `#${it.product_id}`} subtitle={it.name_en}>
            <div className="inventory-cell__title inventory-cell__clip" data-hover-card-clip>
              {it.product_name ?? `#${it.product_id}`}
            </div>
            {it.name_en && (
              <div className="inventory-cell__sub inventory-cell__clip" data-hover-card-clip>
                {it.name_en}
              </div>
            )}
          </HoverCard>
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
        renderCell: (it) => (
          <span className={`inventory-cell__nowrap inventory-cell__condition--${conditionBadgeVariant(it.condition)}`}>
            {it.condition}
          </span>
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
        renderCell: (it) => (
          <span className="inventory-cell__nowrap">
            <BlockValue frame={it.badge_cheapest ? "cheapest" : null} label={t("inventory.badge.cheapest")}>
              {`¥${it.unit_price.toLocaleString()}`}
            </BlockValue>
          </span>
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
            <span className="inventory-cell__nowrap">
              <BlockValue frame={it.badge_most_stock ? "mostStock" : null} label={t("inventory.badge.mostStock")}>
                {it.quantity ?? ""}
              </BlockValue>
            </span>
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
      hideId: "note",
      col: {
        key: "note",
        header: t("inventory.col.note"),
        mobileOrder: 5,
        renderCell: (it) => <span className="inventory-cell__wrap">{it.note_ja ?? ""}</span>,
      },
    },
    {
      hideId: "ship",
      col: {
        key: "ship",
        header: t("inventory.col.ship"),
        mobileOrder: 6,
        renderCell: (it) => <span className="inventory-cell__wrap">{it.ship_ja ?? ""}</span>,
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
            <div className="inventory-cell__nowrap">{supplierLabel(it)}</div>
            <div className="inventory-cell__sub">{fmtOfferedAt(it.offered_at)}</div>
          </>
        ),
      },
    },
    {
      hideId: null,
      col: {
        key: "release_date",
        header: t("inventory.col.releaseDate"),
        sortable: true,
        mobileHidden: true,
        renderCell: (it) => <span className="inventory-cell__nowrap">{it.release_date ?? "-"}</span>,
      },
    },
  ];
  return all.filter((c) => c.hideId === null || colVisible(c.hideId)).map((c) => c.col);
}

/**
 * スマホのカード表示だけに足す「原文」ボタン列（便1）。
 * PC では使わない（呼び出し側 InventoryPage.tsx が isMobile のときだけこの列を足す）。
 * カードのラベル行を増やさないため header は空・mobileLabel も付けない。
 */
export function buildInventoryRawTextColumn({
  t,
  onOpen,
}: {
  t: TFunction;
  onOpen: (row: InventoryRow) => void;
}): DataTableColumn<InventoryRow> {
  return {
    key: "rawText",
    header: "",
    mobileOrder: 8,
    renderCell: (it) => (
      <Button
        variant="ghost"
        size="lg"
        iconOnly
        aria-label={t("inventory.rowDrawer.openButton")}
        data-testid={`inventory-raw-text-${it.id}`}
        onClick={() => onOpen(it)}
      >
        <PAGE_ICONS.rawText size={ICON.md} aria-hidden="true" />
      </Button>
    ),
  };
}
