/* eslint-disable local/no-japanese-literal -- テスト: 作る小窓の日時の 1 行が Google と同じ日本語で出ることを検証する（ADR-027・precedent: CalendarView.test.tsx） */
import { describe, expect, it } from "vitest";
import i18n from "../../i18n";
import ja from "../../locales/ja.json";
import {
  draftToRange,
  eventNumericId,
  fitCreatePopover,
  fitPopover,
  fitRecurrenceToDate,
  formatDraftDateLine,
  formatSearchResultLine,
  normalizeEvent,
  normalizeShift,
  rangeToDraftDates,
  recurrenceChoicesFor,
  recurrenceLabel,
  recurrenceOptionsFor,
  scopeChoices,
  shiftDraftStart,
  toCalendarEnd,
  toHolidayEvents,
  toRangeEnd,
  toRangeStart,
  type AnchorRect,
  type ApiShift,
  type ScheduleItem,
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

describe("formatSearchResultLine", () => {
  const t = i18n.getFixedT("ja");
  const item = (patch: Partial<ScheduleItem>): ScheduleItem => ({
    id: "event-1",
    title: "商談A",
    start: new Date(2026, 10, 10, 10, 0),
    end: new Date(2026, 10, 10, 11, 0),
    allDay: false,
    category: null,
    calendarType: "shared",
    source: "app",
    ownerUserId: 101,
    ownerName: null,
    ...patch,
  });

  it("U1: timed event matches formatDraftDateLine for the same values", () => {
    const expected = formatDraftDateLine(
      { startDate: "2026-11-10", startTime: "10:00", endDate: "2026-11-10", endTime: "11:00", allDay: false },
      t,
      "ja",
    );
    expect(formatSearchResultLine(item({}), t, "ja")).toBe(expected);
  });

  it("U2: all-day event shows a single date and the all-day label", () => {
    const line = formatSearchResultLine(
      item({ allDay: true, start: new Date(2026, 10, 10), end: new Date(2026, 10, 11) }),
      t,
      "ja",
    );
    expect(line).toContain("11月10日");
    expect(line).not.toContain("11/11");
    expect(line).not.toContain("11日");
    expect(line).toContain(t("schedule.allDay"));
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

describe("three-day view range", () => {
  it("covers 3 days from the selected day", () => {
    const anchor = new Date(2026, 10, 4, 15);
    expect(toRangeStart("threeDay", anchor)).toEqual(new Date(2026, 10, 4));
    expect(toRangeEnd("threeDay", anchor)).toEqual(new Date(2026, 10, 7));
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

const D = (y: number, mo: number, d: number, h = 0, mi = 0) => new Date(y, mo - 1, d, h, mi);

describe("draftToRange（便12）", () => {
  const timedDraft = { startDate: "2026-11-10", startTime: "10:00", endDate: "2026-11-10", endTime: "11:00", allDay: false };

  it("時刻つき 10:00〜11:00", () => {
    expect(draftToRange(timedDraft)).toEqual({ start: D(2026, 11, 10, 10), end: D(2026, 11, 10, 11), allDay: false });
  });

  it("終日 1 日は end が次の日 0 時", () => {
    const r = draftToRange({ ...timedDraft, allDay: true });
    expect(r?.start).toEqual(D(2026, 11, 10));
    expect(r?.end).toEqual(D(2026, 11, 11));
    expect(r?.allDay).toBe(true);
  });

  it("終日 2 日は end が 11-12 0 時", () => {
    const r = draftToRange({ ...timedDraft, allDay: true, endDate: "2026-11-11" });
    expect(r?.end).toEqual(D(2026, 11, 12));
  });

  it("startDate が空なら null", () => {
    expect(draftToRange({ ...timedDraft, startDate: "" })).toBeNull();
  });

  it("end が start と同じなら null", () => {
    expect(draftToRange({ ...timedDraft, endTime: "10:00" })).toBeNull();
  });
});

describe("rangeToDraftDates（便12）", () => {
  it("終日 1 日", () => {
    expect(rangeToDraftDates(D(2026, 11, 10), D(2026, 11, 11), true)).toEqual({
      startDate: "2026-11-10", startTime: "00:00", endDate: "2026-11-10", endTime: "23:59", allDay: true,
    });
  });

  it("終日 2 日", () => {
    expect(rangeToDraftDates(D(2026, 11, 10), D(2026, 11, 12), true).endDate).toBe("2026-11-11");
  });

  it("時刻つき 10:00〜11:30", () => {
    expect(rangeToDraftDates(D(2026, 11, 10, 10), D(2026, 11, 10, 11, 30), false)).toEqual({
      startDate: "2026-11-10", startTime: "10:00", endDate: "2026-11-10", endTime: "11:30", allDay: false,
    });
  });

  it("時刻つき end なしは 1 時間後", () => {
    const r = rangeToDraftDates(D(2026, 11, 10, 10), null, false);
    expect(r.endTime).toBe("11:00");
  });

  it("終日 end なしは endDate＝startDate", () => {
    expect(rangeToDraftDates(D(2026, 11, 10), null, true).endDate).toBe("2026-11-10");
  });

  it("draftToRange との往復で元に戻る", () => {
    const cases: Array<[Date, Date, boolean]> = [
      [D(2026, 11, 10), D(2026, 11, 11), true],
      [D(2026, 11, 10), D(2026, 11, 12), true],
      [D(2026, 11, 10, 10), D(2026, 11, 10, 11, 30), false],
    ];
    for (const [s, e, a] of cases) {
      expect(draftToRange(rangeToDraftDates(s, e, a))).toEqual({ start: s, end: e, allDay: a });
    }
  });
});

describe("shiftDraftStart（便12）", () => {
  const base = { startDate: "2026-11-10", startTime: "10:00", endDate: "2026-11-10", endTime: "11:00", allDay: false };

  it("始まりを 15:00 にすると 15:00〜16:00", () => {
    const r = shiftDraftStart(base, "2026-11-10", "15:00");
    expect([r.startTime, r.endTime, r.endDate]).toEqual(["15:00", "16:00", "2026-11-10"]);
  });

  it("日付を 1 日進めると終わりの日付も 1 日進む", () => {
    const r = shiftDraftStart(base, "2026-11-11", "10:00");
    expect([r.startDate, r.endDate, r.endTime]).toEqual(["2026-11-11", "2026-11-11", "11:00"]);
  });

  it("終日 2 日の始まりを 3 日進めると終わりも 3 日進む", () => {
    const allDay = { ...base, allDay: true, endDate: "2026-11-11" };
    const r = shiftDraftStart(allDay, "2026-11-13", "00:00");
    expect([r.startDate, r.endDate]).toEqual(["2026-11-13", "2026-11-14"]);
  });

  it("新しい始まりが空なら終わりは今のまま", () => {
    const r = shiftDraftStart(base, "", "10:00");
    expect([r.startDate, r.endDate, r.endTime]).toEqual(["", "2026-11-10", "11:00"]);
  });
});

describe("fitCreatePopover（便12）", () => {
  const size = { width: 600, height: 300 };
  const viewport = { width: 1280, height: 800 };
  const rect = (left: number, top: number, width = 100, height = 40): AnchorRect => ({
    left, top, width, height, right: left + width, bottom: top + height,
  });

  it("右に入るなら anchor.right＋8", () => {
    expect(fitCreatePopover(rect(100, 100), size, viewport, 16, 8).left).toBe(208);
  });

  it("右に入らないなら anchor.left−幅−8", () => {
    expect(fitCreatePopover(rect(900, 100), size, viewport, 16, 8).left).toBe(900 - 600 - 8);
  });

  it("縦は anchor.top と (vh−h)/2 の小さい方", () => {
    expect(fitCreatePopover(rect(100, 100), size, viewport, 16, 8).top).toBe(100);
    expect(fitCreatePopover(rect(100, 400), size, viewport, 16, 8).top).toBe(250);
  });

  it("下にはみ出すなら vh−h−margin に収める", () => {
    const tall = { width: 600, height: 790 };
    expect(fitCreatePopover(rect(100, 600), tall, viewport, 16, 8).top).toBe(Math.max(16, 800 - 790 - 16));
    expect(fitCreatePopover(rect(100, 600), { width: 600, height: 700 }, viewport, 16, 8).top).toBe(50);
  });

  it("anchor なしは fitPopover(null) と同じ真ん中", () => {
    expect(fitCreatePopover(null, size, viewport, 16, 8)).toEqual(fitPopover(null, size, viewport, 16));
  });
});

describe("recurrence（便15B）", () => {
  const t = i18n.getFixedT("ja") as never;

  it("recurrenceChoicesFor は開始日で第 N・最終を出し分ける（G70）", () => {
    const nov12 = recurrenceChoicesFor(new Date(2026, 10, 12));
    expect(nov12).toContain("monthly_nth");
    expect(nov12).not.toContain("monthly_last");
    const nov26 = recurrenceChoicesFor(new Date(2026, 10, 26));
    expect(nov26).toContain("monthly_nth");
    expect(nov26).toContain("monthly_last");
    const nov30 = recurrenceChoicesFor(new Date(2026, 10, 30));
    expect(nov30).not.toContain("monthly_nth");
    expect(nov30).toContain("monthly_last");
  });

  it("recurrenceLabel は選び方の文字を作る（G72）", () => {
    expect(recurrenceLabel("weekly", new Date(2026, 10, 12), t, "ja")).toBe("毎週 木曜日");
    expect(recurrenceLabel("monthly_nth", new Date(2026, 10, 12), t, "ja")).toBe("毎月 第 2 木曜日");
    expect(recurrenceLabel("monthly_last", new Date(2026, 10, 30), t, "ja")).toBe("毎月 最終月曜日");
    expect(recurrenceLabel("yearly", new Date(2026, 10, 12), t, "ja")).toBe("毎年 11月12日");
    expect(recurrenceLabel("weekly", new Date("x"), t, "ja")).toBe("");
  });

  it("recurrenceOptionsFor は今の値を残し custom を含まない", () => {
    const nov30 = new Date(2026, 10, 30);
    expect(recurrenceOptionsFor(nov30, "monthly_nth")).toContain("monthly_nth");
    expect(recurrenceOptionsFor(nov30, null)).not.toContain("monthly_nth");
    expect(recurrenceOptionsFor(nov30, "monthly_nth")).not.toContain("custom");
    expect(recurrenceOptionsFor(nov30, null)).not.toContain("custom");
  });

  it("fitRecurrenceToDate は使えなくなった値をもう一方へ入れ替える", () => {
    expect(fitRecurrenceToDate("monthly_nth", new Date(2026, 10, 30))).toBe("monthly_last");
    expect(fitRecurrenceToDate("monthly_last", new Date(2026, 10, 12))).toBe("monthly_nth");
    expect(fitRecurrenceToDate("weekly", new Date(2026, 10, 12))).toBe("weekly");
  });

  it("scopeChoices は種類・1 回目か・選び方を変えたかで並びを決める", () => {
    expect(scopeChoices("save", true, false)).toEqual(["this", "all"]);
    expect(scopeChoices("save", false, false)).toEqual(["this", "following", "all"]);
    expect(scopeChoices("save", false, true)).toEqual(["following", "all"]);
    expect(scopeChoices("save", true, true)).toEqual(["all"]);
    expect(scopeChoices("delete", false, false)).toEqual(["this", "following", "all"]);
    expect(scopeChoices("move", true, false)).toEqual(["this", "all"]);
    expect(scopeChoices("move", false, false)).toEqual(["this", "following"]);
  });

  it("normalizeEvent は回ごとに違う id を作り、eventNumericId は元の行の数を返す", () => {
    const base = {
      id: 1, user_id: 1, calendar_type: "shared", title: "定例", description: null, location: null,
      start_datetime: "2026-11-12T10:00:00+09:00", end_datetime: "2026-11-12T11:00:00+09:00",
      is_all_day: false, google_event_id: null, source: "app", sync_status: null,
      created_by_user_id: 1, created_at: null, updated_at: null, created_by_name: null,
    };
    const occ = normalizeEvent({
      ...base,
      recurrence: "weekly",
      recurring_event_id: 1,
      occurrence_start: "2026-11-12T10:00:00+09:00",
      is_first_occurrence: true,
    });
    expect(occ.id).toBe(`event-1-${new Date("2026-11-12T10:00:00+09:00").getTime()}`);
    expect(eventNumericId(occ.id)).toBe(1);
    expect(eventNumericId("event-1")).toBe(1);
    expect(occ.occurrenceStart?.getTime()).toBe(new Date("2026-11-12T10:00:00+09:00").getTime());
    expect(occ.isFirstOccurrence).toBe(true);
    expect(occ.recurrence).toBe("weekly");
    expect(normalizeEvent(base).id).toBe("event-1");
  });
});
