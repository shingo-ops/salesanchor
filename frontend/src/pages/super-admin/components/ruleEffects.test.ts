import { describe, expect, it } from "vitest";
import {
  CONTEXT_EFFECTS,
  defaultMatchTypeFor,
  effectAfterCanonicalChange,
  isContextEffect,
} from "./ruleEffects";

describe("ruleEffects", () => {
  it("treats only the pre-order clue effects as context", () => {
    expect(CONTEXT_EFFECTS).toEqual(["RELEASE_AHEAD", "DATE_AHEAD", "HEADING"]);
    expect(isContextEffect("HEADING")).toBe(true);
    expect(isContextEffect("OUTPUT")).toBe(false);
    expect(isContextEffect("EXCLUDE")).toBe(false);
  });

  it("keeps LITERAL as the default match type for the existing effects", () => {
    expect(defaultMatchTypeFor("OUTPUT")).toBe("LITERAL");
    expect(defaultMatchTypeFor("EXCLUDE")).toBe("LITERAL");
    expect(defaultMatchTypeFor("RELEASE_AHEAD")).toBe("RELEASE");
    expect(defaultMatchTypeFor("DATE_AHEAD")).toBe("REGEX");
    expect(defaultMatchTypeFor("HEADING")).toBe("REGEX");
  });

  it("does not change the current effect when a canonical has several effects", () => {
    const options = [
      { canonical: "Pre-order", effect: "OUTPUT" },
      { canonical: "Pre-order", effect: "HEADING" },
      { canonical: "Sold out", effect: "EXCLUDE" },
    ];
    expect(effectAfterCanonicalChange(options, "Pre-order", "HEADING")).toBe("HEADING");
    expect(effectAfterCanonicalChange(options, "Pre-order", "OUTPUT")).toBe("OUTPUT");
    expect(effectAfterCanonicalChange(options, "Sold out", "OUTPUT")).toBe("EXCLUDE");
    expect(effectAfterCanonicalChange(options, "Unknown", "OUTPUT")).toBe("OUTPUT");
  });
});
