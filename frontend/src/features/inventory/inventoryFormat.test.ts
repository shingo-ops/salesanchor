import { describe, expect, it } from "vitest";
import { fmtOfferedAt, supplierLabel } from "./inventoryFormat";

describe("inventoryFormat", () => {
  it("fmtOfferedAt returns '-' for an invalid date", () => {
    expect(fmtOfferedAt("")).toBe("-");
    expect(fmtOfferedAt("not-a-date")).toBe("-");
  });

  it("fmtOfferedAt formats as YYYY-MM-DD HH:mm in local time", () => {
    expect(fmtOfferedAt("2026-10-17T09:05:00")).toBe("2026-10-17 09:05");
  });

  it("supplierLabel uses the name, or #id when the name is null", () => {
    expect(supplierLabel({ supplier_name: "Shop A", supplier_id: 7 })).toBe("Shop A");
    expect(supplierLabel({ supplier_name: null, supplier_id: 7 })).toBe("#7");
  });
});
