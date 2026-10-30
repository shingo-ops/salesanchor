import { describe, expect, it } from "vitest";
import i18n from "../../i18n";
import ja from "../../locales/ja.json";
import { normalizeShift, type ApiShift } from "./schedule-utils";

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
