import { describe, expect, it } from "vitest";
import { SORT_VALUE, sortQuotes, type SortableQuote } from "./quotesSort";
import { getStatusPresentation } from "../../utils/statusPresentation";

const mk = (over: Partial<SortableQuote>): SortableQuote => ({
  quote_code: null,
  company_name: null,
  contact_name: null,
  created_by_name: null,
  currency: "JPY",
  total_amount: null,
  status: "draft",
  validity_date: null,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

describe("getStatusPresentation — quote domain", () => {
  it("maps each status to the SSoT badge variant", () => {
    expect(getStatusPresentation("quote", "approved").badgeVariant).toBe("won");
    expect(getStatusPresentation("quote", "rejected").badgeVariant).toBe("lost");
    expect(getStatusPresentation("quote", "expired").badgeVariant).toBe("cancelled");
    expect(getStatusPresentation("quote", "sent").badgeVariant).toBe("negotiating");
    expect(getStatusPresentation("quote", "draft").badgeVariant).toBe("neutral");
    expect(getStatusPresentation("quote", "unknown").badgeVariant).toBe("neutral");
  });
});

describe("SORT_VALUE", () => {
  it("extracts comparable values, treating nulls safely", () => {
    const q = mk({ quote_code: "QUO-1", company_name: "Acme", contact_name: "Tanaka", total_amount: 1000 });
    expect(SORT_VALUE.quote_code(q)).toBe("QUO-1");
    expect(SORT_VALUE.customer(q)).toBe("AcmeTanaka");
    expect(SORT_VALUE.total(q)).toBe(1000);
    expect(SORT_VALUE.total(mk({ total_amount: null }))).toBe(Number.NEGATIVE_INFINITY);
    expect(SORT_VALUE.sales_rep(mk({ created_by_name: null }))).toBe("");
  });
});

describe("sortQuotes", () => {
  const a = mk({ quote_code: "A", total_amount: 300, created_at: "2026-01-03T00:00:00Z" });
  const b = mk({ quote_code: "B", total_amount: 100, created_at: "2026-01-01T00:00:00Z" });
  const c = mk({ quote_code: "C", total_amount: 200, created_at: "2026-01-02T00:00:00Z" });

  it("sorts numbers ascending and descending without mutating the input", () => {
    const input = [a, b, c];
    const asc = sortQuotes(input, "total", "asc");
    expect(asc.map((q) => q.total_amount)).toEqual([100, 200, 300]);
    const desc = sortQuotes(input, "total", "desc");
    expect(desc.map((q) => q.total_amount)).toEqual([300, 200, 100]);
    // 元配列は不変
    expect(input.map((q) => q.quote_code)).toEqual(["A", "B", "C"]);
  });

  it("sorts strings with locale compare", () => {
    const r = sortQuotes([a, c, b], "quote_code", "asc");
    expect(r.map((q) => q.quote_code)).toEqual(["A", "B", "C"]);
  });

  it("falls back to created_at for unknown fields", () => {
    const r = sortQuotes([a, b, c], "nope", "asc");
    expect(r.map((q) => q.created_at)).toEqual([
      "2026-01-01T00:00:00Z",
      "2026-01-02T00:00:00Z",
      "2026-01-03T00:00:00Z",
    ]);
  });
});
