import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import i18n from "../../../i18n";
import { formatDate } from "../../../features/tcg-analysis-review/formatDateTime";
import NeedsReviewTabsPanel from "./NeedsReviewTabsPanel";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));
vi.mock("../../../hooks/useRealtimeRefresh", () => ({ useRealtimeRefresh: () => undefined }));
vi.mock("../../../features/tcg-analysis-review/V102PostsTab", () => ({ V102PostsTab: () => <div>posts-tab</div> }));
vi.mock("../../../features/tcg-review-csv/ReviewCsvPanel", () => ({ ReviewCsvPanel: () => <div>csv-panel</div> }));

const makeItem = (id: string, name: string, postedAt: string | null) => ({
  extraction_item_id: id,
  source_message_id: `source-${id}`,
  provider: "Supplier A",
  posted_at: postedAt,
  raw_text: "",
  gemini: { name, span: "L1-1" },
  system: {},
  review_issues: [],
  condition_review: null,
  review_reason_details: [],
});

const response = (items: ReturnType<typeof makeItem>[]) => ({
  items, total: items.length, item_total: items.length, offset: 0, limit: 25, providers: [], works: [],
});

const listCalls = () =>
  vi.mocked(api.get).mock.calls.map(([p]) => String(p)).filter((p) => p.startsWith("/tcg/analysis-results"));
const lastCall = () => { const c = listCalls(); return c[c.length - 1] ?? ""; };
const paramsOf = (path: string) => new URLSearchParams(path.split("?")[1]);
const view = () => render(<MemoryRouter><NeedsReviewTabsPanel /></MemoryRouter>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockImplementation(() =>
    // 2026-10-21 00:30:00Z = 日本時間 09:30
    Promise.resolve(response([makeItem("a", "Card A", "2026-10-21T00:30:00Z"), makeItem("b", "Card B", null)])),
  );
});
afterEach(() => cleanup());

describe("production tab: posted-desc list, 24h button, page size", () => {
  it("first GET asks for newest-first, 24 hours, 25 rows from offset 0", async () => {
    view();
    await screen.findByText("Card A");
    const p = paramsOf(listCalls()[0]);
    expect(p.get("status_tab")).toBe("NEEDS_REVIEW");
    expect(p.get("order")).toBe("posted_desc");
    expect(p.get("posted_within_hours")).toBe("24");
    expect(p.get("limit")).toBe("25");
    expect(p.get("offset")).toBe("0");
  });

  it("turning the 24h button off drops posted_within_hours and returns to offset 0", async () => {
    view();
    await screen.findByText("Card A");
    const button = screen.getByTestId("needs-review-fresh-toggle");
    expect(button.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(button);
    await waitFor(() => expect(paramsOf(lastCall()).has("posted_within_hours")).toBe(false));
    expect(screen.getByTestId("needs-review-fresh-toggle").getAttribute("aria-pressed")).toBe("false");
    expect(paramsOf(lastCall()).get("offset")).toBe("0");
    expect(paramsOf(lastCall()).get("order")).toBe("posted_desc");
  });

  it("changing the page size to 50 asks for limit=50 from offset 0", async () => {
    view();
    await screen.findByText("Card A");
    fireEvent.change(screen.getByTestId("needs-review-page-size"), { target: { value: "50" } });
    await waitFor(() => expect(paramsOf(lastCall()).get("limit")).toBe("50"));
    expect(paramsOf(lastCall()).get("offset")).toBe("0");
  });

  it("shows the posted time in Japan time, and a dash when it is null", async () => {
    view();
    await screen.findByText("Card A");
    expect(screen.getByText(formatDate("2026-10-21T00:30:00Z", "en"))).toBeTruthy();
    const rowB = screen.getByText("Card B").closest("tr");
    expect(rowB?.textContent).toContain("—");
  });
});

describe("acked tab keeps the previous behaviour", () => {
  it("GET has only status_tab, offset and limit=20, no toolbar", async () => {
    view();
    await screen.findByText("Card A");
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    await waitFor(() => expect(lastCall()).toContain("status_tab=ACKED"));
    const p = paramsOf(lastCall());
    expect([...p.keys()].sort()).toEqual(["limit", "offset", "status_tab"]);
    expect(p.get("limit")).toBe("20");
    expect(p.get("offset")).toBe("0");
    expect(screen.queryByTestId("needs-review-fresh-toggle")).toBeNull();
    expect(screen.queryByTestId("needs-review-page-size")).toBeNull();
  });

  it("the date column still shows the Gemini span text path (not posted_at)", async () => {
    view();
    await screen.findByText("Card A");
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    await waitFor(() => expect(lastCall()).toContain("status_tab=ACKED"));
    await screen.findByText("Card A");
    expect(screen.queryByText(formatDate("2026-10-21T00:30:00Z", "en"))).toBeNull();
  });
});
