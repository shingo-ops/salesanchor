/**
 * 閲覧ページの在庫表の列定義。
 * アプリの buildInventoryColumns（features/inventory/inventoryColumns.tsx）と同じ金型・同じ見え方にする。
 * ずれは viewerColumns.parity.test.tsx が縛る（並び順・sortable・align・stickyLeft・mobileOrder・mobileHidden）。
 * アプリの unit（形態）の列は閲覧の行に無いので持たない。
 */
import type { TFunction } from "i18next";
import { Badge } from "../../components/Badge";
import type { DataTableColumn } from "../../components/DataTable";
import { conditionBadgeVariant } from "../../features/inventory/conditionBadge";
import "../../features/inventory/inventoryColumns.css";
import type { ViewerTableRow } from "./types";

/** 価格は '' でなければ ¥ と3桁区切り（アプリの `¥${unit_price.toLocaleString()}` と同じ形）。'' なら空。 */
export function formatPrice(unitPrice: string): string {
  if (unitPrice === "") return "";
  const n = Number(unitPrice);
  return Number.isFinite(n) ? `¥${n.toLocaleString()}` : "";
}

/** 投稿日時 'YYYY-MM-DD HH:MM:SS' → 'MM-DD HH:mm'（GAS と同じ） */
export function formatPostedAt(postedAt: string): string {
  return postedAt.length >= 16 ? postedAt.slice(5, 16) : "";
}

export function buildViewerColumns({ t }: { t: TFunction }): DataTableColumn<ViewerTableRow>[] {
  return [
    {
      key: "mark",
      header: t("viewer.col.mark"),
      sortable: true,
      mobileHidden: true,
      renderCell: (it) => it.mark || "-",
    },
    {
      key: "name",
      header: t("viewer.col.title"),
      sortable: true,
      stickyLeft: true,
      mobileOrder: 1,
      renderCell: (it) => (
        <>
          <div className="inventory-cell__title">{it.japanese_title}</div>
          {it.english_title && <div className="inventory-cell__sub">{it.english_title}</div>}
        </>
      ),
    },
    {
      key: "condition",
      header: t("viewer.col.condition"),
      sortable: true,
      mobileOrder: 2,
      renderCell: (it) => <Badge variant={conditionBadgeVariant(it.condition)}>{it.condition}</Badge>,
    },
    {
      key: "offer_type",
      header: t("viewer.col.offerType"),
      sortable: true,
      mobileHidden: true,
      renderCell: (it) =>
        it.offer_type === null ? (
          it.status || "-"
        ) : it.offer_type === "pre_order" ? (
          <Badge variant="info" appearance="soft">
            {t("viewer.offerType.pre_order")}
          </Badge>
        ) : (
          t("viewer.offerType.in_stock")
        ),
    },
    {
      key: "quantity",
      header: t("viewer.col.quantity"),
      sortable: true,
      align: "right",
      mobileOrder: 4,
      renderCell: (it) => it.quantity,
    },
    {
      key: "unit_price",
      header: t("viewer.col.unitPrice"),
      sortable: true,
      align: "right",
      mobileOrder: 3,
      renderCell: (it) => formatPrice(it.unit_price),
    },
    {
      key: "supplier",
      header: t("viewer.col.supplier"),
      sortable: true,
      mobileOrder: 7,
      renderCell: (it) => (
        <>
          <div>{it.provider}</div>
          <div className="inventory-cell__sub">{formatPostedAt(it.posted_at)}</div>
        </>
      ),
    },
    {
      key: "note",
      header: t("viewer.col.note"),
      mobileOrder: 5,
      renderCell: (it) => it.note_ja,
    },
    {
      key: "ship",
      header: t("viewer.col.ship"),
      mobileOrder: 6,
      renderCell: (it) => it.ship_ja,
    },
    {
      key: "release_date",
      header: t("viewer.col.releaseDate"),
      sortable: true,
      mobileHidden: true,
      renderCell: (it) => it.release_date || "-",
    },
  ];
}
