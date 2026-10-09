import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import i18n from "../../../i18n";
import NeedsReviewTabsPanel from "./NeedsReviewTabsPanel";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

const makeItem = (id: string, name: string, isV102: boolean) => ({
  extraction_item_id: id,
  source_message_id: `source-${id}`,
  provider: "Supplier A",
  raw_text: "",
  gemini: { name, quantity: "1", price: "100", unit: "", state: "", memo: "", span: "L1-1" },
  system: { product_id: "", product_title: "" },
  review_issues: [],
  is_v102: isV102,
  condition_review: null,
  review_reason_details: [{ code: "product_not_in_master", source: "system", fix_stage: "analysis" }],
});

const response = (items: ReturnType<typeof makeItem>[]) => ({
  items, total: items.length, item_total: items.length, offset: 0, limit: 20, providers: [], works: [],
});

const view = () => render(<MemoryRouter><NeedsReviewTabsPanel /></MemoryRouter>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockResolvedValue(response([makeItem("v102-item", "Card V102", true), makeItem("v6-item", "Card V6", false)]));
});
afterEach(() => cleanup());

describe("production tab row drawer", () => {
  it("opens a drawer with the item comparison and the product correction button when a row is clicked", async () => {
    view();
    fireEvent.click(await screen.findByText("Card V6"));
    const dialog = await screen.findByRole("dialog");
    expect(dialog.textContent).toContain("Item to review");
    expect(screen.getByRole("button", { name: "Edit" })).toBeTruthy();
  });

  it("shows the keep-as-is button only for a v102 item and posts the reason code", async () => {
    vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 1 });
    view();
    fireEvent.click(await screen.findByText("Card V102"));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: "Keep as is" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
    expect(api.post).toHaveBeenCalledWith("/tcg/items/v102-item/review-ack", {
      source_message_id: "source-v102-item",
      codes: ["product_not_in_master"],
    });
    expect(await screen.findByText("Marked as checked. Re-running the analysis")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();
    // 一覧を読み直した（最初の読み込み＋ack 後）
    await waitFor(() => expect(vi.mocked(api.get).mock.calls.filter(([p]) => String(p).startsWith("/tcg/analysis-results")).length).toBe(2));
  });

  it("does not show the keep-as-is button for a v6 item", async () => {
    view();
    fireEvent.click(await screen.findByText("Card V6"));
    await screen.findByRole("dialog");
    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();
    expect(api.post).not.toHaveBeenCalled();
  });
});

describe("posts tab", () => {
  it("is added after the existing tabs and loads the v102 post list", async () => {
    vi.mocked(api.get).mockImplementation((path: string) =>
      Promise.resolve(path.startsWith("/tcg/v102/posts") ? { items: [], total: 0, limit: 20, offset: 0 } : response([])),
    );
    view();
    fireEvent.click(await screen.findByRole("tab", { name: "Posts" }));
    await waitFor(() => expect(vi.mocked(api.get).mock.calls.some(([p]) => String(p).startsWith("/tcg/v102/posts"))).toBe(true));
  });
});
