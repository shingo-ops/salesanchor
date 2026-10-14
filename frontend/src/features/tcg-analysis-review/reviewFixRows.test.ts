import { describe, expect, it } from "vitest";
import type { AnalysisReviewItem, ConditionReview } from "./ItemComparison";
import { fixRowsOf } from "./reviewFixRows";

const t = (key: string) => (key === "conditionReview.emptyBox" ? "EMPTY-BOX-LABEL" : key);

const review = (over: Partial<ConditionReview> = {}): ConditionReview => ({
  condition_id: "1", review_version: "v", needs_review: true, review_reasons: "condition_unknown", confirmed: false, classification: "none", ...over,
});

function makeItem(system: Record<string, string> = {}, condition_review: ConditionReview | null = null): AnalysisReviewItem {
  return { extraction_item_id: "i", source_message_id: "m", provider: "p", raw_text: "", gemini: {}, system, condition_review };
}

describe("fixRowsOf", () => {
  it("product and work rows are always fixable, with no value unless a person decided the product", () => {
    expect(fixRowsOf(makeItem({ product_id: "PM-1", pid_basis: "EXACT" }), t)).toEqual({
      productId: { scope: "product", value: null },
      work: { scope: "product", value: null },
    });
  });

  it("shows the product title and work name when pid_basis is MANUAL", () => {
    const rows = fixRowsOf(makeItem({ pid_basis: "MANUAL", product_id: "PM-1", product_title: "Title", work_name: "Work" }), t);
    expect(rows.productId).toEqual({ scope: "product", value: "Title" });
    expect(rows.work).toEqual({ scope: "product", value: "Work" });
  });

  it("falls back to the product id when the title is empty, and to no value when the work is empty", () => {
    const rows = fixRowsOf(makeItem({ pid_basis: "MANUAL", product_id: "PM-1", product_title: "" }), t);
    expect(rows.productId.value).toBe("PM-1");
    expect(rows.work.value).toBeNull();
  });

  it("does not treat other bases as a person's decision", () => {
    const rows = fixRowsOf(makeItem({ pid_basis: "MANUAL_RAW_REVIEW:PO_RULES", product_title: "Title" }), t);
    expect(rows.productId.value).toBeNull();
  });

  it("has no state row when the item cannot be condition-reviewed", () => {
    expect(fixRowsOf(makeItem({ condition: "New" }), t).state).toBeUndefined();
  });

  it("state row is fixable when relevant, with a value only for MANUAL_CONDITION_REVIEW", () => {
    const base = { condition: "Used" };
    expect(fixRowsOf(makeItem(base, review()), t).state).toEqual({ scope: "condition", value: null });
    expect(fixRowsOf(makeItem({ ...base, condition_basis: "AUTO" }, review()), t).state).toEqual({ scope: "condition", value: null });
    expect(fixRowsOf(makeItem({ ...base, condition_basis: "MANUAL_CONDITION_REVIEW" }, review()), t).state).toEqual({ scope: "condition", value: "Used" });
  });

  it("shows Empty box in Japanese through the translator", () => {
    const rows = fixRowsOf(makeItem({ condition: "Empty box", condition_basis: "MANUAL_CONDITION_REVIEW" }, review()), t);
    expect(rows.state?.value).toBe("EMPTY-BOX-LABEL");
  });

  it("other rows are not listed (not fixable)", () => {
    const rows = fixRowsOf(makeItem({}, review()), t);
    for (const key of ["name", "quantity", "price", "unit", "memo", "sourcePosition", "saleStatus"]) expect(rows[key]).toBeUndefined();
  });
});
