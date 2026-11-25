/* eslint-disable local/no-japanese-literal -- テスト: 管理者が付けた種類の名前（DB の値）をそのまま出すことを検証する（ADR-027） */
import { describe, expect, it } from "vitest";
import en from "../../locales/en.json";
import ja from "../../locales/ja.json";
import { categoryLabel } from "./useCalendarCategories";

const t = (key: string, options?: { defaultValue?: string }) => {
  const word = key.split(".").reduce<unknown>((node, part) => {
    if (node && typeof node === "object") return (node as Record<string, unknown>)[part];
    return undefined;
  }, ja);
  return typeof word === "string" ? word : (options?.defaultValue ?? key);
};

describe("categoryLabel", () => {
  it("shows the given name when one is set", () => {
    expect(categoryLabel("meeting", "商談", t)).toBe("商談");
  });

  it("falls back to the i18n name of a built-in category when the name is empty", () => {
    expect(categoryLabel("meeting", null, t)).toBe(ja.schedule.calendarLabels.meeting);
    expect(categoryLabel("shipping", "", t)).toBe(ja.schedule.calendarLabels.shipping);
  });

  it("shows the key itself for a category with no name and no i18n name", () => {
    expect(categoryLabel("custom_9", null, t)).toBe("custom_9");
  });

  it("keeps the same calendarLabels keys in ja and en", () => {
    expect(Object.keys(en.schedule.calendarLabels).sort()).toEqual(Object.keys(ja.schedule.calendarLabels).sort());
  });
});
