import { describe, expect, it } from "vitest";
import vectors from "./searchNormalize.vectors.json";
import { normalizeForSearch } from "./searchNormalize";

// backend の test_inventory_distribution_rows_pg.py も同じベクタを読む。ベクタを変えるときは両方のテストを触る。
describe("normalizeForSearch", () => {
  it.each(vectors)("normalizes %j", ({ input, expected }) => {
    expect(normalizeForSearch(input)).toBe(expected);
  });
});
