import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { InventoryRowDrawer } from "./InventoryRowDrawer";
import type { InventoryRow } from "./inventoryColumns";

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
  ship_timing: null, supplier_id: 1, supplier_name: "S", unit_price: 1, quantity: 1, tcg_type: null,
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
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} />);

    expect(await screen.findByText("original post text")).toBeTruthy();
    expect(screen.getAllByText("gemini-a").length).toBeGreaterThan(0);
    expect(screen.getAllByText("system-a").length).toBeGreaterThan(0);
    expect(mock.get).toHaveBeenCalledWith("/tcg/analysis-results?extraction_item_ids=a");
    expect(screen.queryByRole("tab")).toBeNull();
    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();
  });

  it("F4: a merged row (2 ids) shows 2 tabs and switches between the items", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a"), item("b", "text-b")] });
    render(<InventoryRowDrawer row={row(["a", "b"])} onClose={() => undefined} onChanged={() => undefined} />);

    expect(await screen.findByText("text-a")).toBeTruthy();
    expect(mock.get).toHaveBeenCalledWith("/tcg/analysis-results?extraction_item_ids=a&extraction_item_ids=b");
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Item 1", "Item 2"]);
    fireEvent.click(tabs[1]);
    expect(await screen.findByText("text-b")).toBeTruthy();
  });

  it("shows the not-found text when no result comes back", async () => {
    mock.get.mockResolvedValue({ items: [] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} />);

    expect(await screen.findByText(/No analysis result for this row/)).toBeTruthy();
  });

  it("shows the load error text on a failure", async () => {
    mock.get.mockRejectedValue(new Error("boom"));
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} />);

    await waitFor(() => expect(screen.getByText("Failed to load the analysis result")).toBeTruthy());
  });

  const rowOf = (label: string) => screen.getByRole("row", { name: new RegExp(`^${label}`) });

  it("E1: pressing a comparison row opens the fix wizard (not view-only)", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a")] });
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={() => undefined} />);

    await screen.findByText("text-a");
    expect(screen.getByRole("columnheader", { name: "Fix" })).toBeTruthy();
    fireEvent.click(rowOf("Condition"));
    expect(screen.getByTestId("condition-panel")).toBeTruthy();
  });

  it("E2: onRefresh reloads the panel and calls onChanged", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a")] });
    const onChanged = vi.fn();
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={onChanged} />);

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
    render(<InventoryRowDrawer row={row(["a"])} onClose={() => undefined} onChanged={onChanged} />);

    await screen.findByText("text-a");
    const [topics, reload] = mock.realtime.mock.calls[mock.realtime.mock.calls.length - 1] as [string[], () => void];
    expect(topics).toEqual(["tcg.review"]);
    reload();

    await waitFor(() => expect(mock.get).toHaveBeenCalledTimes(2));
  });

  it("E4: switching tabs drops the selected row and the wizard", async () => {
    mock.get.mockResolvedValue({ items: [item("a", "text-a"), item("b", "text-b")] });
    render(<InventoryRowDrawer row={row(["a", "b"])} onClose={() => undefined} onChanged={() => undefined} />);

    await screen.findByText("text-a");
    fireEvent.click(rowOf("Condition"));
    expect(screen.getByTestId("condition-panel")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("tab")[1]);

    expect(await screen.findByText("text-b")).toBeTruthy();
    expect(screen.queryByTestId("condition-panel")).toBeNull();
    expect(rowOf("Condition").className).not.toContain("comp-table__row--selected");
  });
});
