import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import i18n from "../../../i18n";
import NeedsReviewTabsPanel from "./NeedsReviewTabsPanel";

let fireRealtime: () => void = () => undefined;

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));
vi.mock("../../../hooks/useRealtimeRefresh", () => ({
  useRealtimeRefresh: (_topics: readonly string[], reload: () => void) => {
    fireRealtime = reload;
  },
}));
vi.mock("../../../features/tcg-analysis-review/V102PostsTab", () => ({ V102PostsTab: () => <div>posts-tab</div> }));
vi.mock("../../../features/tcg-review-csv/ReviewCsvPanel", () => ({ ReviewCsvPanel: () => <div>csv-panel</div> }));

const makeItem = (id: string, name: string) => ({
  extraction_item_id: id,
  source_message_id: `source-${id}`,
  provider: "Supplier A",
  raw_text: "",
  gemini: { name, quantity: "1", price: "100", unit: "", state: "", memo: "", span: "L1-1" },
  system: { product_id: "", product_title: "" },
  review_issues: [],
  is_v102: true,
  condition_review: null,
  review_reason_details: [],
});

const response = (items: ReturnType<typeof makeItem>[]) => ({
  items, total: items.length, item_total: items.length, offset: 0, limit: 20, providers: [], works: [],
});

const listCalls = () => vi.mocked(api.get).mock.calls.map(([p]) => String(p)).filter((p) => p.startsWith("/tcg/analysis-results"));
const lastCall = () => { const c = listCalls(); return c[c.length - 1] ?? ""; };

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockImplementation((path: string) =>
    Promise.resolve(response(path.includes("status_tab=ACKED") ? [makeItem("acked-1", "Card Acked")] : [makeItem("need-1", "Card Need")])),
  );
});
afterEach(() => cleanup());

const view = () => render(<MemoryRouter><NeedsReviewTabsPanel /></MemoryRouter>);

describe("acked tab", () => {
  it("is placed between the production and posts tabs and loads status_tab=ACKED from offset 0", async () => {
    view();
    await screen.findByText("Card Need");
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Production review", "Checked", "Posts"]);
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    expect(await screen.findByText("Card Acked")).toBeTruthy();
    const last = lastCall() ?? "";
    expect(last).toContain("status_tab=ACKED");
    expect(last).toContain("offset=0");
    expect(screen.queryByText("csv-panel")).toBeNull();
  });

  it("shows the acked empty text on the acked tab and the review empty text on production", async () => {
    vi.mocked(api.get).mockResolvedValue(response([]));
    view();
    expect(await screen.findByText("No items need review")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    expect(await screen.findByText("No confirmed items")).toBeTruthy();
  });

  it("shows the CSV card on the production tab only", async () => {
    view();
    expect(await screen.findByText("csv-panel")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    await screen.findByText("Card Acked");
    expect(screen.queryByText("csv-panel")).toBeNull();
  });

  it("opens the drawer in the acked view with the revoke button, and no removed notice", async () => {
    view();
    fireEvent.click(await screen.findByRole("tab", { name: "Checked" }));
    fireEvent.click(await screen.findByText("Card Acked"));
    await screen.findByRole("dialog");
    expect(screen.getByText("This item is marked as checked")).toBeTruthy();
    expect(screen.getByRole("button", { name: 'Undo "checked"' })).toBeTruthy();
    expect(screen.queryByText("This item is no longer in the review list")).toBeNull();
  });

  it("does not show the acked view on the production tab", async () => {
    view();
    fireEvent.click(await screen.findByText("Card Need"));
    await screen.findByRole("dialog");
    expect(screen.queryByText("This item is marked as checked")).toBeNull();
  });

  it("resets the page and closes the drawer when the tab is switched", async () => {
    view();
    fireEvent.click(await screen.findByText("Card Need"));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    await screen.findByText("Card Acked");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("keeps the rows when the already-open tab is pressed again", async () => {
    view();
    await screen.findByText("Card Need");
    const before = listCalls().length;
    fireEvent.click(screen.getByRole("tab", { name: "Production review" }));
    expect(screen.getByText("Card Need")).toBeTruthy();
    expect(listCalls().length).toBe(before);
  });

  it("reloads the acked tab when the realtime signal arrives", async () => {
    view();
    fireEvent.click(await screen.findByRole("tab", { name: "Checked" }));
    await screen.findByText("Card Acked");
    const before = listCalls().length;
    act(() => fireRealtime());
    await waitFor(() => expect(listCalls().length).toBe(before + 1));
    expect(lastCall()).toContain("status_tab=ACKED");
  });

  it("does not show acked rows on production after: posts -> signal -> acked -> production", async () => {
    view();
    await screen.findByText("Card Need");
    fireEvent.click(screen.getByRole("tab", { name: "Posts" }));
    await screen.findByText("posts-tab");
    act(() => fireRealtime()); // posts 表示中の合図。effect は止まったまま
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    await screen.findByText("Card Acked");
    fireEvent.click(screen.getByRole("tab", { name: "Production review" }));
    await screen.findByText("Card Need");
    expect(screen.queryByText("Card Acked")).toBeNull();
    expect(lastCall()).toContain("status_tab=NEEDS_REVIEW");
  });
});
