import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { buildInventoryColumns } from "./inventoryColumns";
import type { InventoryRow } from "./inventoryColumns";

const t = ((k: string) => k) as never;
const row: InventoryRow = {
  id: "r1", product_id: 2, product_name: "Card", name_en: "En", category: "x", mark: null,
  condition: "sealed", unit: null, offer_type: "in_stock", status: "in_stock", note_ja: null, ship_ja: null,
  merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: "S",
  unit_price: 10, quantity: 1, work_code: null, offered_at: "", release_date: null, extraction_item_ids: [],
};

afterEach(() => cleanup());

describe("buildInventoryColumns", () => {
  it("has the designed column order and no category column", () => {
    const cols = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
    expect(cols.map((c) => c.key)).toEqual([
      "offer_type", "mark", "name", "condition", "unit_price", "quantity", "note", "ship", "supplier", "release_date",
    ]);
    expect(cols.map((c) => c.key)).not.toContain("category");
    expect(cols.find((c) => c.key === "offer_type")?.stickyLeft).toBe(true);
    expect(cols.find((c) => c.key === "name")?.stickyLeft).toBeFalsy();
    expect(cols.find((c) => c.key === "quantity")?.align).toBe("right");
    expect(cols.find((c) => c.key === "unit_price")?.align).toBe("right");
    expect(cols.filter((c) => c.sortable).map((c) => c.key)).not.toContain("note");
  });

  it("hides columns by hidden id but always keeps name and release_date", () => {
    const hidden = new Set(["mark", "unitPrice"]);
    const cols = buildInventoryColumns({ t, colVisible: (c) => !hidden.has(c), fmtOfferedAt: () => "-" });
    expect(cols.map((c) => c.key)).toEqual(["offer_type", "name", "condition", "quantity", "note", "ship", "supplier", "release_date"]);
  });

  it.each([
    ["Sealed box", "inventory-cell__condition--info"],
    ["Damaged sealed box", "inventory-cell__condition--warning"],
    ["No shrink box", "inventory-cell__condition--purple"],
    ["Opened box", "inventory-cell__condition--danger"],
    ["Case", "inventory-cell__condition--success"],
    ["New", "inventory-cell__condition--neutral"],
  ])("renders condition %s as colored text without Badge", (cond, cls) => {
    const cols = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
    const cell = cols.find((c) => c.key === "condition")!.renderCell!({ ...row, condition: cond }, "r1");
    render(<div data-testid="cell">{cell}</div>);
    expect(screen.getByTestId("cell").querySelector(`.${cls}`)?.textContent).toBe(cond);
    expect(screen.getByTestId("cell").querySelector(".comp-badge")).toBeNull();
  });
  it("has no unit column and keeps offer_type always visible", () => {
    const cols = buildInventoryColumns({ t, colVisible: () => false, fmtOfferedAt: () => "-" });
    expect(cols.map((c) => c.key)).not.toContain("unit");
    expect(cols.map((c) => c.key)).toContain("offer_type");
  });

  it("renders offer type as colored text (no badge): in stock blue, pre-order orange, other status plain", () => {
    const cols = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
    const render1 = (r: InventoryRow) => {
      cleanup();
      render(<div data-testid="cell">{cols.find((c) => c.key === "offer_type")!.renderCell!(r, "r1")}</div>);
      return screen.getByTestId("cell");
    };
    const inStock = render1({ ...row, offer_type: "in_stock" });
    expect(inStock.querySelector(".inventory-cell__offer--instock")?.textContent).toBe("inventory.offerType.in_stock");
    expect(inStock.querySelector(".comp-badge")).toBeNull();
    const pre = render1({ ...row, offer_type: "pre_order", status: "pre_order", ship_timing: "on_release" });
    expect(pre.querySelector(".inventory-cell__offer--preorder")?.textContent).toBe("inventory.offerType.pre_order");
    expect(pre.querySelector(".comp-badge")).toBeNull();
    expect(pre.querySelector(".inventory-cell__sub")?.textContent).toBe("inventory.shipTiming.on_release");
    const other = render1({ ...row, offer_type: null, status: "sold_out" });
    expect(other.textContent).toBe("sold_out");
    expect(other.querySelector(".inventory-cell__offer--instock, .inventory-cell__offer--preorder")).toBeNull();
  });
});

describe("block frames (ADR-1014 rev 2026-10-19 (3))", () => {
  const cell = (key: string, r: InventoryRow) => {
    const cols = buildInventoryColumns({ t, colVisible: () => true, fmtOfferedAt: () => "-" });
    render(<div data-testid="cell">{cols.find((c) => c.key === key)!.renderCell!(r, "r1")}</div>);
    return screen.getByTestId("cell");
  };
  it("frames the cheapest price in the price cell and the most-stock quantity in the quantity cell", () => {
    const price = cell("unit_price", { ...row, badge_cheapest: true });
    const p = price.querySelector('[data-testid="block-frame-cheapest"]');
    expect(p?.classList.contains("inventory-cell__value--cheapest")).toBe(true);
    expect(p?.getAttribute("title")).toBe("inventory.badge.cheapest");
    expect(price.querySelector('[data-testid="block-frame-most-stock"]')).toBeNull();
    cleanup();
    const qty = cell("quantity", { ...row, badge_most_stock: true });
    const q = qty.querySelector('[data-testid="block-frame-most-stock"]');
    expect(q?.classList.contains("inventory-cell__value--most-stock")).toBe(true);
    expect(q?.getAttribute("title")).toBe("inventory.badge.mostStock");
    expect(qty.querySelector('[data-testid="block-frame-cheapest"]')).toBeNull();
  });
  it.each([false, undefined])("keeps the value in the same container without a frame or title when the flag is %s", (flag) => {
    const price = cell("unit_price", { ...row, badge_cheapest: flag, badge_most_stock: flag });
    const p = price.querySelector(".inventory-cell__value");
    expect(p).not.toBeNull();
    expect(p?.classList.contains("inventory-cell__value--cheapest")).toBe(false);
    expect(p?.classList.contains("inventory-cell__value--most-stock")).toBe(false);
    expect(p?.hasAttribute("title")).toBe(false);
    cleanup();
    const qty = cell("quantity", { ...row, badge_cheapest: flag, badge_most_stock: flag });
    const q = qty.querySelector(".inventory-cell__value");
    expect(q).not.toBeNull();
    expect(q?.classList.contains("inventory-cell__value--cheapest")).toBe(false);
    expect(q?.classList.contains("inventory-cell__value--most-stock")).toBe(false);
    expect(q?.hasAttribute("title")).toBe(false);
  });
  it("shows no badge in the price and quantity cells", () => {
    const price = cell("unit_price", { ...row, badge_cheapest: true });
    expect(price.querySelector(".comp-badge")).toBeNull();
    cleanup();
    const qty = cell("quantity", { ...row, badge_most_stock: true });
    expect(qty.querySelector(".comp-badge")).toBeNull();
  });
});
