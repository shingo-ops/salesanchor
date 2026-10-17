/**
 * 在庫表の「提供者」表示（仕入元名・掲載時間）の整形。
 * 在庫表の列と原文スライドの見出しで同じ文字にするため、ここを唯一の定義にする。
 */
import type { InventoryRow } from "./inventoryColumns";

// 掲載時間: YYYY-MM-DD HH:mm（○時○分まで表示）
export function fmtOfferedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** 仕入元名。名前が無ければ #仕入元ID */
export function supplierLabel(row: Pick<InventoryRow, "supplier_name" | "supplier_id">): string {
  return row.supplier_name ?? `#${row.supplier_id}`;
}
