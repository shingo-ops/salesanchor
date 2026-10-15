import { describe, expect, it } from "vitest";
import { initialZoom, refineZoom } from "./tableFitZoom";
import { MAX_ZOOM_ADJUST_STEPS } from "../constants/tableFit";

describe("initialZoom", () => {
  it("shrinks to frame / natural, floored to 3 decimals", () => {
    expect(initialZoom(900, 1200)).toBe(0.75);
    expect(initialZoom(1000, 3000)).toBe(0.333);
  });
  it("is 1 when the table already fits", () => {
    expect(initialZoom(1200, 900)).toBe(1);
  });
  it("is 1 when naturalWidth <= 0", () => {
    expect(initialZoom(900, 0)).toBe(1);
    expect(initialZoom(900, -5)).toBe(1);
  });
});

describe("refineZoom", () => {
  it("returns z unchanged when it does not overflow", () => {
    expect(refineZoom(0.75, () => false)).toBe(0.75);
  });
  it("decreases by 0.001 while overflowing", () => {
    const seen: number[] = [];
    const result = refineZoom(0.75, (z) => { seen.push(z); return z > 0.748; });
    expect(result).toBe(0.748);
    expect(seen).toEqual([0.75, 0.749, 0.748]);
  });
  it("stops after MAX_ZOOM_ADJUST_STEPS steps", () => {
    let calls = 0;
    const result = refineZoom(0.9, () => { calls += 1; return true; });
    expect(calls).toBe(MAX_ZOOM_ADJUST_STEPS);
    expect(result).toBe(0.7);
  });
  it("stops when z <= 0.001", () => {
    expect(refineZoom(0.001, () => true)).toBe(0.001);
    expect(refineZoom(0.002, () => true)).toBe(0.001);
  });
});
