/**
 * 在庫の「状態」文字列 → Badge の variant（GAS 在庫一覧 H:1591-1605 と同じ規則）。
 * trim・小文字化したうえで完全一致。sealed→success / damaged→danger / case→info / 他→neutral。
 */
import type { BadgeVariant } from "../../components/Badge";

export function conditionBadgeVariant(condition: string | null | undefined): BadgeVariant {
  switch ((condition ?? "").trim().toLowerCase()) {
    case "sealed":
      return "success";
    case "damaged":
      return "danger";
    case "case":
      return "info";
    default:
      return "neutral";
  }
}
