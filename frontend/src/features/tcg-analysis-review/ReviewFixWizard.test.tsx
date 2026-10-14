import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { availableFixChoices, ReviewFixWizard, type FixChoice } from "./ReviewFixWizard";
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

describe("ReviewFixWizard", () => {
  const renderWizard = (item: ReviewDrawerItem, onRefresh = vi.fn().mockResolvedValue(undefined)) => {
    render(<ReviewFixWizard item={item} onRefresh={onRefresh} />);
    return onRefresh;
  };

  it("asks the question and never offers an exclude choice", () => {
    renderWizard(makeItem({ review_issues: ["PRODUCT_ID_UNRESOLVED", "EXCLUDED"], is_v102: true, review_reason_details: ackable, condition_review: condition }));

    expect(screen.getByRole("group", { name: "What do you want to fix?" })).toBeTruthy();
    expect(screen.getAllByRole("radio").length).toBe(4);
    expect(screen.queryByText(/exclude/i)).toBeNull();
  });

  it("shows only the chosen input and hides the question", () => {
    renderWizard(makeItem({ review_issues: ["PRODUCT_ID_UNRESOLVED"] }));

    fireEvent.click(screen.getByRole("radio", { name: /Reassign to an existing product/ }));

    expect(screen.queryByRole("group", { name: "What do you want to fix?" })).toBeNull();
    expect(screen.getByText("Fixing: Reassign to an existing product")).toBeTruthy();
    expect(screen.getByText("Product").tagName).toBe("LABEL");
    expect(screen.queryByRole("group", { name: "Add “Pika Box” as a search keyword?" })).toBeNull();
  });

  it("returns to the question with Back and drops what was typed", () => {
    renderWizard(makeItem());

    fireEvent.click(screen.getByRole("radio", { name: /Reassign to an existing product/ }));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "abc" } });
    fireEvent.click(screen.getByRole("button", { name: "Back" }));

    expect(screen.getByRole("group", { name: "What do you want to fix?" })).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: /Reassign to an existing product/ }));
    expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("");
  });

  it("acknowledges a reason, shows the notice, returns to the question and reloads", async () => {
    vi.mocked(postReviewAck).mockResolvedValue({});
    const onRefresh = renderWizard(makeItem({ is_v102: true, review_reason_details: ackable }));

    fireEvent.click(screen.getByRole("radio", { name: /Keep as is/ }));
    fireEvent.click(screen.getByRole("button", { name: "Keep as is" }));

    await waitFor(() => expect(onRefresh).toHaveBeenCalledOnce());
    expect(postReviewAck).toHaveBeenCalledWith(expect.objectContaining({ extraction_item_id: "item-1" }), ["product_not_in_master"]);
    expect(screen.getByRole("status").textContent).toContain("Marked as checked");
    expect(screen.getByRole("group", { name: "What do you want to fix?" })).toBeTruthy();
    expect(screen.queryByRole("radio", { name: /Keep as is/ })).toBeNull();
  });
});
