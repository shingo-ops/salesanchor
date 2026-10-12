import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ReviewItemDrawer, type ReviewDrawerItem } from "./ReviewItemDrawer";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("./ItemComparison", () => ({ ItemComparison: () => null }));
vi.mock("./ConditionReviewPanel", () => ({ ConditionReviewPanel: () => null }));
vi.mock("./ProductMasterDrawer", () => ({ ProductMasterDrawer: () => null }));

const suspect = { gap_lines: [14, 15], candidates: [{ product_id: "1001", name: "Product A" }] };

function makeItem(code: string, withSuspect = true): ReviewDrawerItem {
  return {
    extraction_item_id: "item-1", source_message_id: "msg-1", provider: "Supplier A", raw_text: "",
    gemini: {}, system: {}, is_v102: true,
    review_reason_details: [{ code, source: "system", fix_stage: "extraction" }],
    ...(withSuspect ? { gap_suspect: suspect } : {}),
  };
}

const renderDrawer = (item: ReviewDrawerItem) =>
  render(<ReviewItemDrawer item={item} onClose={() => undefined} onRefresh={async () => undefined} />);

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("ReviewItemDrawer gap suspect", () => {
  it("shows gap lines and candidates when the reason is gemini_gap_suspect", () => {
    renderDrawer(makeItem("gemini_gap_suspect"));

    expect(screen.getByText(/Gap lines: L14.*L15/)).toBeTruthy();
    expect(screen.getByText("Candidates: Product A")).toBeTruthy();
  });

  it("does not show them for another reason code even if gap_suspect is present", () => {
    renderDrawer(makeItem("pid_unresolved"));

    expect(screen.queryByText(/Gap lines/)).toBeNull();
    expect(screen.queryByText(/Candidates/)).toBeNull();
  });

  it("does not show them when gap_suspect is missing", () => {
    renderDrawer(makeItem("gemini_gap_suspect", false));

    expect(screen.queryByText(/Gap lines/)).toBeNull();
  });
});
