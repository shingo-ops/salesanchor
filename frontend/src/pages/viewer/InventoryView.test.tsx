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

  it("T8: re-evaluates the 24h window against a fresh clock when data is replaced", () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-10-22T03:00:00Z"));
      const jst = (ms: number) => new Date(ms + 9 * 3600 * 1000).toISOString().slice(0, 19).replace("T", " ");
      const old = { ...mkRow(1), posted_at: jst(Date.now() - 23.5 * 3600 * 1000) };
      const d1: ViewerInventoryResponse = { ...data, rows: [old] };
      const { rerender } = render(<InventoryView data={d1} />);
      expect(captured.props!.data).toHaveLength(1);
      vi.setSystemTime(new Date("2026-10-22T04:00:00Z"));
      rerender(<InventoryView data={{ ...d1, updated_at: "2026-10-22T04:00:00Z" }} />);
      expect(captured.props!.data).toHaveLength(0);
    } finally {
      vi.useRealTimers();
    }
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

  /* eslint-disable local/no-japanese-literal -- DB の series 名（画面文言ではない） */
  const seriesData: ViewerInventoryResponse = {
    ...data,
    rows: [
      { ...mkRow(1), series: "ポケモン" },
      { ...mkRow(2), series: "ワンピース" },
      { ...mkRow(3), series: "ホロライブ" },
      { ...mkRow(4), series: "アクア" },
    ],
  };

  it("K3: PC tabs are all + 3 main series, no counts, 'other' pull-down lists the rest in name order, tab row sits right before the table", () => {
    render(<InventoryView data={seriesData} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
    expect(tabs.slice(1).map((el) => el.textContent)).toEqual(["ポケモン", "ワンピース", "ドラゴンボール"]);
    expect(document.querySelector(".comp-tabs__tab .comp-badge")).toBeNull();
    const other = screen.getByTestId("viewer-tab-other") as HTMLSelectElement;
    expect(Array.from(other.options).map((o) => o.value)).toEqual(["", "アクア", "ホロライブ"]);
    const bar = screen.getByRole("tablist").closest(".comp-tabs-bar") as HTMLElement;
    expect(bar.nextElementSibling).toBe(screen.getByTestId("dt"));
    expect(captured.props!.attachedTop).toBe(true);
  });

  it("K4: choosing a series in 'other' shows only that series and clears the tab selection", () => {
    render(<InventoryView data={seriesData} />);
    fireEvent.change(screen.getByTestId("viewer-tab-other"), { target: { value: "ホロライブ" } });
    expect(captured.props!.data).toHaveLength(1);
    expect((captured.props!.data[0] as unknown as { series: string }).series).toBe("ホロライブ");
    expect((screen.getByTestId("viewer-tab-other") as HTMLSelectElement).className).toContain("comp-select--tab-active");
    for (const tab of screen.getAllByRole("tab")) expect(tab.getAttribute("aria-selected")).toBe("false");
    fireEvent.click(screen.getAllByRole("tab")[1]);
    expect(captured.props!.data).toHaveLength(1);
    expect((captured.props!.data[0] as unknown as { series: string }).series).toBe("ポケモン");
  });

  it("K5: mobile keeps the series select with counts and shows no tab row", () => {
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
      render(<InventoryView data={seriesData} />);
      const sel = screen.getByTestId("viewer-tab-select") as HTMLSelectElement;
      expect(sel.options[1].textContent).toMatch(/\(\d+\)$/);
      expect(screen.queryByRole("tablist")).toBeNull();
      expect(captured.props!.attachedTop).toBe(false);
    } finally {
      delete (window as unknown as { matchMedia?: unknown }).matchMedia;
    }
  });

  const mobileMatchMedia = {
    configurable: true,
    writable: true,
    value: (q: string) => ({
      matches: true, media: q, onchange: null,
      addEventListener: () => undefined, removeEventListener: () => undefined,
      addListener: () => undefined, removeListener: () => undefined, dispatchEvent: () => false,
    }),
  };

  it("K1: PC opens on the first main series tab and shows only its rows", () => {
    render(<InventoryView data={seriesData} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs[1].textContent).toBe("ポケモン");
    expect(tabs[1].getAttribute("aria-selected")).toBe("true");
    expect(tabs[0].getAttribute("aria-selected")).toBe("false");
    expect(captured.props!.data).toHaveLength(1);
    expect((captured.props!.data[0] as unknown as { series: string }).series).toBe("ポケモン");
  });

  it("K1: mobile select opens on the first main series", () => {
    Object.defineProperty(window, "matchMedia", mobileMatchMedia);
    try {
      render(<InventoryView data={seriesData} />);
      expect((screen.getByTestId("viewer-tab-select") as HTMLSelectElement).value).toBe("ポケモン");
      expect(captured.props!.data).toHaveLength(1);
    } finally {
      delete (window as unknown as { matchMedia?: unknown }).matchMedia;
    }
  });

  it("K2: opens on 'all' when there is no row of the first main series", () => {
    const noPokemon: ViewerInventoryResponse = {
      ...data,
      rows: [{ ...mkRow(2), series: "ワンピース" }, { ...mkRow(3), series: "ホロライブ" }],
    };
    render(<InventoryView data={noPokemon} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs[0].getAttribute("aria-selected")).toBe("true");
    expect(captured.props!.data).toHaveLength(2);
  });
  /* eslint-enable local/no-japanese-literal */

  const providerData: ViewerInventoryResponse = {
    ...data,
    rows: [
      ...Array.from({ length: 5 }, (_, i) => ({ ...mkRow(i), provider: "Acme" })),
      ...Array.from({ length: 5 }, (_, i) => ({ ...mkRow(i + 5), provider: "Globex" })),
    ],
  };

  it("A14: opening the drawer moves focus to its first focusable element", () => {
    Object.defineProperty(window, "matchMedia", mobileMatchMedia);
    try {
      render(<InventoryView data={providerData} />);
      fireEvent.click(screen.getByTestId("viewer-filter-toggle"));
      expect(document.activeElement).toBe(screen.getByTestId("drawer-close"));
    } finally {
      delete (window as unknown as { matchMedia?: unknown }).matchMedia;
    }
  });

  describe("filter subscreen navigation (docs/handoff/viewer-filter-subscreen/design.md 4-4)", () => {
    function openDrawer() {
      Object.defineProperty(window, "matchMedia", mobileMatchMedia);
      render(<InventoryView data={providerData} />);
      fireEvent.click(screen.getByTestId("viewer-filter-toggle"));
    }
    afterEach(() => {
      delete (window as unknown as { matchMedia?: unknown }).matchMedia;
    });

    it("A1/A2: root shows the provider and condition rows and is not a subscreen (no drawer-back)", () => {
      openDrawer();
      expect(screen.getByTestId("viewer-provider-row")).toBeTruthy();
      expect(screen.getByTestId("viewer-condition-row")).toBeTruthy();
      expect(screen.queryByTestId("drawer-back")).toBeNull();
    });

    it("A2/A14: clicking the provider row opens the subscreen, drawer-back appears and takes focus", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      expect(screen.getByTestId("viewer-provider-options-option-Acme")).toBeTruthy();
      const back = screen.getByTestId("drawer-back");
      expect(back).toBeTruthy();
      expect(document.activeElement).toBe(back);
    });

    it("A3/A14: back returns to root, drawer-back disappears and focus returns to the row", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.click(screen.getByTestId("drawer-back"));
      expect(screen.queryByTestId("drawer-back")).toBeNull();
      expect(screen.getByTestId("viewer-provider-row")).toBeTruthy();
      expect(document.activeElement).toBe(screen.getByTestId("viewer-provider-row"));
    });

    it("A11: apply returns to root and keeps the selection", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.click(screen.getByTestId("viewer-provider-options-option-Acme"));
      fireEvent.click(screen.getByTestId("viewer-filter-apply"));
      expect(screen.queryByTestId("drawer-back")).toBeNull();
      expect(captured.props!.data).toHaveLength(5);
      // 親の行に選んだ名前が出る（A7）
      expect(screen.getByTestId("viewer-provider-row").textContent).toContain("Acme");
    });

    it("A12: Escape in a subscreen returns to root (the drawer stays open)", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByTestId("drawer-back")).toBeNull();
      expect(screen.getByTestId("viewer-provider-row")).toBeTruthy();
    });

    it("A8/A9: narrowing the options by search keeps the selected names resolved", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.click(screen.getByTestId("viewer-provider-options-option-Acme"));
      fireEvent.click(screen.getByTestId("viewer-provider-options-option-Globex"));
      // "Acme" を検索語で画面から追い出す
      fireEvent.change(screen.getByTestId("viewer-filter-option-search"), { target: { value: "Globex" } });
      expect(screen.queryByTestId("viewer-provider-options-option-Acme")).toBeNull();
      expect(screen.getByTestId("viewer-provider-options-option-Globex")).toBeTruthy();
      // 要約（inline の summary）は絞り込み前の2件とも正しい名前のまま
      expect(document.querySelector(".comp-multiselect__inline-summary")!.textContent).toBe("Acme, Globex");
    });

    it("A10: a query with no matches shows the noOptions text", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.change(screen.getByTestId("viewer-filter-option-search"), { target: { value: "no-such-provider" } });
      // eslint-disable-next-line local/no-japanese-literal -- テスト: 画面に出る日本語文言そのものを検証する（ADR-027・precedent: src/features/tcg-analysis-review/SourceRawPane.test.tsx:1）
      expect(screen.getByText("見つかりません")).toBeTruthy();
    });

    it("A17: the option search box is cleared when leaving the subscreen with back", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.change(screen.getByTestId("viewer-filter-option-search"), { target: { value: "Acme" } });
      fireEvent.click(screen.getByTestId("drawer-back"));
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      expect((screen.getByTestId("viewer-filter-option-search") as HTMLInputElement).value).toBe("");
    });

    it("A17: the option search box is cleared when leaving with apply", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.change(screen.getByTestId("viewer-filter-option-search"), { target: { value: "Acme" } });
      fireEvent.click(screen.getByTestId("viewer-filter-apply"));
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      expect((screen.getByTestId("viewer-filter-option-search") as HTMLInputElement).value).toBe("");
    });

    it("the condition row navigates the same way", () => {
      openDrawer();
      fireEvent.click(screen.getByTestId("viewer-condition-row"));
      expect(screen.getByTestId("drawer-back")).toBeTruthy();
      expect(screen.getByTestId("viewer-condition-options-option-sealed")).toBeTruthy();
      fireEvent.click(screen.getByTestId("drawer-back"));
      expect(document.activeElement).toBe(screen.getByTestId("viewer-condition-row"));
    });
  });

  it("A15: mobile — opening the drawer, entering the provider screen, and selecting one provider narrows the table", () => {
    Object.defineProperty(window, "matchMedia", mobileMatchMedia);
    try {
      render(<InventoryView data={providerData} />);
      expect(captured.props!.data).toHaveLength(10);
      fireEvent.click(screen.getByTestId("viewer-filter-toggle"));
      fireEvent.click(screen.getByTestId("viewer-provider-row"));
      fireEvent.click(screen.getByTestId("viewer-provider-options-option-Acme"));
      expect(captured.props!.data).toHaveLength(5);
    } finally {
      delete (window as unknown as { matchMedia?: unknown }).matchMedia;
    }
  });
});
