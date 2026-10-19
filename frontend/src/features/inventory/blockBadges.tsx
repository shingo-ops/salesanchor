/** 価格・数量の値の入れ物。同じ商品・ステータス・状態のまとまりの最安は薄い水色の塗り、在庫最多は薄い緑の塗りで囲む（ADR-1014 改訂 2026-10-19（4））。在庫表と閲覧ページで同じ描画を使う。枠の有無で幅を変えない。 */
import type { ReactNode } from "react";
import "./inventoryColumns.css";

export function BlockValue({ frame, label, children }: { frame: "cheapest" | "mostStock" | null; label?: string; children: ReactNode }) {
  const cls = frame === "cheapest" ? " inventory-cell__value--cheapest" : frame === "mostStock" ? " inventory-cell__value--most-stock" : "";
  const testid = frame === "cheapest" ? "block-frame-cheapest" : frame === "mostStock" ? "block-frame-most-stock" : undefined;
  return (
    <span className={`inventory-cell__value${cls}`} data-testid={testid} title={frame ? label : undefined}>
      {children}
    </span>
  );
}
