/* eslint-disable local/no-japanese-literal -- 試験の題名と日本語の入力値（画面の文字ではない） */
import { describe, expect, it } from "vitest";
import { DELIVERY_ADDRESS_LINE_MAX, deliveryAddressLineError } from "./addressRules";

describe("deliveryAddressLineError（受け口 test_delivery_address_rule.py と同じ値）", () => {
  it("35文字は通る", () => {
    expect(deliveryAddressLineError("x".repeat(35))).toBeNull();
    expect(DELIVERY_ADDRESS_LINE_MAX).toBe(35);
  });
  it("36文字は maxLength", () => {
    expect(deliveryAddressLineError("x".repeat(36))).toBe("addressRule.maxLength");
  });
  it("日本語・é は ascii", () => {
    expect(deliveryAddressLineError("東京")).toBe("addressRule.ascii");
    expect(deliveryAddressLineError("é")).toBe("addressRule.ascii");
  });
  it("記号と空白は通る", () => {
    expect(deliveryAddressLineError("1-2 Main St, #3")).toBeNull();
  });
  it("null・undefined・空文字は通る", () => {
    expect(deliveryAddressLineError(null)).toBeNull();
    expect(deliveryAddressLineError(undefined)).toBeNull();
    expect(deliveryAddressLineError("")).toBeNull();
  });
  it("改行は ascii", () => {
    expect(deliveryAddressLineError("a\nb")).toBe("addressRule.ascii");
    expect(deliveryAddressLineError("abc\n")).toBe("addressRule.ascii");
  });
  it("文字の種類を先に見る（東京×36）", () => {
    expect(deliveryAddressLineError("東京".repeat(36))).toBe("addressRule.ascii");
  });
});
