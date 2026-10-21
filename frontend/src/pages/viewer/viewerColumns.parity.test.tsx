import { describe, expect, it } from "vitest";
import { buildInventoryColumns } from "../../features/inventory/inventoryColumns";
import { buildViewerColumns } from "./viewerColumns";

const t = ((k: string) => k) as never;

// 閲覧の列は、アプリの在庫表の列（在庫・予約が左端の10列）と、並び順・並べ替え・寄せ・固定・スマホ表示が同じ
describe("viewer columns parity with the app inventory table", () => {
  const app = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
  const viewer = buildViewerColumns({ t });

  it("has the designed 10 columns in the same order (offer_type first)", () => {
    expect(app.map((c) => c.key)).toEqual([
      "offer_type", "mark", "name", "condition", "unit_price", "quantity", "note", "ship", "supplier", "release_date",
    ]);
    expect(viewer.map((c) => c.key)).toEqual(app.map((c) => c.key));
  });

  it.each(["sortable", "align", "stickyLeft", "mobileOrder", "mobileHidden"] as const)("has the same %s on every column", (prop) => {
    const pick = (cols: { key: string; sortable?: boolean; align?: string; stickyLeft?: boolean; mobileOrder?: number; mobileHidden?: boolean }[]) =>
      cols.map((c) => [c.key, c[prop] ?? null]);
    expect(pick(viewer)).toEqual(pick(app));
  });
});
