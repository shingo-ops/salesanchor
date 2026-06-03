import { describe, expect, it } from "vitest";
import {
  buildInitialItems,
  lineFromSelected,
  weightForUnit,
  type LineItem,
  type QuoteDraft,
} from "./quoteDraft";

const draftOf = (items: LineItem[]): QuoteDraft => ({
  items,
  companyId: 1,
  contactId: 2,
  currency: "JPY",
  notes: "",
  shippingFee: "",
  taxAmount: "",
});

describe("lineFromSelected", () => {
  it("maps a selected product to a line item (qty 1, null price -> 0)", () => {
    expect(lineFromSelected({ product_id: 5, product_name: "X", unit_price: null, inventory_id: 9 }))
      .toEqual({
        product_id: 5,
        product_name: "X",
        name_en: null,
        condition: null,
        unit: null,
        quantity: 1,
        unit_price: 0,
        weight: null,
        box_weight_kg: null,
        case_weight_kg: null,
        inventory_id: 9,
      });
  });
});

describe("weightForUnit", () => {
  it("returns box_weight_kg when unit is box", () => {
    expect(weightForUnit("box", 1.25, 20.5, null)).toBe(1.25);
  });
  it("returns case_weight_kg when unit is case", () => {
    expect(weightForUnit("case", 1.25, 20.5, null)).toBe(20.5);
  });
  it("falls back when unit is neither box nor case", () => {
    expect(weightForUnit("pack", 1.25, 20.5, 0.3)).toBe(0.3);
  });
  it("falls back to null when no fallback given", () => {
    expect(weightForUnit("pack", 1.25, 20.5, null)).toBeNull();
    expect(weightForUnit(null, null, null, undefined)).toBeNull();
  });
  it("is case-insensitive on unit", () => {
    expect(weightForUnit("BOX", 1.25, 20.5, null)).toBe(1.25);
  });
  it("falls back when the matching weight column is null", () => {
    expect(weightForUnit("box", null, 20.5, 0.3)).toBe(0.3);
  });
});

describe("buildInitialItems", () => {
  it("returns a single blank row with no handoff", () => {
    const r = buildInitialItems(null);
    expect(r).toHaveLength(1);
    expect(r[0].product_name).toBe("");
  });

  it("maps fresh inventory selection into line items", () => {
    const r = buildInitialItems({
      selectedProducts: [
        { product_id: 1, product_name: "A", unit_price: 100, inventory_id: 11 },
        { product_id: 2, product_name: "B", unit_price: 200, inventory_id: 12 },
      ],
    });
    expect(r.map((i) => i.product_name)).toEqual(["A", "B"]);
    expect(r.map((i) => i.inventory_id)).toEqual([11, 12]);
  });

  it("round-trip merge: keeps free-text rows, preserves edits on re-selected inventory rows, drops unchecked", () => {
    const draft = draftOf([
      // 在庫由来（編集済み: qty 3, price 150）。再選択されるので編集が残るべき。
      { product_id: 1, product_name: "A", quantity: 3, unit_price: 150, weight: null, inventory_id: 11 },
      // 在庫由来だが今回 在庫表で外す（selectedProducts に含めない）→ 落ちるべき。
      { product_id: 2, product_name: "B", quantity: 1, unit_price: 200, weight: null, inventory_id: 12 },
      // 自由記入（inventory_id 無し・名前あり）→ 残すべき。
      { product_id: null, product_name: "ManualItem", quantity: 1, unit_price: 50, weight: null, inventory_id: null },
      // 空の自由記入 → 落とす。
      { product_id: null, product_name: "", quantity: 1, unit_price: 0, weight: null, inventory_id: null },
    ]);
    const r = buildInitialItems({
      draft,
      selectedProducts: [
        { product_id: 1, product_name: "A", unit_price: 999, inventory_id: 11 }, // 価格は draft 側(150)を優先
        { product_id: 9, product_name: "C", unit_price: 300, inventory_id: 13 }, // 新規追加
      ],
    });
    // 在庫行: 11(編集保持) + 13(新規)、自由記入: ManualItem。Bは外したので無し。空行も無し。
    expect(r.map((i) => i.inventory_id)).toEqual([11, 13, null]);
    expect(r.map((i) => i.product_name)).toEqual(["A", "C", "ManualItem"]);
    const a = r.find((i) => i.inventory_id === 11)!;
    expect(a.quantity).toBe(3); // 編集された数量が保持される
    expect(a.unit_price).toBe(150); // 編集された単価が保持される（selectedProducts の 999 で上書きしない）
  });

  it("round-trip with everything removed falls back to a blank row", () => {
    const draft = draftOf([
      { product_id: 1, product_name: "A", quantity: 1, unit_price: 100, weight: null, inventory_id: 11 },
    ]);
    const r = buildInitialItems({ draft, selectedProducts: [] });
    expect(r).toHaveLength(1);
    expect(r[0].product_name).toBe("");
  });
});
