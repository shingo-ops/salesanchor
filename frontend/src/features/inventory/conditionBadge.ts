/**
 * 在庫の「状態」文字列 → 状態の色の種類（文字色のクラス名にも使う）。
 * 値の集合は ADR-1023「What」4 の12値（正本は DB public.line_conditions）。
 * 割り当ては docs/handoff/inventory-condition-colors/design.md の表（PO 決定 2026-10-17）。
 * trim・小文字化したうえで完全一致（部分一致はしない）。
 *   info（青）   : sealed box / unsearched pack
 *   success（緑） : case
 *   warning（黄）: damaged sealed box / damaged case
 *   purple（薄紫）: no shrink box
 *   danger（薄赤）: opened box / opened case / searched box / searched pack / ar confirmed pack
 *   neutral（灰）: 上記以外（Bulk・空・null など）
 * 状態の値が ADR-1023 で増減したら、この表・design.md・conditionBadge.test.ts を同じ PR で直す。
 */
import type { BadgeVariant } from "../../components/Badge";

export function conditionBadgeVariant(condition: string | null | undefined): BadgeVariant {
  switch ((condition ?? "").trim().toLowerCase()) {
    case "sealed box":
    case "unsearched pack":
      return "info";
    case "case":
      return "success";
    case "damaged sealed box":
    case "damaged case":
      return "warning";
    case "no shrink box":
      return "purple";
    case "opened box":
    case "opened case":
    case "searched box":
    case "searched pack":
    case "ar confirmed pack":
      return "danger";
    default:
      return "neutral";
  }
}
