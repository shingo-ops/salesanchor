import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { availableFixChoices, choicesForScope, ReviewFixWizard, type FixChoice, type FixScope } from "./ReviewFixWizard";
import type { ReviewDrawerItem } from "./ReviewItemDrawer";
import { postReviewAck } from "./reviewActions";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(async () => []), post: vi.fn() },
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

const condition = {
  condition_id: "c1",
  review_version: "v1",
  needs_review: true,
  review_reasons: "condition_unknown",
  confirmed: false,
  classification: "none",
};

function makeItem(over: Partial<ReviewDrawerItem> = {}): ReviewDrawerItem {
  return {
    extraction_item_id: "item-1",
    source_message_id: "msg-1",
    provider: "Supplier A",
    raw_text: "",
    gemini: { name: "Pika Box" },
    system: {},
    review_issues: [],
    review_reason_details: [],
    is_v102: false,
    ...over,
  };
}

const ackable = [{ code: "product_not_in_master", source: "system" as const, fix_stage: "analysis" as const, ackable: true }];

describe("availableFixChoices", () => {
  const cases: Array<[string, Partial<ReviewDrawerItem>, FixChoice[]]> = [
    ["a plain v6 item only reassigns", {}, ["reassign"]],
    ["PRODUCT_ID_UNRESOLVED adds register", { review_issues: ["PRODUCT_ID_UNRESOLVED"] }, ["reassign", "register"]],
    ["PRODUCT_MASTER_UNREGISTERED adds register", { review_issues: ["PRODUCT_MASTER_UNREGISTERED"] }, ["reassign", "register"]],
    ["a resolved product does not offer register", { review_issues: ["UNIT_UNRESOLVED"] }, ["reassign"]],
    ["a condition review adds condition", { condition_review: condition }, ["reassign", "condition"]],
    ["v102 with an ackable reason adds keep", { is_v102: true, review_reason_details: ackable }, ["reassign", "keep"]],
    ["v6 with an ackable reason does not add keep", { is_v102: false, review_reason_details: ackable }, ["reassign"]],
    [
      "v102 with only a non-ackable reason does not add keep",
      { is_v102: true, review_reason_details: [{ code: "condition_unknown", source: "system" as const, fix_stage: "analysis" as const, ackable: false }] },
      ["reassign"],
    ],
    [
      "everything at once keeps the order of the table",
      { is_v102: true, review_reason_details: ackable, review_issues: ["PRODUCT_ID_UNRESOLVED"], condition_review: condition },
      ["reassign", "register", "condition", "keep"],
    ],
  ];

  it.each(cases)("%s", (_name, over, expected) => {
    expect(availableFixChoices(makeItem(over), [])).toEqual(expected);
  });

  it("drops keep once every ackable reason is acknowledged", () => {
    expect(availableFixChoices(makeItem({ is_v102: true, review_reason_details: ackable }), ["product_not_in_master"])).toEqual(["reassign"]);
  });
});

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("choicesForScope", () => {
  const all = { is_v102: true, review_reason_details: ackable, review_issues: ["PRODUCT_ID_UNRESOLVED"], condition_review: condition };
  const cases: Array<[FixScope, string[], FixChoice[]]> = [
    ["product", [], ["reassign", "register"]],
    ["condition", [], ["condition"]],
    ["keep", [], ["keep"]],
    ["keep", ["product_not_in_master"], []],
  ];

  it.each(cases)("%s (acked %j) -> %j", (scope, acked, expected) => {
    expect(choicesForScope(makeItem(all), scope, acked)).toEqual(expected);
  });

  it("product is only reassign when the product is already resolved", () => {
    expect(choicesForScope(makeItem(), "product", [])).toEqual(["reassign"]);
  });

  it("condition is empty when the item has no condition review", () => {
    expect(choicesForScope(makeItem(), "condition", [])).toEqual([]);
  });
});

describe("ReviewFixWizard", () => {
  const renderWizard = (
    item: ReviewDrawerItem,
    scope: FixScope,
    { ackedCodes = [] as string[], onAcked = vi.fn(), onRefresh = vi.fn().mockResolvedValue(undefined) } = {},
  ) => {
    render(<ReviewFixWizard item={item} scope={scope} ackedCodes={ackedCodes} onAcked={onAcked} onRefresh={onRefresh} />);
    return { onAcked, onRefresh };
  };

  it("product scope with two choices asks the question and never offers an exclude choice", () => {
    renderWizard(makeItem({ review_issues: ["PRODUCT_ID_UNRESOLVED", "EXCLUDED"], is_v102: true, review_reason_details: ackable, condition_review: condition }), "product");

    expect(screen.getByRole("group", { name: "What do you want to fix?" })).toBeTruthy();
    expect(screen.getAllByRole("radio").length).toBe(2);
    expect(screen.queryByText(/exclude/i)).toBeNull();
  });

  it("product scope with one choice skips the question and the Back button", () => {
    renderWizard(makeItem(), "product");

    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
    expect(screen.getByText("Product").tagName).toBe("LABEL");
  });

  it("condition scope shows the condition input directly, without the question", () => {
    renderWizard(makeItem({ condition_review: condition }), "condition");

    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
    expect(screen.queryByText("Product")).toBeNull();
  });

  it("shows only the chosen input and hides the question", () => {
    renderWizard(makeItem({ review_issues: ["PRODUCT_ID_UNRESOLVED"] }), "product");

    fireEvent.click(screen.getByRole("radio", { name: /Reassign to an existing product/ }));

    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    expect(screen.getByText("Fixing: Reassign to an existing product")).toBeTruthy();
    expect(screen.getByText("Product").tagName).toBe("LABEL");
  });

  it("returns to the question with Back and drops what was typed", () => {
    renderWizard(makeItem({ review_issues: ["PRODUCT_ID_UNRESOLVED"] }), "product");

    fireEvent.click(screen.getByRole("radio", { name: /Reassign to an existing product/ }));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "abc" } });
    fireEvent.click(screen.getByRole("button", { name: "Back" }));

    expect(screen.getByRole("group", { name: "What do you want to fix?" })).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: /Reassign to an existing product/ }));
    expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("");
  });

  it("says there is nothing to fix when the scope has no choice", () => {
    renderWizard(makeItem(), "condition");

    expect(screen.getByText("Nothing to fix on this row")).toBeTruthy();
  });

  it("keep scope acknowledges a reason, tells the parent, shows the notice and reloads", async () => {
    vi.mocked(postReviewAck).mockResolvedValue({});
    const { onAcked, onRefresh } = renderWizard(makeItem({ is_v102: true, review_reason_details: ackable }), "keep");

    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Keep as is" }));

    await waitFor(() => expect(onRefresh).toHaveBeenCalledOnce());
    expect(postReviewAck).toHaveBeenCalledWith(expect.objectContaining({ extraction_item_id: "item-1" }), ["product_not_in_master"]);
    expect(onAcked).toHaveBeenCalledWith(["product_not_in_master"]);
    expect(screen.getByRole("status").textContent).toContain("Marked as checked");
  });
});
