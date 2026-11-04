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
