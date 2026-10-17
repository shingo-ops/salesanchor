import { describe, expect, it } from "vitest";
import type { BadgeVariant } from "../../components/Badge";
import { conditionBadgeVariant } from "./conditionBadge";

// ADR-1023 の12値（public.line_conditions）＋ Bulk。割り当ては design.md の表。
const CASES: ReadonlyArray<[string, BadgeVariant]> = [
  ["Sealed box", "info"],
  ["Case", "success"],
  ["Unsearched pack", "info"],
  ["Damaged sealed box", "warning"],
  ["Damaged case", "warning"],
  ["No shrink box", "purple"],
  ["Opened box", "danger"],
  ["Opened case", "danger"],
  ["Searched box", "danger"],
  ["Searched pack", "danger"],
  ["AR confirmed pack", "danger"],
  ["Bulk", "neutral"],
];

describe("conditionBadgeVariant", () => {
  it.each(CASES)("maps %s -> %s", (value, variant) => {
    expect(conditionBadgeVariant(value)).toBe(variant);
  });
  it.each(CASES)("is trim and case-insensitive for %s", (value, variant) => {
    expect(conditionBadgeVariant(`  ${value.toUpperCase()} `)).toBe(variant);
    expect(conditionBadgeVariant(value.toLowerCase())).toBe(variant);
  });
  it.each([["Empty box"], ["FLAG_SINGLE"], ["New"], ["sealed"], ["damaged"], ["sealed box x"]])(
    "falls back to neutral for %s (no partial match, old values dropped)",
    (value) => {
      expect(conditionBadgeVariant(value)).toBe("neutral");
    },
  );
  it.each([[""], ["   "], [null], [undefined]])("falls back to neutral for empty %s", (value) => {
    expect(conditionBadgeVariant(value)).toBe("neutral");
  });
});
