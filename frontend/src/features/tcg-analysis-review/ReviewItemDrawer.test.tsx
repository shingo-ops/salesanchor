import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ReviewItemDrawer, type ReviewDrawerItem } from "./ReviewItemDrawer";
import { postReviewAck, postReviewAckRevoke } from "./reviewActions";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("./reviewActions", () => ({
  postProductCorrection: vi.fn(),
  postReviewAck: vi.fn(),
  postReviewAckRevoke: vi.fn(),
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

describe("ReviewItemDrawer keep as is (confirm popup)", () => {
  const ackable = (codes: string[]): ReviewDrawerItem => ({
    ...makeItem("pid_unresolved", false),
    review_reason_details: codes.map((code) => ({ code, source: "system" as const, fix_stage: "analysis" as const, ackable: true })),
  });
  const keepButton = () => screen.getByRole("button", { name: "Keep as is" });
  // Modal の × も名前が「Close」なので、下のボタン列から探す
  const closeButton = () => within(popup().querySelector(".form-actions") as HTMLElement).getByRole("button", { name: "Close" });
  const popup = () => screen.getByRole("dialog", { name: "Keep as it is?" });
  const render2 = (item: ReviewDrawerItem, onClose = vi.fn(), onRefresh = vi.fn().mockResolvedValue(undefined)) => {
    render(<ReviewItemDrawer item={item} onClose={onClose} onRefresh={onRefresh} />);
    return { onClose, onRefresh };
  };

  it("has no button when no reason can be acknowledged", () => {
    renderDrawer({ ...makeItem("pid_unresolved", false), is_v102: false });

    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();
  });

  it("K1: one press opens a popup with the message, the reasons and two buttons; nothing is saved yet", () => {
    render2(ackable(["product_not_in_master"]));

    fireEvent.click(keepButton());

    expect(within(popup()).getByText(/will be marked as checked/)).toBeTruthy();
    expect(within(popup()).getByText("Not in the product master")).toBeTruthy();
    expect(within(popup()).getByRole("button", { name: "Keep" })).toBeTruthy();
    expect(closeButton()).toBeTruthy();
    expect(postReviewAck).not.toHaveBeenCalled();
  });

  it("K2: Close hides the popup and saves nothing", () => {
    render2(ackable(["product_not_in_master"]));

    fireEvent.click(keepButton());
    fireEvent.click(closeButton());

    expect(screen.queryByRole("dialog", { name: "Keep as it is?" })).toBeNull();
    expect(postReviewAck).not.toHaveBeenCalled();
  });

  it("K3: Keep saves once with all remaining codes, shows the notice and reloads", async () => {
    vi.mocked(postReviewAck).mockResolvedValue({});
    const { onRefresh } = render2(ackable(["product_not_in_master", "condition_unknown"]));

    fireEvent.click(keepButton());
    fireEvent.click(within(popup()).getByRole("button", { name: "Keep" }));

    await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1));
    expect(postReviewAck).toHaveBeenCalledTimes(1);
    expect(vi.mocked(postReviewAck).mock.calls[0][1]).toEqual(["product_not_in_master", "condition_unknown"]);
    expect(screen.queryByRole("dialog", { name: "Keep as it is?" })).toBeNull();
    expect(screen.getByText(/Marked as checked/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Keep as is" })).toBeNull();

    fireEvent.click(rowOf("Product ID"));
    expect(document.querySelector(".review-item-reasons-block")?.textContent).not.toContain("Marked as checked");
  });

  it("K4: only one Keep as is button exists, even after pressing it", () => {
    render2(ackable(["product_not_in_master"]));

    expect(screen.getAllByRole("button", { name: "Keep as is" }).length).toBe(1);
    fireEvent.click(keepButton());
    expect(screen.getAllByRole("button", { name: "Keep as is" }).length).toBe(1);
    expect(document.querySelector(".review-item-fix")).toBeNull();
  });

  it("K5: while saving the button is disabled", async () => {
    let finish: (value: object) => void = () => undefined;
    vi.mocked(postReviewAck).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render2(ackable(["product_not_in_master"]));

    fireEvent.click(keepButton());
    fireEvent.click(within(popup()).getByRole("button", { name: "Keep" }));

    await waitFor(() => expect((keepButton() as HTMLButtonElement).disabled).toBe(true));
    fireEvent.click(keepButton());
    expect(screen.queryByRole("dialog", { name: "Keep as it is?" })).toBeNull();
    finish({});
    await waitFor(() => expect(screen.getByText(/Marked as checked/)).toBeTruthy());
    expect(postReviewAck).toHaveBeenCalledTimes(1);
  });

  it("a failed save shows a warning, leaves the button, and can be pressed again", async () => {
    vi.mocked(postReviewAck).mockRejectedValueOnce(new Error("boom")).mockResolvedValueOnce({});
    render2(ackable(["product_not_in_master"]));

    fireEvent.click(keepButton());
    fireEvent.click(within(popup()).getByRole("button", { name: "Keep" }));

    await waitFor(() => expect(screen.getByText("Could not mark as checked. Please try again")).toBeTruthy());
    expect((keepButton() as HTMLButtonElement).disabled).toBe(false);

    fireEvent.click(keepButton());
    expect(screen.queryByText("Could not mark as checked. Please try again")).toBeNull();
    fireEvent.click(within(popup()).getByRole("button", { name: "Keep" }));
    await waitFor(() => expect(screen.getByText(/Marked as checked/)).toBeTruthy());
    expect(postReviewAck).toHaveBeenCalledTimes(2);
  });

  it("Esc while the popup is open closes only the popup, not the drawer", () => {
    const { onClose } = render2(ackable(["product_not_in_master"]));

    fireEvent.click(keepButton());
    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog", { name: "Keep as it is?" })).toBeNull();
    expect(onClose).not.toHaveBeenCalled();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
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

describe("ReviewItemDrawer revoke", () => {
  const ackable = (): ReviewDrawerItem => makeItem("product_not_in_master", false);
  const undoPopup = () => screen.getByRole("dialog", { name: 'Undo "checked"?' });
  const confirmUndo = () => fireEvent.click(within(undoPopup()).getByRole("button", { name: "Undo" }));
  const keepAndConfirm = () => {
    fireEvent.click(screen.getByRole("button", { name: "Keep as is" }));
    fireEvent.click(within(screen.getByRole("dialog", { name: "Keep as it is?" })).getByRole("button", { name: "Keep" }));
  };

  it("K1: after keeping, Undo opens a popup, revoke is posted once and the revoked notice replaces the old one", async () => {
    vi.mocked(postReviewAck).mockResolvedValue({});
    vi.mocked(postReviewAckRevoke).mockResolvedValue({});
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<ReviewItemDrawer item={ackable()} onClose={() => undefined} onRefresh={onRefresh} />);

    keepAndConfirm();
    await screen.findByText(/Marked as checked/);
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(postReviewAckRevoke).not.toHaveBeenCalled();
    confirmUndo();

    expect(await screen.findByText("Undone. Re-running the analysis")).toBeTruthy();
    expect(postReviewAckRevoke).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/Marked as checked/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
    expect(onRefresh).toHaveBeenCalledTimes(2);
  });

  it("a failed revoke shows the failure notice and keeps the Undo button", async () => {
    vi.mocked(postReviewAck).mockResolvedValue({});
    vi.mocked(postReviewAckRevoke).mockRejectedValue(new Error("boom"));
    render(<ReviewItemDrawer item={ackable()} onClose={() => undefined} onRefresh={async () => undefined} />);

    keepAndConfirm();
    await screen.findByText(/Marked as checked/);
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    confirmUndo();

    expect(await screen.findByText("Could not undo. Please try again")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Undo" })).toBeTruthy();
  });

  it("K1/K5: keep -> undo -> keep again shows Undo again and only one notice", async () => {
    vi.mocked(postReviewAck).mockResolvedValue({});
    vi.mocked(postReviewAckRevoke).mockResolvedValue({});
    render(<ReviewItemDrawer item={ackable()} onClose={() => undefined} onRefresh={async () => undefined} />);

    keepAndConfirm();
    await screen.findByText(/Marked as checked/);
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    confirmUndo();
    await screen.findByText("Undone. Re-running the analysis");

    keepAndConfirm();
    await screen.findByText(/Marked as checked/);
    expect(screen.queryByText("Undone. Re-running the analysis")).toBeNull();
    expect(screen.getAllByRole("button", { name: "Undo" }).length).toBe(1);
  });

  it("K2: ackedView shows the checked notice and the revoke button; without it neither appears", () => {
    const { unmount } = render(<ReviewItemDrawer item={ackable()} onClose={() => undefined} onRefresh={async () => undefined} ackedView />);
    expect(screen.getByText("This item is marked as checked")).toBeTruthy();
    expect(screen.getByRole("button", { name: 'Undo "checked"' })).toBeTruthy();
    unmount();
    render(<ReviewItemDrawer item={ackable()} onClose={() => undefined} onRefresh={async () => undefined} />);
    expect(screen.queryByText("This item is marked as checked")).toBeNull();
    expect(screen.queryByRole("button", { name: 'Undo "checked"' })).toBeNull();
  });

  it("revokes from the acked view and swaps the notice", async () => {
    vi.mocked(postReviewAckRevoke).mockResolvedValue({});
    render(<ReviewItemDrawer item={ackable()} onClose={() => undefined} onRefresh={async () => undefined} ackedView />);
    fireEvent.click(screen.getByRole("button", { name: 'Undo "checked"' }));
    confirmUndo();
    expect(await screen.findByText("Undone. Re-running the analysis")).toBeTruthy();
    expect(screen.queryByText("This item is marked as checked")).toBeNull();
  });

  it("after revoking in the acked view, selecting a row does not bring the checked notice back", async () => {
    vi.mocked(postReviewAckRevoke).mockResolvedValue({});
    const item: ReviewDrawerItem = {
      ...ackable(),
      system: { product_id: "PM-00001", product_title: "Title A", work_name: "Work A", condition: "Box", pid_basis: "MANUAL" },
      review_issues: ["PRODUCT_ID_UNRESOLVED"],
    };
    render(<ReviewItemDrawer item={item} onClose={() => undefined} onRefresh={async () => undefined} ackedView />);
    fireEvent.click(screen.getByRole("button", { name: 'Undo "checked"' }));
    confirmUndo();
    await screen.findByText("Undone. Re-running the analysis");
    fireEvent.click(rowOf("Product ID"));
    expect(rowOf("Product ID").className).toContain("comp-table__row--selected");
    expect(screen.queryByText("This item is marked as checked")).toBeNull();
  });

  it("Esc while the revoke popup is open closes only the popup, not the drawer", () => {
    const onClose = vi.fn();
    render(<ReviewItemDrawer item={ackable()} onClose={onClose} onRefresh={async () => undefined} ackedView />);
    fireEvent.click(screen.getByRole("button", { name: 'Undo "checked"' }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: 'Undo "checked"?' })).toBeNull();
    expect(onClose).not.toHaveBeenCalled();
  });
});
