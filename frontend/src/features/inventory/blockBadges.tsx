/** 価格・数量の値の入れ物。同じ商品・ステータス・状態のまとまりの最安は水色の枠、在庫最多は緑の枠で囲む（ADR-1014 改訂 2026-10-19（3））。在庫表と閲覧ページで同じ描画を使う。枠の有無で幅を変えない。 */
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
