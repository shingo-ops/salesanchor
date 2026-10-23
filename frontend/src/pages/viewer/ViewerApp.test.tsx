import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DataTableProps } from "../../components/DataTable";
import type { ViewerInventoryResponse, ViewerRow } from "./types";

// 表の描画は金型のテストが見る。ここでは行の文字とページ送りだけ出す
vi.mock("../../components/DataTable", () => ({
  DataTable: (props: DataTableProps<{ idx: number; english_title: string }>) => (
    <div data-testid="dt">
      {props.data.map((r) => (
        <div key={props.rowKey(r)} data-testid="dt-row">{r.english_title}</div>
      ))}
      <button type="button" data-testid="viewer-next" onClick={() => props.onPageChange?.(props.page! + 1)}>next</button>
      <span data-testid="viewer-pagination-label">{props.pageInfo}</span>
    </div>
  ),
}));
vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, fetchInventory: vi.fn(), readToken: vi.fn(() => "tok"), clearToken: vi.fn() };
});
import "./i18n";
import { ViewerApiError, clearToken, fetchInventory } from "./api";
import ViewerApp from "./ViewerApp";

const jstNow = () => new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 19).replace("T", " ");
const mkRow = (title: string): ViewerRow => ({
  posted_at: jstNow(), mark: "M", japanese_title: title, english_title: title, condition: "sealed",
  unit_price: "100", quantity: "1", note_ja: "", status: "In Stock", release_date: "", series: "S", provider: "P",
  search_keywords: "", ship_ja: "", offer_type: "in_stock",
});
const mkData = (updated_at: string, titles: string[]): ViewerInventoryResponse => ({
  updated_at, fresh_window_hours: 24, rows: titles.map(mkRow),
});
const titles1 = Array.from({ length: 120 }, (_, i) => `item-a${String(i).padStart(3, "0")}`);
const titles2 = [...titles1, "item-a999new"];
const fetchMock = vi.mocked(fetchInventory);

async function mountWithFirstData() {
  fetchMock.mockResolvedValueOnce(mkData("2026-10-16T03:05:00Z", titles1));
  render(<ViewerApp />);
  await act(async () => { await Promise.resolve(); });
  expect(screen.getByTestId("viewer-updated").textContent).toContain("12:05");
}

beforeEach(() => {
  vi.useFakeTimers();
  fetchMock.mockReset();
  vi.mocked(clearToken).mockReset();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("ViewerApp auto refresh", () => {
  it("T5: swaps data without losing search text or page, and never shows loading", async () => {
    await mountWithFirstData();
    fireEvent.change(screen.getByTestId("viewer-search"), { target: { value: "item-a" } });
    fireEvent.click(screen.getByTestId("viewer-next"));
    expect(screen.getByTestId("viewer-pagination-label").textContent).toContain("2");

    let resolve!: (v: ViewerInventoryResponse) => void;
    fetchMock.mockReturnValueOnce(new Promise<ViewerInventoryResponse>((r) => { resolve = r; }));
    await vi.advanceTimersByTimeAsync(60_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByTestId("viewer-loading")).toBeNull();
    await act(async () => { resolve(mkData("2026-10-16T03:06:00Z", titles2)); });

    expect(screen.queryByTestId("viewer-loading")).toBeNull();
    expect((screen.getByTestId("viewer-search") as HTMLInputElement).value).toBe("item-a");
    expect(screen.getByTestId("viewer-pagination-label").textContent).toContain("2");
    expect(screen.getByTestId("viewer-pagination-label").textContent).toContain("121");
    expect(screen.getByTestId("viewer-updated").textContent).toContain("12:06");
    fireEvent.click(screen.getByTestId("viewer-next"));
    expect(screen.getAllByTestId("dt-row").map((e) => e.textContent)).toContain("item-a999new");
  });

  it("T6: a 503 on refresh keeps the table and search text", async () => {
    await mountWithFirstData();
    fireEvent.change(screen.getByTestId("viewer-search"), { target: { value: "item-a" } });
    fetchMock.mockRejectedValueOnce(new ViewerApiError(503, "viewer_inventory_not_ready"));
    await vi.advanceTimersByTimeAsync(60_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByTestId("viewer-notice-preparing")).toBeNull();
    expect((screen.getByTestId("viewer-search") as HTMLInputElement).value).toBe("item-a");
    expect(screen.getByTestId("dt")).toBeTruthy();
  });

  it("T7: a 401 invalid viewer token on refresh goes to login and clears the token", async () => {
    await mountWithFirstData();
    fetchMock.mockRejectedValueOnce(new ViewerApiError(401, "invalid viewer token"));
    await vi.advanceTimersByTimeAsync(60_000);
    expect(screen.getByTestId("viewer-login")).toBeTruthy();
    expect(clearToken).toHaveBeenCalled();
  });

  it("T9: a 403 viewer_suspended on refresh shows the suspended notice without clearing the token", async () => {
    await mountWithFirstData();
    fetchMock.mockRejectedValueOnce(new ViewerApiError(403, "viewer_suspended"));
    await vi.advanceTimersByTimeAsync(60_000);
    expect(screen.getByTestId("viewer-notice-suspended")).toBeTruthy();
    expect(clearToken).not.toHaveBeenCalled();
  });
});
