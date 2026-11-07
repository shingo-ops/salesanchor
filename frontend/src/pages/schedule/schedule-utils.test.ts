/* eslint-disable local/no-japanese-literal -- テスト: 作る小窓の日時の 1 行が Google と同じ日本語で出ることを検証する（ADR-027・precedent: CalendarView.test.tsx） */
import { describe, expect, it } from "vitest";
import i18n from "../../i18n";
import ja from "../../locales/ja.json";
import {
  eventNumericId,
  fitPopover,
  formatDraftDateLine,
  normalizeShift,
  toCalendarEnd,
  toHolidayEvents,
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

describe("formatDraftDateLine", () => {
  const t = i18n.getFixedT("ja");
  const d = { startDate: "2026-11-10", startTime: "10:00", endDate: "2026-11-10", endTime: "11:00", allDay: false };
  const line = (patch: Partial<typeof d>) => formatDraftDateLine({ ...d, ...patch }, t, "ja");

  it("same-day timed range", () => {
    expect(line({})).toBe("11月10日(火) 午前10時～午前11時");
  });

  it("afternoon range", () => {
    expect(line({ startTime: "12:30", endTime: "13:30" })).toBe("11月10日(火) 午後12:30～午後1:30");
  });

  it("all-day single day", () => {
    expect(line({ allDay: true })).toBe("11月10日(火) 終日");
  });

  it("all-day multiple days", () => {
    expect(line({ allDay: true, endDate: "2026-11-12" })).toBe("11月10日(火)～11月12日(木)");
  });

  it("range across midnight", () => {
    expect(line({ startTime: "23:00", endDate: "2026-11-11", endTime: "01:00" })).toBe(
      "11月10日(火) 午後11時～11月11日(水) 午前1時",
    );
  });

  it("empty when the start is unreadable", () => {
    expect(line({ startTime: "" })).toBe("");
  });

  it("start only when the end time is unreadable", () => {
    expect(line({ endTime: "" })).toBe("11月10日(火) 午前10時");
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

describe("eventNumericId", () => {
  it("takes the number out of an event id", () => {
    expect(eventNumericId("event-12")).toBe(12);
  });

  it("returns null for a shift id", () => {
    expect(eventNumericId("shift-3")).toBeNull();
  });

  it("returns null for the pending box", () => {
    expect(eventNumericId("pending")).toBeNull();
  });
});

describe("toCalendarEnd", () => {
  const timedItem = {
    start: new Date(2026, 10, 10, 9, 0),
    end: new Date(2026, 10, 10, 10, 30),
    allDay: false,
  };
  const allDayItem = {
    start: new Date(2026, 10, 10, 0, 0),
    end: new Date(2026, 10, 10, 23, 59),
    allDay: true,
  };

  it("all-day one day: goes back one day and ends at 23:59", () => {
    const end = toCalendarEnd(new Date(2026, 10, 10), new Date(2026, 10, 11), true, allDayItem);
    expect(end).toEqual(new Date(2026, 10, 10, 23, 59));
  });

  it("all-day three days: ends at 23:59 of the last day", () => {
    const end = toCalendarEnd(new Date(2026, 10, 10), new Date(2026, 10, 13), true, allDayItem);
    expect(end).toEqual(new Date(2026, 10, 12, 23, 59));
  });

  it("timed with no end: keeps the original length", () => {
    const start = new Date(2026, 10, 12, 14, 0);
    expect(toCalendarEnd(start, null, false, timedItem)).toEqual(new Date(2026, 10, 12, 15, 30));
  });

  it("all-day moved to timed with no end: one hour", () => {
    const start = new Date(2026, 10, 12, 14, 0);
    expect(toCalendarEnd(start, null, false, allDayItem)).toEqual(new Date(2026, 10, 12, 15, 0));
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

describe("toHolidayEvents", () => {
  it("U1: makes an all-day, immovable holiday event", () => {
    expect(toHolidayEvents([{ date: "2026-11-03", name: "文化の日" }])).toEqual([
      {
        id: "holiday-2026-11-03",
        title: "文化の日",
        start: "2026-11-03",
        end: "2026-11-04",
        allDay: true,
        tone: "holiday",
        editable: false,
      },
    ]);
  });

  it("U2: month end rolls over to the next year", () => {
    expect(toHolidayEvents([{ date: "2026-12-31", name: "x" }])[0].end).toBe("2027-01-01");
  });

  it("U3: drops malformed dates and returns [] for undefined / []", () => {
    expect(toHolidayEvents([{ date: "2026/11/03", name: "x" }])).toEqual([]);
    expect(toHolidayEvents(undefined)).toEqual([]);
    expect(toHolidayEvents([])).toEqual([]);
  });
});
