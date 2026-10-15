import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { api } from "../../lib/api";
import { availableFixChoices, choicesForScope, ReviewFixWizard, type FixChoice, type FixScope } from "./ReviewFixWizard";
import type { ReviewDrawerItem } from "./ReviewItemDrawer";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(async () => []), post: vi.fn() },
  ApiError: class extends Error { status: number; constructor(message: string, status: number) { super(message); this.status = status; } },
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
    ["a v102 item adds value", { is_v102: true }, ["reassign", "value"]],
    ["a v102 item with a condition review (not empty-box) adds condition and value", { is_v102: true, condition_review: { ...condition, review_reasons: "pid_unresolved" } }, ["reassign", "condition", "value"]],
    ["an ackable reason does not add a choice (keep lives in the drawer)", { is_v102: true, review_reason_details: ackable }, ["reassign", "value"]],
    [
      "everything at once keeps the order of the table",
      { is_v102: true, review_reason_details: ackable, review_issues: ["PRODUCT_ID_UNRESOLVED"], condition_review: condition },
      ["reassign", "register", "condition", "value"],
    ],
  ];

  it.each(cases)("%s", (_name, over, expected) => {
    expect(availableFixChoices(makeItem(over))).toEqual(expected);
  });
});

beforeEach(async () => {
  vi.clearAllMocks();
  vi.mocked(api.get).mockResolvedValue([]);
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("choicesForScope", () => {
  const all = { is_v102: true, review_reason_details: ackable, review_issues: ["PRODUCT_ID_UNRESOLVED"], condition_review: condition };
  const cases: Array<[FixScope, FixChoice[]]> = [
    ["product", ["reassign", "register"]],
    ["condition", ["condition"]],
    ["value", ["value"]],
  ];

  it.each(cases)("%s -> %j", (scope, expected) => {
    expect(choicesForScope(makeItem(all), scope)).toEqual(expected);
  });

  it("product is only reassign when the product is already resolved", () => {
    expect(choicesForScope(makeItem(), "product")).toEqual(["reassign"]);
  });

  it("condition is empty when the item has no condition review", () => {
    expect(choicesForScope(makeItem(), "condition")).toEqual([]);
  });
});

describe("ReviewFixWizard", () => {
  const renderWizard = (item: ReviewDrawerItem, scope: FixScope, { onRefresh = vi.fn().mockResolvedValue(undefined), rowKey = "" } = {}) => {
    render(<ReviewFixWizard item={item} scope={scope} rowKey={rowKey} onRefresh={onRefresh} />);
    return { onRefresh };
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

  it("K3: value scope shows the value form directly for the pressed row", async () => {
    vi.mocked(api.get).mockResolvedValue({ units: ["BOX"], statuses: ["Sold out"] });
    renderWizard(makeItem({ is_v102: true, system: { quantity: "4" } }), "value", { rowKey: "quantity" });

    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    expect((screen.getByLabelText("Quantity") as HTMLInputElement).value).toBe("4");
  });

  it("R1: the condition scope passes fromWizard so a non empty-box item still gets the select, without the confirm button", async () => {
    vi.mocked(api.get).mockResolvedValue([{ id: "n", code: "CN1", canonical: "Sealed box" }]);
    renderWizard(makeItem({ is_v102: true, system: { condition: "New" }, condition_review: { ...condition, review_reasons: "pid_unresolved" } }), "condition");

    await screen.findByRole("option", { name: "Sealed box" });
    expect(screen.getByRole("button", { name: "Save selected condition" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Confirm empty box" })).toBeNull();
  });

  it("says there is nothing to fix when the scope has no choice", () => {
    renderWizard(makeItem(), "condition");

    expect(screen.getByText("Nothing to fix on this row")).toBeTruthy();
  });
});
