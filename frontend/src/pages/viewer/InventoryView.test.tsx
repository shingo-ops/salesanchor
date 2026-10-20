import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DataTableProps } from "../../components/DataTable";

// DataTable に渡る props を捕まえる（描画そのものは金型のテストが見ている）
const captured: { props: DataTableProps<{ idx: number }> | null } = { props: null };
vi.mock("../../components/DataTable", () => ({
  DataTable: (props: DataTableProps<{ idx: number }>) => {
    captured.props = props;
    return <div data-testid="dt" data-rows={props.data.length} />;
  },
}));
import "./i18n";
import { InventoryView } from "./InventoryView";
import type { ViewerInventoryResponse, ViewerRow } from "./types";

const jstNow = () => new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 19).replace("T", " ");
const mkRow = (i: number): ViewerRow => ({
  posted_at: jstNow(), mark: `M${i}`, japanese_title: `n${i}`, english_title: `t${String(i).padStart(3, "0")}`, condition: "sealed",
  unit_price: String(100 + i), quantity: "1", note_ja: "", status: "In Stock", release_date: "", series: "S", provider: "P",
  search_keywords: "", ship_ja: "", offer_type: "in_stock",
});
const data: ViewerInventoryResponse = {
  updated_at: "2026-10-16T03:05:00Z", fresh_window_hours: 24, rows: Array.from({ length: 120 }, (_, i) => mkRow(i)),
};

beforeEach(() => { captured.props = null; });
afterEach(() => cleanup());

describe("InventoryView", () => {
  it("has no password-change or logout button in the header", () => {
    render(<InventoryView data={data} />);
    expect(screen.queryByTestId("viewer-change-password")).toBeNull();
    expect(screen.queryByTestId("viewer-logout")).toBeNull();
  });
  it("passes the designed props to DataTable: sticky, fit, cards, 50 per page, default sort release_date desc", () => {
    render(<InventoryView data={data} />);
    const p = captured.props!;
    expect(p.stickyHeader).toBe(true);
    expect(p.fitToWidth).toBe(true);
    expect(p.mobileCards).toBe(true);
    expect(p.data).toHaveLength(50);
    expect(p.sortKey).toBe("release_date");
    expect(p.sortDir).toBe("desc");
    expect(p.hasNextPage).toBe(true);
    expect(typeof p.onPageChange).toBe("function");
    expect(p.rowKey({ idx: 7 })).toBe("7");
  });

  it("shows the last updated time as HH:MM (JST) and has no refresh button", () => {
    render(<InventoryView data={data} />);
    expect(screen.getByTestId("viewer-updated").textContent).toContain("12:05");
    expect(screen.queryByTestId("viewer-refresh")).toBeNull();
  });

  it("sort pull-down has a heading plus 3 options (no release_date:desc) and shows the heading by default", () => {
    render(<InventoryView data={data} />);
    const select = screen.getByTestId("viewer-sort-menu") as HTMLSelectElement;
    expect(select.value).toBe("");
    expect(Array.from(select.options).map((o) => o.value)).toEqual(["", "unit_price:asc", "quantity:desc", "offered_at:desc"]);
    fireEvent.change(select, { target: { value: "unit_price:asc" } });
    expect(captured.props!.sortKey).toBe("unit_price");
    expect(captured.props!.sortDir).toBe("asc");
  });

  it("choosing the heading after another sort returns to release_date desc", () => {
    render(<InventoryView data={data} />);
    const select = screen.getByTestId("viewer-sort-menu") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "unit_price:asc" } });
    expect(captured.props!.sortKey).toBe("unit_price");
    fireEvent.change(select, { target: { value: "" } });
    expect(captured.props!.sortKey).toBe("release_date");
    expect(captured.props!.sortDir).toBe("desc");
    expect(select.value).toBe("");
  });

  it("24 hours button is pressed by default and toggles", () => {
    render(<InventoryView data={data} />);
    const btn = screen.getByTestId("viewer-fresh-toggle");
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-pressed")).toBe("false");
  });

  it("PC: two-row toolbar, no filter button, reset restores search and sort", () => {
    render(<InventoryView data={data} />);
    expect(screen.queryByTestId("viewer-filter-toggle")).toBeNull();
    const rows = document.querySelectorAll(".content-toolbar--two-rows > .content-toolbar__row");
    expect(rows).toHaveLength(2);
    for (const id of ["viewer-search", "viewer-price-min", "viewer-qty-max"]) {
      expect(rows[0].contains(screen.getByTestId(id))).toBe(true);
    }
    for (const id of ["viewer-sort-menu", "viewer-condition-filter-button", "viewer-provider-filter-button", "viewer-fresh-toggle", "viewer-reset"]) {
      expect(rows[1].contains(screen.getByTestId(id))).toBe(true);
    }
    fireEvent.change(screen.getByTestId("viewer-search"), { target: { value: "t001" } });
    fireEvent.change(screen.getByTestId("viewer-sort-menu"), { target: { value: "unit_price:asc" } });
    expect(captured.props!.sortKey).toBe("unit_price");
    expect(captured.props!.data).toHaveLength(1);
    fireEvent.click(screen.getByTestId("viewer-reset"));
    expect((screen.getByTestId("viewer-search") as HTMLInputElement).value).toBe("");
    expect(captured.props!.sortKey).toBe("release_date");
    expect(captured.props!.sortDir).toBe("desc");
    expect(captured.props!.data).toHaveLength(50);
  });

  it("mobile: keeps the old single toolbar with the filter button", () => {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      writable: true,
      value: (q: string) => ({
        matches: true, media: q, onchange: null,
        addEventListener: () => undefined, removeEventListener: () => undefined,
        addListener: () => undefined, removeListener: () => undefined, dispatchEvent: () => false,
      }),
    });
    try {
      render(<InventoryView data={data} />);
      expect(document.querySelector(".content-toolbar--two-rows")).toBeNull();
      expect(screen.getByTestId("viewer-filter-toggle")).toBeTruthy();
      expect(screen.queryByTestId("viewer-reset")).toBeNull();
    } finally {
      delete (window as unknown as { matchMedia?: unknown }).matchMedia;
    }
  });
});
