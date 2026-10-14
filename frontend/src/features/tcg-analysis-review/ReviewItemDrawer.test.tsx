import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ReviewItemDrawer, type ReviewDrawerItem } from "./ReviewItemDrawer";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("./ItemComparison", () => ({
  ItemComparison: ({ heading }: { heading?: string }) => <div data-testid="comparison-heading">{heading}</div>,
}));
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

describe("ReviewItemDrawer layout", () => {
  const withRaw = (span: string): ReviewDrawerItem => ({
    ...makeItem("pid_unresolved", false),
    raw_text: "line one\nline two\nline three\nline four",
    gemini: { span },
  });

  it("shows the source text with the block range marked", () => {
    renderDrawer(withRaw("L2-3"));

    expect(screen.getByText("Source text")).toBeTruthy();
    expect(screen.getByText("line two")).toBeTruthy();
    const marked = Array.from(document.querySelectorAll('[data-range="block"]')).map((el) => el.getAttribute("data-line-number"));
    expect(marked).toEqual(["2", "3"]);
  });

  it("marks nothing when the span cannot be read", () => {
    renderDrawer(withRaw("unknown"));

    expect(document.querySelectorAll('[data-range="block"]').length).toBe(0);
  });

  it("opens the drawer in the wide size", () => {
    renderDrawer(withRaw("L1"));

    expect(screen.getByTestId("supplier-drawer").className).toContain("comp-drawer-panel--wide");
  });

  it("shows the fix heading", () => {
    renderDrawer(withRaw("L1"));

    expect(screen.getByText("Fix")).toBeTruthy();
  });

  it("puts the source and comparison heading rows on both panes", () => {
    renderDrawer(withRaw("L1"));

    const sourceHead = document.querySelector(".review-item-source > .review-item-pane-head");
    expect(sourceHead?.textContent).toBe("Source text");
    expect(screen.getByTestId("comparison-heading").textContent).toBe("Comparison");
  });

  it("shows the labelled product form with a disabled reassign button in the fix section", () => {
    renderDrawer(withRaw("L1"));

    expect(screen.getByText("Product").tagName).toBe("LABEL");
    expect((screen.getByRole("button", { name: "Reassign to this product" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Register or exclude in the product master")).toBeTruthy();
  });
});
