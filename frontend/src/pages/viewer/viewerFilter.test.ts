import { describe, expect, it } from "vitest";
import vectors from "../../features/inventory/searchNormalize.vectors.json";
import { filterRows, matchesQuery, parsePostedAt, seriesTabs, sortRows, withIndex } from "./viewerFilter";
import type { ViewerFilters } from "./viewerFilter";
import type { ViewerRow } from "./types";

const mk = (o: Partial<ViewerRow>): ViewerRow => ({
  posted_at: "", mark: "", japanese_title: "", english_title: "", condition: "", unit_price: "", quantity: "",
  note_ja: "", status: "", release_date: "", series: "", provider: "", search_keywords: "", ship_ja: "", offer_type: null, ...o,
});
const noFilter: ViewerFilters = {
  tab: "all", query: "", freshOnly: false, freshWindowHours: 24, providers: [], conditions: [],
  priceMin: "", priceMax: "", qtyMin: "", qtyMax: "",
};

describe("search vectors (searchNormalize.vectors.json, all entries)", () => {
  it.each(vectors)("hits the row for %j", ({ input, expected }) => {
    const row = mk({ japanese_title: input });
    expect(matchesQuery(row, input)).toBe(true);
    expect(matchesQuery(row, expected)).toBe(true);
    expect(matchesQuery(mk({ english_title: expected }), input)).toBe(true);
  });
  it("does not hit an unrelated row", () => {
    expect(matchesQuery(mk({ japanese_title: "ピカチュウ" }), "リザードン")).toBe(false);
  });
  it("ANDs whitespace separated words across the four fields", () => {
    const row = mk({ japanese_title: "ピカチュウ", english_title: "Pikachu", mark: "SV1", search_keywords: "box" });
    expect(matchesQuery(row, "ぴかちゅう sv1 BOX")).toBe(true);
    expect(matchesQuery(row, "ぴかちゅう zzz")).toBe(false);
  });
});

describe("filters", () => {
  const rows = withIndex([
    mk({ series: "A", provider: "P1", condition: "sealed", unit_price: "100", quantity: "5", posted_at: "2026-10-16 10:00:00" }),
    mk({ series: "B", provider: "P2", condition: "damaged", unit_price: "300", quantity: "", posted_at: "2026-10-14 10:00:00" }),
    mk({ series: "", provider: "P1", condition: "sealed", unit_price: "", quantity: "1", posted_at: "" }),
  ]);
  const now = parsePostedAt("2026-10-16 12:00:00")!;
  it("tab / provider / condition", () => {
    expect(filterRows(rows, { ...noFilter, tab: "A" }, now).map((r) => r.idx)).toEqual([0]);
    expect(filterRows(rows, { ...noFilter, providers: ["P1"] }, now).map((r) => r.idx)).toEqual([0, 2]);
    expect(filterRows(rows, { ...noFilter, conditions: ["damaged"] }, now).map((r) => r.idx)).toEqual([1]);
  });
  it("price and quantity ranges drop rows with an empty value", () => {
    expect(filterRows(rows, { ...noFilter, priceMin: "100", priceMax: "200" }, now).map((r) => r.idx)).toEqual([0]);
    expect(filterRows(rows, { ...noFilter, qtyMin: "1" }, now).map((r) => r.idx)).toEqual([0, 2]);
  });
  it("24 hours: only rows posted within the window (JST naive time)", () => {
    expect(filterRows(rows, { ...noFilter, freshOnly: true }, now).map((r) => r.idx)).toEqual([0]);
    const later = parsePostedAt("2026-10-17 11:00:00")!; // 25 時間後
    expect(filterRows(rows, { ...noFilter, freshOnly: true }, later)).toEqual([]);
  });
  it("tabs are ordered by count then name; empty series only in all", () => {
    const rs = [mk({ series: "B" }), mk({ series: "A" }), mk({ series: "A" }), mk({ series: "" }), mk({ series: "C" })];
    expect(seriesTabs(rs)).toEqual([{ key: "A", count: 2 }, { key: "B", count: 1 }, { key: "C", count: 1 }]);
  });
});

describe("sort (design L365)", () => {
  const rows = withIndex([
    mk({ english_title: "item 2", release_date: "2026-01-01" }), // 0
    mk({ english_title: "item 10", release_date: "2026-03-01" }), // 1
    mk({ english_title: "", release_date: "2026-02-01", japanese_title: "あ" }), // 2
    mk({ english_title: "item 2", release_date: "" }), // 3
    mk({ english_title: "item 2", release_date: "2026-05-01" }), // 4
    mk({ english_title: "", release_date: "", japanese_title: "い" }), // 5
  ]);
  it("default: english_title asc ('' first), then release_date desc (empty last), then original order", () => {
    // 'item 10' < 'item 2'（numeric なし）。'' が先頭
    expect(sortRows(rows, "release_date", "desc").map((r) => r.idx)).toEqual([2, 5, 1, 4, 0, 3]);
  });
  it("pull-down price asc applies only inside the same english_title", () => {
    const rs = withIndex([
      mk({ english_title: "b", unit_price: "5" }),
      mk({ english_title: "a", unit_price: "9" }),
      mk({ english_title: "a", unit_price: "" }),
      mk({ english_title: "a", unit_price: "2" }),
    ]);
    expect(sortRows(rs, "unit_price", "asc").map((r) => r.idx)).toEqual([3, 1, 2, 0]);
  });
  it("name header desc: english_title desc and japanese_title desc, '' english last", () => {
    const out = sortRows(rows, "name", "desc");
    // english_title '' の行は末尾（降順）、'item 2' が 'item 10' より前
    expect(out.slice(-2).map((r) => r.english_title)).toEqual(["", ""]);
    expect(out.slice(-2).map((r) => r.japanese_title)).toEqual(["い", "あ"]);
    expect(out.map((r) => r.english_title).slice(0, 4)).toEqual(["item 2", "item 2", "item 2", "item 10"]);
  });
  it("'item 10' sorts before 'item 2' (no numeric collation)", () => {
    const out = sortRows(withIndex([mk({ english_title: "item 2" }), mk({ english_title: "item 10" })]), "release_date", "desc");
    expect(out.map((r) => r.english_title)).toEqual(["item 10", "item 2"]);
  });
});
