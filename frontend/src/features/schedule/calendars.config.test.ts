import { describe, expect, it } from "vitest";
import en from "../../locales/en.json";
import ja from "../../locales/ja.json";
import { CALENDARS } from "./calendars.config";

function lookup(dict: unknown, key: string): unknown {
  return key.split(".").reduce<unknown>((node, part) => {
    if (node && typeof node === "object") {
      return (node as Record<string, unknown>)[part];
    }
    return undefined;
  }, dict);
}

const LOCALES: Array<[string, unknown]> = [
  ["ja", ja],
  ["en", en],
];

describe("CALENDARS badgeVariant and colors (G29)", () => {
  it("maps each calendar to its badge variant", () => {
    expect(Object.fromEntries(CALENDARS.map((c) => [c.id, c.badgeVariant]))).toEqual({
      meeting: "info",
      personal: "purple",
      procurement: "success",
      shipping: "danger",
      billing: "warning",
      release: "neutral",
      holiday: "purple",
    });
  });

  it("holds no hex color", () => {
    expect(JSON.stringify(CALENDARS)).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});

describe("CALENDARS labelKey has non-empty text in both ja and en", () => {
  const cases = CALENDARS.flatMap((meta) =>
    LOCALES.map(([lang, dict]) => ({
      id: meta.id,
      labelKey: meta.labelKey,
      lang,
      dict,
    })),
  );

  it.each(cases)("$id ($lang): $labelKey", ({ labelKey, dict }) => {
    const value = lookup(dict, labelKey);
    expect(typeof value).toBe("string");
    expect((value as string).trim().length).toBeGreaterThan(0);
  });
});
