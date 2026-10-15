import { describe, expect, it } from "vitest";
import { conditionBadgeVariant } from "./conditionBadge";

describe("conditionBadgeVariant", () => {
  it("maps exact (trimmed, case-insensitive) values", () => {
    expect(conditionBadgeVariant("sealed")).toBe("success");
    expect(conditionBadgeVariant("  Sealed ")).toBe("success");
    expect(conditionBadgeVariant("DAMAGED")).toBe("danger");
    expect(conditionBadgeVariant("case")).toBe("info");
  });
  it("falls back to neutral for anything else (no partial match)", () => {
    expect(conditionBadgeVariant("sealed box")).toBe("neutral");
    expect(conditionBadgeVariant("New")).toBe("neutral");
    expect(conditionBadgeVariant("")).toBe("neutral");
    expect(conditionBadgeVariant(null)).toBe("neutral");
  });
});
