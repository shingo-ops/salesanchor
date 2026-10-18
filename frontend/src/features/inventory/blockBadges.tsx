/**
 * 同じ商品のまとまりの中の「最安」「在庫最多」バッジ（ADR-1014 改訂 2026-10-19（2））。
 * 在庫表と閲覧ページで同じ描画を使う。金型 Badge を値の右隣に並べるだけで、新しい部品ではない。
 */
import { Badge } from "../../components/Badge";
import "./inventoryColumns.css";

// Badge は data-testid などの残りの props を受け取らない（Badge.tsx）。testid は包む span に付ける
export function BlockBadge({ kind, label }: { kind: "cheapest" | "mostStock"; label: string }) {
  return (
    <span className="inventory-cell__badge" data-testid={kind === "cheapest" ? "block-badge-cheapest" : "block-badge-most-stock"}>
      <Badge size="sm" variant={kind === "cheapest" ? "success" : "info"}>
        {label}
      </Badge>
    </span>
  );
}
