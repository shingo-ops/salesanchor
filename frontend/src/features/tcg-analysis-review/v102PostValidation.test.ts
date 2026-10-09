import { describe, expect, it } from "vitest";
import { blockRangeOf, parseLines, toSaveItems, validateRows, type EditRow } from "./v102PostValidation";

const row = (patch: Partial<EditRow>): EditRow => ({
  key: "k1", id: "id-1", linesText: "1", price: "", quantity: "", reasonsText: "", ...patch,
});

describe("parseLines", () => {
  it.each([
    ["3,5,4", [3, 5, 4], null],
    [" 3 , 5 ", [3, 5], null],
    ["", [], "empty"],
    ["   ", [], "empty"],
    ["3.5", [], "notInteger"],
    ["a", [], "notInteger"],
    ["3,,5", [], "notInteger"],
    ["-1", [], "notInteger"],
    ["0", [0], "outOfRange"],
    ["9", [9], "outOfRange"],
    ["2,2", [2, 2], "duplicate"],
  ])("%j -> error %s", (text, lines, error) => {
    const result = parseLines(text, 5);
    expect(result.error).toBe(error);
    if (error === null || error === "outOfRange" || error === "duplicate") expect(result.lines).toEqual(lines);
  });
});

describe("validateRows", () => {
  it("is invalid when there are no rows", () => {
    const result = validateRows([], 5);
    expect(result.hasNoRows).toBe(true);
    expect(result.isValid).toBe(false);
  });

  it("flags only the bad rows and fields", () => {
    const rows = [row({ key: "a", linesText: "1,2" }), row({ key: "b", linesText: "9", price: "x".repeat(201) })];
    const result = validateRows(rows, 5);
    expect(result.isValid).toBe(false);
    expect(result.rowErrors.a).toEqual({ lines: null, price: false, quantity: false });
    expect(result.rowErrors.b).toEqual({ lines: "outOfRange", price: true, quantity: false });
  });

  it("accepts exactly 200 characters", () => {
    expect(validateRows([row({ price: "x".repeat(200), quantity: "y".repeat(200) })], 5).isValid).toBe(true);
  });
});

describe("toSaveItems", () => {
  it("sends blank price and quantity as null, sorts lines, and leaves id out for new items", () => {
    const items = toSaveItems([
      row({ id: "id-1", linesText: "3, 1", price: "  ", quantity: "2" }),
      row({ key: "n", id: null, linesText: "2", price: "100" }),
    ], 5);
    expect(items).toEqual([
      { id: "id-1", source_lines: [1, 3], raw_price: null, raw_quantity: "2" },
      { source_lines: [2], raw_price: "100", raw_quantity: null },
    ]);
    expect("id" in items[1]).toBe(false);
  });
});

describe("blockRangeOf", () => {
  it("covers the min to max line, and is null when the lines cannot be read", () => {
    expect(blockRangeOf(row({ linesText: "5,2" }), 5)).toEqual({ start: 2, end: 5 });
    expect(blockRangeOf(row({ linesText: "x" }), 5)).toBeNull();
    expect(blockRangeOf(row({ linesText: "9" }), 5)).toBeNull();
    expect(blockRangeOf(undefined, 5)).toBeNull();
  });
});
