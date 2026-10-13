import { describe, expect, it } from "vitest";
import { parseSourceLineRange } from "./sourceRawNavigation";

describe("parseSourceLineRange", () => {
  it("reads a range", () => {
    expect(parseSourceLineRange("L12-15")).toEqual({ start: 12, end: 15 });
  });
  it("reads a single line as a one-line range", () => {
    expect(parseSourceLineRange("L12")).toEqual({ start: 12, end: 12 });
  });
  it.each([undefined, null, "", "abc", "L0", "L0-3", "L15-12", "L-3"])("returns null for %s", (value) => {
    expect(parseSourceLineRange(value as string | null | undefined)).toBeNull();
  });
});
