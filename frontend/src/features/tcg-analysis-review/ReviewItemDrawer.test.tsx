import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ReviewItemDrawer, type ReviewDrawerItem } from "./ReviewItemDrawer";
import { postReviewAck } from "./reviewActions";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("./reviewActions", () => ({
  postProductCorrection: vi.fn(),
  postReviewAck: vi.fn(),
  addSearchKeyword: vi.fn(),
  fetchRegistrationForm: vi.fn(async () => ({ item: { extraction_item_id: "item-1", source_message_id: "msg-1", raw_name: "" }, lookups: {} })),
  checkProductDuplicates: vi.fn(),
  createProduct: vi.fn(),
  searchProductOptions: vi.fn(async () => []),
}));
vi.mock("./ConditionReviewPanel", async () => ({
  ...(await vi.importActual<typeof import("./ConditionReviewPanel")>("./ConditionReviewPanel")),
  ConditionReviewPanel: () => <div data-testid="condition-panel" />,
}));

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
  vi.clearAllMocks();
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

  it("puts the source and comparison heading rows on both panes", () => {
    renderDrawer(withRaw("L1"));

    const sourceHead = document.querySelector(".review-item-source > .review-item-pane-head");
    expect(sourceHead?.textContent).toBe("Source text");
    expect(document.querySelector(".item-comparison .review-item-pane-head h3")?.textContent).toBe("Comparison");
  });

  it("shows no fix area before a row is selected, and no question or product master button", () => {
    renderDrawer(withRaw("L1"));

    expect(document.querySelector(".review-item-fix")).toBeNull();
    expect(screen.queryByText("Select the row you want to fix in the table")).toBeNull();
    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    expect(screen.queryByText("Register or exclude in the product master")).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
  });
});

const rowOf = (label: string) => screen.getByRole("row", { name: new RegExp(`^${label}`) });

describe("ReviewItemDrawer reasons (K1)", () => {
  it("puts the red reasons under the title and above the source and comparison, with no heading", () => {
    renderDrawer({ ...makeItem("pid_unresolved", false), review_reason_details: [{ code: "pid_unresolved", source: "system", fix_stage: "extraction" }] });

    expect(screen.queryByText("Reasons for review")).toBeNull();
    const list = document.querySelector("ul.review-item-reasons") as HTMLElement;
    expect(list.textContent).toContain("Product not identified");
    expect(list.querySelector(".review-item-reasons__text")).not.toBeNull();
    const top = document.querySelector(".review-item-top") as HTMLElement;
    expect(list.compareDocumentPosition(top) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/^Source: /)).toBeTruthy();
  });

  it("shows the no-reasons text when there is no reason", () => {
    renderDrawer({ ...makeItem("pid_unresolved", false), review_reason_details: [] });

    expect(screen.getByText("No reasons")).toBeTruthy();
  });
});

describe("ReviewItemDrawer fix column (K2-K4)", () => {
  const item = (over: Partial<ReviewDrawerItem> = {}): ReviewDrawerItem => ({
    ...makeItem("pid_unresolved", false),
    system: { product_id: "PM-00001", product_title: "Title A", work_name: "Work A", condition: "Box", pid_basis: "MANUAL" },
    review_issues: ["PRODUCT_ID_UNRESOLVED"],
    ...over,
  });

  it("shows the Fix column instead of the Source column", () => {
    renderDrawer(item());

    expect(screen.getByRole("columnheader", { name: "Fix" })).toBeTruthy();
    expect(screen.queryByRole("columnheader", { name: "Source" })).toBeNull();
  });

  it("selects the product row and asks what to fix (two choices)", () => {
    renderDrawer(item());

    fireEvent.click(rowOf("Product ID"));

    expect(rowOf("Product ID").className).toContain("comp-table__row--selected");
    expect(screen.getByRole("group", { name: "What do you want to fix?" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: /Reassign to an existing product/ })).toBeTruthy();
    expect(screen.getByRole("radio", { name: /Register as a new product/ })).toBeTruthy();
    expect(document.querySelector(".review-item-fix")).not.toBeNull();
  });

  it("the work row opens the same product question", () => {
    renderDrawer(item());

    fireEvent.click(rowOf("Series"));

    expect(screen.getByRole("group", { name: "What do you want to fix?" })).toBeTruthy();
  });

  it("the state row opens the condition input directly when the item allows it", () => {
    renderDrawer(item({ condition_review: { condition_id: "1", review_version: "v", needs_review: true, review_reasons: "condition_unknown", confirmed: false, classification: "none" } }));

    fireEvent.click(rowOf("Condition"));

    expect(screen.getByTestId("condition-panel")).toBeTruthy();
    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
  });

  it("a row that cannot be fixed does nothing when clicked, and is marked static", () => {
    renderDrawer(item());

    fireEvent.click(rowOf("Quantity"));
    fireEvent.click(rowOf("Condition"));

    expect(document.querySelector(".review-item-fix")).toBeNull();
    expect(rowOf("Quantity").className).toContain("item-comparison__row--static");
    expect(rowOf("Product ID").className).not.toContain("item-comparison__row--static");
  });

  it("selecting the same row again keeps the selection", () => {
    renderDrawer(item());

    fireEvent.click(rowOf("Product ID"));
    fireEvent.click(rowOf("Product ID"));

    expect(rowOf("Product ID").className).toContain("comp-table__row--selected");
  });
});

describe("ReviewItemDrawer keep as is (K7)", () => {
  const ackable = (codes: string[]): ReviewDrawerItem => ({
    ...makeItem("pid_unresolved", false),
    review_reason_details: codes.map((code) => ({ code, source: "system" as const, fix_stage: "analysis" as const, ackable: true })),
  });

  it("has no button when no reason can be acknowledged", () => {
    renderDrawer({ ...makeItem("pid_unresolved", false), is_v102: false });

    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();
  });

  it("the button under the reasons opens the keep input directly", () => {
    renderDrawer(ackable(["product_not_in_master"]));

    fireEvent.click(screen.getByRole("button", { name: "Keep as is" }));

    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    expect(screen.getAllByRole("button", { name: "Keep as is" }).length).toBe(2);
  });

  it("after the last reason is acknowledged the keep input closes and a notice stays under the reasons", async () => {
    vi.mocked(postReviewAck).mockResolvedValue({});
    renderDrawer(ackable(["product_not_in_master"]));

    fireEvent.click(screen.getByRole("button", { name: "Keep as is" }));
    const fix = document.querySelector(".review-item-fix") as HTMLElement;
    fireEvent.click(within(fix).getByRole("button", { name: "Keep as is" }));

    await waitFor(() => expect(screen.getByText(/Marked as checked/)).toBeTruthy());
    expect(postReviewAck).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();
    expect(document.querySelector(".review-item-fix")).toBeNull();
    const block = document.querySelector(".review-item-reasons-block") as HTMLElement;
    expect(block.textContent).toContain("Marked as checked");

    fireEvent.click(rowOf("Product ID"));
    expect(document.querySelector(".review-item-reasons-block")?.textContent).not.toContain("Marked as checked");
  });
});

describe("ReviewItemDrawer removedFromList (K5)", () => {
  it("shows the removed notice only when asked", () => {
    const { rerender } = render(<ReviewItemDrawer item={makeItem("pid_unresolved", false)} onClose={() => undefined} onRefresh={async () => undefined} />);
    expect(screen.queryByText("This item is no longer in the review list")).toBeNull();

    rerender(<ReviewItemDrawer item={makeItem("pid_unresolved", false)} removedFromList onClose={() => undefined} onRefresh={async () => undefined} />);
    expect(screen.getByText("This item is no longer in the review list")).toBeTruthy();
  });

  it("explains an excluded item in plain words under the reason, using the sale status", () => {
    renderDrawer({ ...makeItem("excluded", false), system: { status: "Sold out" } });

    expect(screen.getByText(/Read as "Sold out", so this item is kept out of stock/)).toBeTruthy();
  });

  it("uses the no-status wording when the sale status is empty", () => {
    renderDrawer(makeItem("excluded", false));

    expect(screen.getByText(/Kept out of stock because of its sale status/)).toBeTruthy();
  });

  it("does not show the excluded explanation for other reasons", () => {
    renderDrawer(makeItem("pid_unresolved", false));

    expect(screen.queryByText(/kept out of stock/i)).toBeNull();
  });
});
