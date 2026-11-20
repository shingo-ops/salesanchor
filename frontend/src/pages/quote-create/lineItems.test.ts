/* eslint-disable local/no-japanese-literal -- テスト: 試験の名前と試験の商品名を日本語で書く（ADR-027・precedent: DataTable.test.tsx） */
import { describe, expect, it } from "vitest";
import {
  INIT_ROWS,
  allRowsReady,
  applyProduct,
  applyQuantity,
  applyState,
  applyUnitPrice,
  categoryOf,
  changeCategory,
  clampQuantity,
  emptyRow,
  filledRows,
  handoffRows,
  padRows,
  reconvertPrices,
  rowStatus,
  statesFor,
  toInvoiceItem,
  totalWeight,
  unitFromState,
  yenToCurrency,
} from "./lineItems";
import type { DraftInventoryItem } from "./useDraftInventory";

const ITEM: DraftInventoryItem = {
  product_id: 7,
  name: "テスト商品",
  name_en: "Test Product",
  mark: "OP-01",
  work_code: "OP",
  box_weight_kg: 0.5,
  case_weight_kg: 6,
  cells: {
    "Sealed box": { price: 15000, quantity: 3 },
    Case: { price: 170000, quantity: 1 },
    "No shrink box": { price: 9000, quantity: 0 },
  },
};

describe("yenToCurrency", () => {
  it("円はそのまま", () => expect(yenToCurrency(15000, "JPY", null)).toBe(15000));
  it("為替で割って小数2けたで切り捨て", () => expect(yenToCurrency(1000, "USD", 151.37)).toBe(6.6));
  it("割り切れる値は誤差で下がらない", () => expect(yenToCurrency(15000, "USD", 150)).toBe(100));
  it("為替が無ければ 0", () => expect(yenToCurrency(15000, "USD", null)).toBe(0));
  it("値段が無ければ 0", () => expect(yenToCurrency(null, "USD", 150)).toBe(0));
});

describe("状態と重さ", () => {
  it("unit の決め方", () => {
    expect(unitFromState("Case")).toBe("case");
    expect(unitFromState("Sealed box")).toBe("box");
    expect(unitFromState("Booster pack")).toBe("pack");
    expect(unitFromState("Other")).toBeNull();
  });
  it("在庫 0 の状態を除き、在庫表の列の順で並べる", () => {
    expect(statesFor(ITEM)).toEqual(["Case", "Sealed box"]);
    expect(statesFor(undefined)).toEqual([]);
  });
  it("上限を超えたら上限に戻す", () => {
    expect(clampQuantity(5, 3)).toBe(3);
    expect(clampQuantity(2, 3)).toBe(2);
    expect(clampQuantity(9, null)).toBe(9);
  });
});

describe("行の操作", () => {
  it("初期は12行の空の行", () => {
    const rows = padRows([]);
    expect(rows).toHaveLength(INIT_ROWS);
    expect(rows.every((r) => rowStatus(r) === "empty")).toBe(true);
  });

  it("持ってきた商品は先頭の行から入る", () => {
    const rows = handoffRows({ selectedProducts: [{ product_id: 7, product_name: "テスト商品", unit_price: 15000 }] });
    expect(rows).toHaveLength(INIT_ROWS);
    expect(rows[0].product_id).toBe(7);
    expect(rows[0].quantity).toBe(1);
    expect(rows[0].unit_price).toBe(0);
    expect(categoryOf(rows[0], [ITEM])).toBe("OP");
    expect(rowStatus(rows[1])).toBe("empty");
  });

  it("カテゴリを選び直すと商品・状態・数量が空になる", () => {
    const row = applyState(applyProduct({ ...emptyRow(), category_code: "OP" }, ITEM), ITEM, "Sealed box", "JPY", null);
    const next = changeCategory(row, "PK");
    expect(next.product_id).toBeNull();
    expect(next.condition).toBeNull();
    expect(next.quantity).toBe(0);
    expect(next.category_code).toBe("PK");
    expect(changeCategory(row, "OP")).toBe(row);
  });

  it("状態を選ぶと重さ・単価・上限が入り、数量は1", () => {
    const row = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "USD", 150);
    expect(row.weight).toBe(0.5);
    expect(row.unit).toBe("box");
    expect(row.unit_price).toBe(100);
    expect(row.price_yen).toBe(15000);
    expect(row.stock_limit).toBe(3);
    expect(row.quantity).toBe(1);
    expect(rowStatus(row)).toBe("ready");
  });

  it("Case はケースの重さ", () => {
    expect(applyState(applyProduct(emptyRow(), ITEM), ITEM, "Case", "JPY", null).weight).toBe(6);
  });

  it("数量は在庫数に戻る", () => {
    const row = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "JPY", null);
    expect(applyQuantity(row, "9").quantity).toBe(3);
    expect(applyQuantity(row, "").quantity).toBe(0);
  });

  it("通貨を選び直すと、手で直していない行だけ入れ直す", () => {
    const auto = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "USD", 150);
    const edited = applyUnitPrice(auto, "80");
    const [a, e] = reconvertPrices([auto, edited], "USD", 100);
    expect(a.unit_price).toBe(150);
    expect(e.unit_price).toBe(80);
    expect(e.price_edited).toBe(true);
  });

  it("状態が無い行・重さが無い行は作れない", () => {
    const noState = applyProduct(emptyRow(), ITEM);
    expect(rowStatus(noState)).toBe("needsState");
    const noWeight = applyState(applyProduct(emptyRow(), { ...ITEM, box_weight_kg: null }), { ...ITEM, box_weight_kg: null }, "Sealed box", "JPY", null);
    expect(rowStatus(noWeight)).toBe("weightMissing");
    expect(allRowsReady([noState, emptyRow()])).toBe(false);
  });

  it("為替が無い通貨の行は単価 0 で作れない", () => {
    const row = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "EUR", null);
    expect(row.unit_price).toBe(0);
    expect(rowStatus(row)).toBe("invalid");
  });

  it("総重量と送る形", () => {
    const row = applyQuantity(applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "JPY", null), "2");
    const rows = [row, emptyRow()];
    expect(filledRows(rows)).toHaveLength(1);
    expect(totalWeight(rows)).toBe(1);
    expect(allRowsReady(rows)).toBe(true);
    expect(toInvoiceItem(row)).toEqual({
      product_id: 7,
      product_name: "テスト商品",
      name_en: "Test Product",
      condition: "Sealed box",
      unit: "box",
      quantity: 2,
      unit_price: 15000,
      weight: 0.5,
    });
  });
});
