import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { InventoryRowDrawer } from "./InventoryRowDrawer";
import type { InventoryRow } from "./inventoryColumns";
import { fmtOfferedAt } from "./inventoryFormat";

const mock = vi.hoisted(() => ({ get: vi.fn(), realtime: vi.fn() }));
vi.mock("../../hooks/useRealtimeRefresh", () => ({
  useRealtimeRefresh: (topics: readonly string[], reload: () => void) => mock.realtime(topics, reload),
}));
vi.mock("../tcg-analysis-review/ConditionReviewPanel", async () => ({
  ...(await vi.importActual<typeof import("../tcg-analysis-review/ConditionReviewPanel")>("../tcg-analysis-review/ConditionReviewPanel")),
  ConditionReviewPanel: (props: { onRefresh: () => Promise<void> }) => (
    <button type="button" data-testid="condition-panel" onClick={() => void props.onRefresh()}>refresh</button>
  ),
}));
vi.mock("../../lib/api", () => ({
  api: mock,
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

const item = (id: string, raw: string) => ({
  extraction_item_id: id, source_message_id: "msg-1", provider: "Supplier A", raw_text: raw,
  gemini: { name: `gemini-${id}` }, system: { work_name: `system-${id}` },
  review_reason_details: [], review_issues: [],
  condition_review: { condition_id: "1", review_version: "v", needs_review: true, review_reasons: "condition_unknown", confirmed: false, classification: "none" },
});

const row = (ids: string[]): InventoryRow => ({
  id: "r1", product_id: 1, product_name: "P", name_en: null, category: null, mark: null, condition: "New", unit: null,
  offer_type: null, status: null, note_ja: null, ship_ja: null, merged_count: ids.length, posted_at: null,
  ship_timing: null, supplier_id: 1, supplier_name: "S", unit_price: 1, quantity: 1, work_code: null,
  offered_at: "", release_date: null, extraction_item_ids: ids,
});

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("InventoryRowDrawer", () => {
  it("F1: loads by item ids and shows the source text, Gemini and system results", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "original post text")] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    expect(await screen.findByText("original post text")).toBeTruthy();
    expect(screen.getAllByText("gemini-a").length).toBeGreaterThan(0);
    expect(screen.getAllByText("system-a").length).toBeGreaterThan(0);
    expect(mock.get).toHaveBeenCalledWith("/tcg/analysis-results?extraction_item_ids=a");
    expect(screen.queryByRole("tab", { name: /^Item/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();
  });

  it("F4: a merged row (2 ids) shows 2 tabs and switches between the items", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a"), item("b", "text-b")] });
    render(<InventoryRowDrawer row={row(["a", "b"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    expect(await screen.findByText("text-a")).toBeTruthy();
    expect(mock.get).toHaveBeenCalledWith("/tcg/analysis-results?extraction_item_ids=a&extraction_item_ids=b");
    const tabs = screen.getAllByRole("tab", { name: /^Item/ });
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Item 1", "Item 2"]);
    fireEvent.click(tabs[1]);
    expect(await screen.findByText("text-b")).toBeTruthy();
  });

  it("shows the not-found text when no result comes back", async () => {
    mock.get.mockResolvedValue({ items: [] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    expect(await screen.findByText(/No analysis result for this row/)).toBeTruthy();
  });

  it("shows the load error text on a failure", async () => {
    mock.get.mockRejectedValue(new Error("boom"));
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    await waitFor(() => expect(screen.getByText("Failed to load the analysis result")).toBeTruthy());
  });

  const rowOf = (label: string) => screen.getByRole("row", { name: new RegExp(`^${label}`) });

  it("E1: pressing a comparison row opens the fix wizard (not view-only)", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a")] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    await screen.findByText("text-a");
    expect(screen.getByRole("columnheader", { name: "Fix" })).toBeTruthy();
    fireEvent.click(rowOf("Condition"));
    expect(screen.getByTestId("condition-panel")).toBeTruthy();
  });

  it("E2: onRefresh reloads the panel and calls onChanged", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a")] });
    const onChanged = vi.fn();
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={onChanged} isSuperAdmin />);

    await screen.findByText("text-a");
    expect(mock.get).toHaveBeenCalledTimes(1);
    fireEvent.click(rowOf("Condition"));
    fireEvent.click(screen.getByTestId("condition-panel"));

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(mock.get).toHaveBeenCalledTimes(2);
  });

  it("E3: a tcg.review signal reloads the panel", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a")] });
    const onChanged = vi.fn();
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={onChanged} isSuperAdmin />);

    await screen.findByText("text-a");
    const [topics, reload] = mock.realtime.mock.calls[mock.realtime.mock.calls.length - 1] as [string[], () => void];
    expect(topics).toEqual(["tcg.review"]);
    reload();

    await waitFor(() => expect(mock.get).toHaveBeenCalledTimes(2));
  });

  it("E4: switching tabs drops the selected row and the wizard", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a"), item("b", "text-b")] });
    render(<InventoryRowDrawer row={row(["a", "b"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    await screen.findByText("text-a");
    fireEvent.click(rowOf("Condition"));
    expect(screen.getByTestId("condition-panel")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("tab", { name: /^Item/ })[1]);

    expect(await screen.findByText("text-b")).toBeTruthy();
    expect(screen.queryByTestId("condition-panel")).toBeNull();
    expect(rowOf("Condition").className).not.toContain("comp-table__row--selected");
  });

  // --- 便4: 原文タブ ---
  const rawOf = (id: string, text: string, start: number | null = 2, end: number | null = 2) => ({
    extraction_item_id: id, raw_text: text, line_start: start, line_end: end,
  });
  const apiUrls = () => mock.get.mock.calls.map(([u]) => String(u));

  it("T1: super admin sees Analysis and Original text tabs, Analysis is the default and the existing view is kept", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a")] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    await screen.findByText("text-a");
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Analysis", "Original text"]);
    expect(tabs[0].getAttribute("aria-selected")).toBe("true");
    expect(apiUrls()).toEqual(["/tcg/analysis-results?extraction_item_ids=a"]);
  });

  it("T2: opening the Original text tab calls /inventory/raw-texts and highlights the row lines", async () => {
    mock.get.mockImplementation(async (url: string) => {
      if (url.startsWith("/inventory/raw-texts")) return { items: [rawOf("a", "line one\nline two\nline three", 2, 2)] };
      return { items: [item("a", "text-a")] };
    });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin />);

    await screen.findByText("text-a");
    expect(apiUrls().some((u) => u.startsWith("/inventory/raw-texts"))).toBe(false);
    fireEvent.click(screen.getByRole("tab", { name: "Original text" }));

    expect(await screen.findByText("line two")).toBeTruthy();
    expect(apiUrls()).toContain("/inventory/raw-texts?extraction_item_ids=a");
    const line = screen.getByText("line two").closest(".shadow-source-line");
    expect(line?.className).toContain("shadow-source-line--block");
    expect(screen.getByText("line one").closest(".shadow-source-line")?.className).not.toContain("shadow-source-line--block");
  });

  it("T3: a non super admin sees only the original text, no tabs, no analysis call and no tcg.review subscription", async () => {
    mock.get.mockResolvedValue({ items: [rawOf("a", "only raw")] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);

    expect(await screen.findByText("only raw")).toBeTruthy();
    expect(screen.queryByRole("tab")).toBeNull();
    expect(apiUrls()).toEqual(["/inventory/raw-texts?extraction_item_ids=a"]);
    expect(mock.realtime).not.toHaveBeenCalled();
  });

  it("T7: the original text root has the full-height class and wraps the source pane", async () => {
    mock.get.mockResolvedValue({ items: [rawOf("a", "tall text")] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);

    await screen.findByText("tall text");
    const root = document.querySelector(".inventory-rawtext-pane");
    expect(root).not.toBeNull();
    expect(root?.querySelector(".shadow-source-pane")).not.toBeNull();
  });

  it("T4: a null line range shows the raw text without a highlight", async () => {
    mock.get.mockResolvedValue({ items: [rawOf("a", "plain text", null, null)] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);

    const line = (await screen.findByText("plain text")).closest(".shadow-source-line");
    expect(line?.className).not.toContain("shadow-source-line--block");
  });

  it("T5: a merged row shows item tabs for the original text and switches between them", async () => {
    mock.get.mockResolvedValue({ items: [rawOf("b", "raw-b"), rawOf("a", "raw-a")] });
    render(<InventoryRowDrawer row={row(["a", "b"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);

    expect(await screen.findByText("raw-a")).toBeTruthy();
    expect(mock.get).toHaveBeenCalledWith("/inventory/raw-texts?extraction_item_ids=a&extraction_item_ids=b");
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Item 1", "Item 2"]);
    fireEvent.click(tabs[1]);
    expect(await screen.findByText("raw-b")).toBeTruthy();
  });

  it("T6b: a non super admin getting 403 sees the common load error, not the super admin only text", async () => {
    const { ApiError } = await import("../../lib/api");
    mock.get.mockRejectedValue(new ApiError("x", 403, null));
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);
    expect(await screen.findByText("Failed to load the analysis result")).toBeTruthy();
    expect(screen.queryByText("This page is restricted to super_admin.")).toBeNull();
  });

  it("T6: the original text view maps 404 and other errors to the existing texts", async () => {
    const { ApiError } = await import("../../lib/api");
    mock.get.mockRejectedValue(new ApiError("x", 404, null));
    const second = render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);
    expect(await screen.findByText(/No analysis result for this row/)).toBeTruthy();
    second.unmount();

    mock.get.mockRejectedValue(new Error("boom"));
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);
    expect(await screen.findByText("Failed to load the analysis result")).toBeTruthy();
  });

  describe("raw text slide header", () => {
    const rawItem = { extraction_item_id: "a", raw_text: "raw body", line_start: 1, line_end: 1 };
    const renderRaw = (r: InventoryRow) => {
      mock.get.mockResolvedValue({ items: [rawItem] });
      render(<InventoryRowDrawer row={r} onClose={() => undefined} onChanged={() => undefined} isSuperAdmin={false} />);
    };

    it("J1: heading is '<supplier> <offered_at>' as in the supplier column", async () => {
      const r = { ...row(["a"]), supplier_name: "Shop A", offered_at: "2026-10-17T09:05:00" };
      renderRaw(r);
      expect(await screen.findByText("raw body")).toBeTruthy();
      expect(screen.getByRole("heading", { name: `Shop A ${fmtOfferedAt(r.offered_at)}` })).toBeTruthy();
    });

    it("falls back to #supplier_id when supplier_name is null", async () => {
      const r = { ...row(["a"]), supplier_name: null, supplier_id: 42, offered_at: "2026-10-17T09:05:00" };
      renderRaw(r);
      expect(await screen.findByText("raw body")).toBeTruthy();
      expect(screen.getByRole("heading", { name: `#42 ${fmtOfferedAt(r.offered_at)}` })).toBeTruthy();
    });

    it("J2: does not show the block range legend", async () => {
      renderRaw({ ...row(["a"]), offered_at: "2026-10-17T09:05:00" });
      expect(await screen.findByText("raw body")).toBeTruthy();
      expect(screen.queryByText("Block range")).toBeNull();
      expect(document.querySelector(".shadow-source-legend")).toBeNull();
    });
  });
});
