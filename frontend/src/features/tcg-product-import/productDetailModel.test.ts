import { describe, expect, it } from "vitest";
import { ApiError } from "../../lib/api";
import { requiredFieldsMessage } from "./productDetailModel";

// t のかわり: キーと引数をそのまま文字にする（キーが無い項目名はキーを返す）
const labels: Record<string, string> = {
  "productDetail.english_title": "EN", "productDetail.mark": "MARK", "productDetail.japanese_title": "JA",
  "reviewItem.wizard.register.listSeparator": "|",
};
const t = ((key: string, opts?: { fields?: string }) => opts?.fields !== undefined ? `${key}:${opts.fields}` : labels[key] ?? key) as never;

describe("requiredFieldsMessage", () => {
  it("maps a missing-fields code to the register message with joined labels", () => {
    expect(requiredFieldsMessage(new ApiError("REQUIRED_FIELDS_MISSING:name_en,mark", 422, null), t))
      .toBe("productDetail.requiredFieldsMissing:EN|MARK");
  });
  it("maps a cleared-fields code to the save message", () => {
    expect(requiredFieldsMessage(new ApiError("REQUIRED_FIELDS_CLEARED:name", 422, null), t))
      .toBe("productDetail.requiredFieldsCleared:JA");
  });
  it("shows an unknown field name as it is", () => {
    expect(requiredFieldsMessage(new ApiError("REQUIRED_FIELDS_MISSING:foo", 422, null), t))
      .toBe("productDetail.requiredFieldsMissing:foo");
  });
  it("returns null for other failures", () => {
    expect(requiredFieldsMessage(new ApiError("REQUIRED_FIELDS_MISSING:mark", 409, null), t)).toBeNull();
    expect(requiredFieldsMessage(new ApiError("PRODUCT_FORMAT_INVALID", 422, null), t)).toBeNull();
    expect(requiredFieldsMessage(new Error("REQUIRED_FIELDS_MISSING:mark"), t)).toBeNull();
  });
});
