import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ItemComparison, buildComparisonRows, geminiCell, systemCell, type AnalysisReviewItem } from "./ItemComparison";

const t = (key: string) => i18n.t(key);

function makeItem(over: Partial<AnalysisReviewItem> = {}): AnalysisReviewItem {
  return {
    extraction_item_id: "item-1", source_message_id: "msg-1", provider: "Supplier A", raw_text: "",
    gemini: { name: "Box A", quantity: "2", price: "13000", unit: "box", state: "new", memo: "", span: "L12-15" },
    system: { unit: "BOX", unit_resolved: "YES", condition: "New", work_name: "Work A", product_id: "PM-00001", status: "on_sale", note: "" },
    review_issues: [],
    ...over,
  };
}

beforeEach(async () => { await i18n.changeLanguage("en"); });
afterEach(cleanup);

describe("buildComparisonRows", () => {
  it("returns 10 rows in the fixed order", () => {
    const rows = buildComparisonRows(makeItem(), t);
    expect(rows.map((r) => r.key)).toEqual(["name", "quantity", "price", "unit", "state", "memo", "sourcePosition", "work", "productId", "saleStatus"]);
  });

  it("puts the dash on the side that has no value", () => {
    const rows = Object.fromEntries(buildComparisonRows(makeItem(), t).map((r) => [r.key, r]));
    const na = t("tcgAnalysisReview.notApplicable");
    expect(na).toBe("—");
    for (const k of ["work", "productId", "saleStatus"]) expect(rows[k].gemini).toBe(na);
    expect(rows.sourcePosition.system).toBe(na);
    for (const k of ["sourcePosition", "work", "productId", "saleStatus"]) expect(rows[k].source).toBe(na);
    expect(rows.productId.system).toBe("PM-00001");
    expect(rows.sourcePosition.line).toBe(12);
  });

  it("uses unresolved for existing-but-empty values (distinct from the dash)", () => {
    const rows = Object.fromEntries(buildComparisonRows(makeItem({ gemini: {}, system: {} }), t).map((r) => [r.key, r]));
    expect(rows.name.gemini).toBe(t("tcgAnalysisReview.unresolved"));
    expect(rows.sourcePosition.gemini).toBe(t("tcgAnalysisReview.unresolved"));
    expect(rows.work.system).toBe(t("common.unresolved"));
    expect(rows.memo.source).toBe("—");
  });
});

describe("geminiCell / v102 dash", () => {
  const na = "—";
  const v102 = () => makeItem({ is_v102: true, gemini: { name: "", quantity: "20", price: "23000", unit: "", state: "", memo: "", span: "L11-12" } });
  it("A1: v102 row shows the dash for name/unit/state/memo", () => {
    const rows = Object.fromEntries(buildComparisonRows(v102(), t).map((r) => [r.key, r]));
    for (const k of ["name", "unit", "state", "memo"]) expect(rows[k].gemini).toBe(na);
    for (const k of ["name", "unit", "state", "memo"]) expect(geminiCell(v102(), k, t)).toBe(na);
  });
  it("A2: v102 row keeps line / quantity / price values", () => {
    const rows = Object.fromEntries(buildComparisonRows(v102(), t).map((r) => [r.key, r]));
    expect(rows.quantity.gemini).toBe("20");
    expect(rows.price.gemini).toBe("23000");
    expect(rows.sourcePosition.gemini).toBe("L11-12");
  });
  it("A3: v6 row is unchanged (value, or unresolved when empty)", () => {
    const rows = Object.fromEntries(buildComparisonRows(makeItem({ is_v102: false }), t).map((r) => [r.key, r]));
    expect(rows.name.gemini).toBe("Box A");
    const empty = Object.fromEntries(buildComparisonRows(makeItem({ is_v102: false, gemini: {} }), t).map((r) => [r.key, r]));
    expect(empty.name.gemini).toBe(t("tcgAnalysisReview.unresolved"));
  });
  it("A1 (edit side): v102 non-readOnly view also shows the dash", () => {
    const { container } = render(<ItemComparison item={v102()} onJumpToSourceLine={() => undefined} />);
    const first = container.querySelectorAll(".aligned-fields .comparison-field:not(.system-field):not(.manual-field) span");
    expect(Array.from(first).map((e) => e.textContent)).toEqual([na, "20", "23000", na, na, na]);
  });
});

describe("systemCell source (4 cases)", () => {
  it("name: product_title adopted as System confirmed (B1)", () => {
    const item = makeItem({ system: { ...makeItem().system, product_title: "Master Title" } });
    expect(systemCell(item, "name", t)).toEqual({ value: "Master Title", source: t("tcgAnalysisReview.systemConfirmed") });
  });
  it("name: empty product_title is unresolved even if gemini has a name (B2)", () => {
    expect(systemCell(makeItem(), "name", t)).toEqual({ value: t("tcgAnalysisReview.unresolved"), source: t("tcgAnalysisReview.unresolved") });
  });
  it("price: gemini value adopted when system has none", () => {
    expect(systemCell(makeItem(), "price", t)).toEqual({ value: "13000", source: t("tcgAnalysisReview.geminiExtracted") });
  });
  it("gemini value missing", () => {
    expect(systemCell(makeItem({ gemini: {} }), "price", t)).toEqual({ value: t("tcgAnalysisReview.unresolved"), source: t("tcgAnalysisReview.unresolved") });
  });
  it("unit confirmed only when unit_resolved is YES", () => {
    expect(systemCell(makeItem(), "unit", t).source).toBe(t("tcgAnalysisReview.systemConfirmed"));
    expect(systemCell(makeItem({ system: { unit: "BOX", unit_resolved: "NO" } }), "unit", t).source).toBe(t("tcgAnalysisReview.unresolved"));
  });
  it("quantity / price: the system value (ar) wins over gemini; empty falls back to gemini", () => {
    const withSystem = makeItem({ system: { quantity: "5", price: "1000" } });
    expect(systemCell(withSystem, "quantity", t)).toEqual({ value: "5", source: t("tcgAnalysisReview.systemConfirmed") });
    expect(systemCell(withSystem, "price", t)).toEqual({ value: "1000", source: t("tcgAnalysisReview.systemConfirmed") });
    expect(systemCell(makeItem({ system: { quantity: "", price: "" } }), "quantity", t)).toEqual({ value: "2", source: t("tcgAnalysisReview.geminiExtracted") });
  });
  it("memo: note present vs absent", () => {
    expect(systemCell(makeItem({ system: { note: "hello" } }), "memo", t)).toEqual({ value: "hello", source: t("tcgAnalysisReview.systemConfirmed") });
    expect(systemCell(makeItem(), "memo", t)).toEqual({ value: t("tcgAnalysisReview.none"), source: null });
  });
});

describe("ItemComparison readOnly", () => {
  const renderIt = (item: AnalysisReviewItem, jump = vi.fn()) => render(<ItemComparison item={item} readOnly={true} onJumpToSourceLine={jump} />);

  it("renders one table with 10 body rows in order", () => {
    renderIt(makeItem());
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(10);
    const labels = rows.map((r) => within(r).getAllByRole("cell")[0].textContent);
    expect(labels).toEqual(["Product name", "Quantity", "Unit price", "Unit", "Condition", "Memo", "Source position", "Series", "Product ID", "Sale Status"]);
    expect(rows[8].textContent).toContain("PM-00001");
  });

  it("shows no badge container when there are no badges, and the same badge list otherwise", () => {
    const { container, unmount } = renderIt(makeItem());
    expect(container.querySelector(".item-comparison__badges")).toBeNull();
    unmount();
    const r2 = renderIt(makeItem({ review_issues: ["CONDITION_REVIEW_REQUIRED", "EXCLUDED"] }));
    const badges = r2.container.querySelectorAll(".item-comparison__badges .tcg-status-badge");
    expect(Array.from(badges).map((b) => b.textContent)).toEqual([t("conditionReview.needsReview"), t("reviewIssues.excluded"), t("conditionReview.needsReview")]);
  });

  it("puts the unregistered badge on the product ID row", () => {
    const { container } = renderIt(makeItem({ review_issues: ["PRODUCT_MASTER_UNREGISTERED"] }));
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[8].querySelectorAll(".tcg-status-badge")).toHaveLength(1);
    expect(container.querySelectorAll(".item-comparison__badges .tcg-status-badge")).toHaveLength(1);
  });

  it("calls onJumpToSourceLine with the line number", () => {
    const jump = vi.fn();
    renderIt(makeItem(), jump);
    fireEvent.click(screen.getByRole("button", { name: "L12-15" }));
    expect(jump).toHaveBeenCalledWith(12);
  });

  it("sets title from text on every cell", () => {
    const { container } = renderIt(makeItem());
    const cells = container.querySelectorAll(".item-comparison__cell, .item-comparison__fixed");
    expect(cells).toHaveLength(40);
    cells.forEach((c) => expect(c.getAttribute("title")).toBe(c.textContent));
  });
});

const lastCell = (row: HTMLElement) => { const cells = within(row).getAllByRole("cell"); return cells[cells.length - 1]; };

describe("ItemComparison readOnly fix column", () => {
  const noop = () => undefined;
  const manual = makeItem({ system: { ...makeItem().system, pid_basis: "MANUAL", product_title: "Title A", work_name: "Work A" } });

  it("keeps the Source column when no fixColumn is given (supplier detail)", () => {
    render(<ItemComparison item={makeItem()} readOnly={true} onJumpToSourceLine={noop} />);

    expect(screen.getByRole("columnheader", { name: "Source" })).toBeTruthy();
    expect(screen.queryByRole("columnheader", { name: "Fix" })).toBeNull();
  });

  it("replaces it with Fix, showing the manual value, the tap hint and the dash", () => {
    render(<ItemComparison item={manual} readOnly={true} onJumpToSourceLine={noop} fixColumn={{ selectedRowKey: null, onRowSelect: noop, fixableRowKeys: ["productId", "work"] }} />);

    expect(screen.queryByRole("columnheader", { name: "Source" })).toBeNull();
    expect(screen.getByRole("columnheader", { name: "Fix" })).toBeTruthy();
    expect(lastCell(screen.getByRole("row", { name: /^Product ID/ })).textContent).toBe("Title A");
    expect(lastCell(screen.getByRole("row", { name: /^Quantity/ })).textContent).toBe("Tap to fix");
    expect(lastCell(screen.getByRole("row", { name: /^Condition/ })).textContent).toBe("—");
  });

  it("shows the tap hint for a fixable row that was not fixed by a person", () => {
    render(<ItemComparison item={makeItem()} readOnly={true} onJumpToSourceLine={noop} fixColumn={{ selectedRowKey: null, onRowSelect: noop, fixableRowKeys: ["productId", "work"] }} />);

    const cell = lastCell(screen.getByRole("row", { name: /^Product ID/ }));
    expect(cell.textContent).toBe("Tap to fix");
    expect(cell.querySelector(".item-comparison__tap")).not.toBeNull();
  });

  it("calls onRowSelect only for fixable rows and marks the selected row", () => {
    const onRowSelect = vi.fn();
    render(<ItemComparison item={makeItem()} readOnly={true} onJumpToSourceLine={noop} fixColumn={{ selectedRowKey: "work", onRowSelect, fixableRowKeys: ["productId", "work"] }} />);

    fireEvent.click(screen.getByRole("row", { name: /^Quantity/ }));
    expect(onRowSelect).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("row", { name: /^Product ID/ }));
    expect(onRowSelect).toHaveBeenCalledExactlyOnceWith("productId");
    expect(screen.getByRole("row", { name: /^Series/ }).className).toContain("comp-table__row--selected");
    expect(screen.getByRole("row", { name: /^Quantity/ }).className).toContain("item-comparison__row--static");
  });
});
