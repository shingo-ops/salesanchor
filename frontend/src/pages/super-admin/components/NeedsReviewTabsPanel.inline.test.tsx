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
  system: { product_id: "", product_title: "", product_uuid: "" },
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
  vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 1 });
});
afterEach(() => cleanup());

describe("production tab inline fix column", () => {
  it("shows the fix controls only on the v102 row", async () => {
    view();
    await screen.findByText("Card V102");
    expect(screen.getByRole("columnheader", { name: "Fix here" })).toBeTruthy();
    expect(screen.getAllByRole("combobox")).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /^Keep as is: / })).toHaveLength(1);
  });

  it("saves keep-as-is from the row without opening the drawer, and keeps the table while reloading", async () => {
    let releaseReload: (value: ReturnType<typeof response>) => void = () => undefined;
    view();
    await screen.findByText("Card V102");
    vi.mocked(api.get).mockImplementationOnce(
      () => new Promise((resolve) => { releaseReload = resolve as typeof releaseReload; }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Keep as is: Card V102" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tcg/items/v102-item/review-ack", {
      source_message_id: "source-v102-item",
      codes: ["product_not_in_master"],
    }));
    await waitFor(() => expect(vi.mocked(api.get).mock.calls.filter(([p]) => String(p).startsWith("/tcg/analysis-results")).length).toBe(2));
    // 読み直しの途中でも表は消えない・件を開く画面は出ない
    expect(screen.getByText("Card V102")).toBeTruthy();
    expect(screen.getByText("Card V6")).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
    releaseReload(response([makeItem("v102-item", "Card V102", true), makeItem("v6-item", "Card V6", false)]));
    expect(await screen.findByText("Saved")).toBeTruthy();
  });
});
