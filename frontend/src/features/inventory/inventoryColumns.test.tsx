import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { buildInventoryColumns } from "./inventoryColumns";
import type { InventoryRow } from "./inventoryColumns";

const t = ((k: string) => k) as never;
const row: InventoryRow = {
  id: "r1", product_id: 2, product_name: "Card", name_en: "En", category: "x", mark: null,
  condition: "sealed", unit: null, offer_type: "in_stock", status: "in_stock", note_ja: null, ship_ja: null,
  merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: "S",
  unit_price: 10, quantity: 1, tcg_type: null, offered_at: "", release_date: null, extraction_item_ids: [],
};

afterEach(() => cleanup());

describe("buildInventoryColumns", () => {
  it("has the designed column order and no category column", () => {
    const cols = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
    expect(cols.map((c) => c.key)).toEqual([
      "mark", "name", "condition", "unit", "offer_type", "quantity", "unit_price", "supplier", "note", "ship", "release_date",
    ]);
    expect(cols.map((c) => c.key)).not.toContain("category");
    expect(cols.find((c) => c.key === "name")?.stickyLeft).toBe(true);
    expect(cols.find((c) => c.key === "quantity")?.align).toBe("right");
    expect(cols.find((c) => c.key === "unit_price")?.align).toBe("right");
    expect(cols.filter((c) => c.sortable).map((c) => c.key)).not.toContain("note");
  });

  it("hides columns by hidden id but always keeps name and release_date", () => {
    const hidden = new Set(["mark", "offerType", "unitPrice"]);
    const cols = buildInventoryColumns({ t, colVisible: (c) => !hidden.has(c), fmtOfferedAt: () => "-" });
    expect(cols.map((c) => c.key)).toEqual(["name", "condition", "unit", "quantity", "supplier", "note", "ship", "release_date"]);
  });

  it.each([
    ["sealed", "comp-badge--success"],
    ["damaged", "comp-badge--danger"],
    ["case", "comp-badge--info"],
    ["New", "comp-badge--neutral"],
  ])("renders condition %s as Badge", (cond, cls) => {
    const cols = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
    const cell = cols.find((c) => c.key === "condition")!.renderCell!({ ...row, condition: cond }, "r1");
    render(<div data-testid="cell">{cell}</div>);
    expect(screen.getByTestId("cell").querySelector(`.${cls}`)?.textContent).toBe(cond);
  });
  it("renders Pre-order as Badge (info, soft) without the legacy badge-negotiating class", () => {
    const cols = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
    const cell = cols.find((c) => c.key === "offer_type")!.renderCell!(
      { ...row, offer_type: "pre_order", status: "pre_order" },
      "r1",
    );
    render(<div data-testid="cell">{cell}</div>);
    const root = screen.getByTestId("cell");
    expect(root.querySelector(".comp-badge--info.comp-badge--soft")?.textContent).toBe("inventory.offerType.pre_order");
    expect(root.querySelector(".badge-negotiating")).toBeNull();
  });
});
