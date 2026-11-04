import { describe, expect, it } from "vitest";
import i18n from "../../i18n";
import ja from "../../locales/ja.json";
import {
  fitPopover,
  normalizeShift,
  toRangeEnd,
  toRangeStart,
  type AnchorRect,
  type ApiShift,
} from "./schedule-utils";

const baseShift: ApiShift = {
  id: 1,
  user_id: 2,
  shift_date: "2026-10-30",
  start_time: "09:00:00",
  end_time: "18:00:00",
  shift_type: "work",
  notes: null,
  created_at: "2026-10-01T00:00:00Z",
};

describe("normalizeShift", () => {
  const t = i18n.getFixedT("ja");

  it("holiday uses the ja translation of schedule.holiday", () => {
    expect(normalizeShift({ ...baseShift, shift_type: "holiday" }, t).title).toBe(ja.schedule.holiday);
  });

  it("non-holiday uses the ja translation of schedule.shiftLabel", () => {
    expect(normalizeShift(baseShift, t).title).toBe(ja.schedule.shiftLabel);
  });
});

function rectOf(left: number, top: number, width = 80, height = 48): AnchorRect {
  return { left, top, width, height, right: left + width, bottom: top + height };
}

describe("fitPopover", () => {
  const margin = 12;
  const popoverWidth = 320;
  const viewportHeights = [600, 768, 900];
  const viewportWidths = [1024, 1280, 1920];

  for (const vh of viewportHeights) {
    for (const vw of viewportWidths) {
      const heights = [240, 400, Math.min(544, vh - 24)];
      for (const h of heights) {
        it(`keeps the popover inside ${vw}x${vh} for height ${h} at the bottom-right slot`, () => {
          const anchor = rectOf(vw - 100, vh - 48);
          const { left, top } = fitPopover(anchor, { width: popoverWidth, height: h }, { width: vw, height: vh }, margin);
          expect(left).toBeGreaterThanOrEqual(margin);
          expect(top).toBeGreaterThanOrEqual(margin);
          expect(left + popoverWidth).toBeLessThanOrEqual(vw - margin);
          expect(top + h).toBeLessThanOrEqual(vh - margin);
        });
      }
    }
  }

  it("pushes the popover back inside when neither the right nor the left side fits", () => {
    const anchor = rectOf(100, 100, 560, 48);
    const { left } = fitPopover(anchor, { width: popoverWidth, height: 300 }, { width: 700, height: 800 }, margin);
    expect(left).toBeGreaterThanOrEqual(margin);
    expect(left + popoverWidth).toBeLessThanOrEqual(700 - margin);
  });

  it("centres the popover when there is no anchor", () => {
    const { left, top } = fitPopover(null, { width: 320, height: 400 }, { width: 1000, height: 800 }, margin);
    expect(left).toBe(340);
    expect(top).toBe(200);
  });
});

describe("list view range", () => {
  it("covers 30 days from the selected day", () => {
    const anchor = new Date(2026, 10, 4, 15, 30);
    expect(toRangeStart("list", anchor)).toEqual(new Date(2026, 10, 4));
    expect(toRangeEnd("list", anchor)).toEqual(new Date(2026, 11, 4));
  });

  it("crosses a month boundary", () => {
    const anchor = new Date(2026, 0, 20);
    expect(toRangeEnd("list", anchor)).toEqual(new Date(2026, 1, 19));
  });

  it("crosses a year boundary", () => {
    const anchor = new Date(2026, 11, 15);
    expect(toRangeEnd("list", anchor)).toEqual(new Date(2027, 0, 14));
  });
});
