import { describe, expect, it } from "vitest";
import {
  EVENT_COLOR_KEYS,
  eventColorLabelKey,
  eventColorVar,
  eventDisplayColor,
  isEventColorKey,
} from "./eventColors";

describe("eventColors", () => {
  it("has 24 distinct keys", () => {
    expect(EVENT_COLOR_KEYS).toHaveLength(24);
    expect(new Set(EVENT_COLOR_KEYS).size).toBe(24);
  });

  it("eventColorVar turns _ into - in the token", () => {
    expect(eventColorVar("cherry_blossom")).toBe("var(--event-color-cherry-blossom)");
    expect(eventColorVar("tomato")).toBe("var(--event-color-tomato)");
  });

  it("isEventColorKey rejects unknown values", () => {
    expect(isEventColorKey("red")).toBe(false);
    expect(isEventColorKey(null)).toBe(false);
    expect(isEventColorKey("")).toBe(false);
    expect(isEventColorKey("tomato")).toBe(true);
  });

  it("eventColorLabelKey returns the default key for null", () => {
    expect(eventColorLabelKey(null)).toBe("schedule.eventColors.default");
    expect(eventColorLabelKey("basil")).toBe("schedule.eventColors.basil");
  });

  it("eventDisplayColor falls back to the owner color", () => {
    expect(eventDisplayColor(null, "X")).toBe("X");
    expect(eventDisplayColor(undefined, "X")).toBe("X");
    expect(eventDisplayColor("tomato", "X")).toBe("var(--event-color-tomato)");
  });
});
