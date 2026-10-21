/**
 * 閲覧ページの在庫表の列定義。
 * アプリの buildInventoryColumns（features/inventory/inventoryColumns.tsx）と同じ金型・同じ見え方にする。
 * ずれは viewerColumns.parity.test.tsx が縛る（並び順・sortable・align・stickyLeft・mobileOrder・mobileHidden）。
 * 列の並びは 在庫・予約（左端・固定）→ 型番 → タイトル → 状態 → 単価 → 数量 → 備考 → 発送 → 仕入元 → 発売日。
 * アプリの unit（形態）の列は閲覧の行に無いので持たない。
 */
import type { TFunction } from "i18next";
import type { DataTableColumn } from "../../components/DataTable";
import { HoverCard } from "../../components/HoverCard";
import { BlockValue } from "../../features/inventory/blockBadges";
import { conditionBadgeVariant } from "../../features/inventory/conditionBadge";
import "../../features/inventory/inventoryColumns.css";
import type { BlockFlags } from "./viewerFilter";
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

export function buildViewerColumns({ t }: { t: TFunction }): DataTableColumn<ViewerTableRow & Partial<BlockFlags>>[] {
  return [
    {
      key: "offer_type",
      header: t("viewer.col.offerType"),
      sortable: true,
      stickyLeft: true,
      mobileHidden: true,
      renderCell: (it) =>
        it.offer_type === null ? (
          <span className="inventory-cell__nowrap">{it.status || "-"}</span>
        ) : it.offer_type === "pre_order" ? (
          <span className="inventory-cell__nowrap inventory-cell__offer--preorder">{t("viewer.offerType.pre_order")}</span>
        ) : (
          <span className="inventory-cell__nowrap inventory-cell__offer--instock">{t("viewer.offerType.in_stock")}</span>
        ),
    },
    {
      key: "mark",
      header: t("viewer.col.mark"),
      sortable: true,
      mobileHidden: true,
      renderCell: (it) => <span className="inventory-cell__nowrap">{it.mark || "-"}</span>,
    },
    {
      key: "name",
      header: t("viewer.col.title"),
      sortable: true,
      mobileOrder: 1,
      renderCell: (it) => (
        <HoverCard title={it.japanese_title} subtitle={it.english_title}>
          <div className="inventory-cell__title inventory-cell__clip" data-hover-card-clip>
            {it.japanese_title}
          </div>
          {it.english_title && (
            <div className="inventory-cell__sub inventory-cell__clip" data-hover-card-clip>
              {it.english_title}
            </div>
          )}
        </HoverCard>
      ),
    },
    {
      key: "condition",
      header: t("viewer.col.condition"),
      sortable: true,
      mobileOrder: 2,
      renderCell: (it) => (
        <span className={`inventory-cell__nowrap inventory-cell__condition--${conditionBadgeVariant(it.condition)}`}>
          {it.condition}
        </span>
      ),
    },
    {
      key: "unit_price",
      header: t("viewer.col.unitPrice"),
      sortable: true,
      align: "right",
      mobileOrder: 3,
      renderCell: (it) => (
        <span className="inventory-cell__nowrap">
          <BlockValue frame={it.badge_cheapest ? "cheapest" : null} label={t("viewer.badge.cheapest")}>
            {formatPrice(it.unit_price)}
          </BlockValue>
        </span>
      ),
    },
    {
      key: "quantity",
      header: t("viewer.col.quantity"),
      sortable: true,
      align: "right",
      mobileOrder: 4,
      renderCell: (it) => (
        <span className="inventory-cell__nowrap">
          <BlockValue frame={it.badge_most_stock ? "mostStock" : null} label={t("viewer.badge.mostStock")}>
            {it.quantity}
          </BlockValue>
        </span>
      ),
    },
    {
      key: "note",
      header: t("viewer.col.note"),
      mobileOrder: 5,
      renderCell: (it) => <span className="inventory-cell__wrap">{it.note_ja}</span>,
    },
    {
      key: "ship",
      header: t("viewer.col.ship"),
      mobileOrder: 6,
      renderCell: (it) => <span className="inventory-cell__wrap">{it.ship_ja}</span>,
    },
    {
      key: "supplier",
      header: t("viewer.col.supplier"),
      sortable: true,
      mobileOrder: 7,
      renderCell: (it) => (
        <>
          <div className="inventory-cell__nowrap">{it.provider}</div>
          <div className="inventory-cell__sub">{formatPostedAt(it.posted_at)}</div>
        </>
      ),
    },
    {
      key: "release_date",
      header: t("viewer.col.releaseDate"),
      sortable: true,
      mobileHidden: true,
      renderCell: (it) => <span className="inventory-cell__nowrap">{it.release_date || "-"}</span>,
    },
  ];
}
