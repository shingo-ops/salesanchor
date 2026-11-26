import { describe, expect, it } from "vitest";
import { LEAD_STATUS_CODES, MANUAL_LEAD_STATUS_CODES } from "./leadStatus";

describe("MANUAL_LEAD_STATUS_CODES (ADR-1091)", () => {
  it("does not offer existing_customer (it is set automatically)", () => {
    expect(MANUAL_LEAD_STATUS_CODES).not.toContain("existing_customer");
  });

  it("keeps every other status in the same order", () => {
    expect(MANUAL_LEAD_STATUS_CODES).toEqual(LEAD_STATUS_CODES.filter((c) => c !== "existing_customer"));
    expect(MANUAL_LEAD_STATUS_CODES).toHaveLength(LEAD_STATUS_CODES.length - 1);
  });
});
