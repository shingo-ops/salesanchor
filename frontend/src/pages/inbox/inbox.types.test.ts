/* eslint-disable local/no-japanese-literal -- 日本語の表示文を期待値として確かめる試験 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { elapsedLabel, formatAbsolute, relativeTime } from "./inbox.types";

const NOW = new Date("2026-10-30T12:00:00");
const ago = (sec: number) => new Date(NOW.getTime() - sec * 1000).toISOString();

describe("inbox time labels", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });
  afterEach(async () => {
    vi.useRealTimers();
    await i18n.changeLanguage("ja");
  });

  it("ja: 経過の言葉", async () => {
    await i18n.changeLanguage("ja");
    const t = i18n.t.bind(i18n);
    expect(relativeTime(ago(30), t, "ja")).toBe("たった今");
    expect(relativeTime(ago(5 * 60), t, "ja")).toBe("5分前");
    expect(relativeTime(ago(3 * 3600), t, "ja")).toBe("3時間前");
    expect(relativeTime(ago(2 * 86400), t, "ja")).toBe("2日前");
    expect(elapsedLabel(ago(5 * 60), t)).toBe("5分前");
  });

  it("en: 5分前は 5m ago", async () => {
    await i18n.changeLanguage("en");
    const t = i18n.t.bind(i18n);
    expect(relativeTime(ago(5 * 60), t, "en")).toBe("5m ago");
  });

  it("10日前は今の言語の月日", () => {
    const t = i18n.t.bind(i18n);
    const iso = ago(10 * 86400);
    const d = new Date(iso);
    for (const lang of ["ja", "en-US"]) {
      expect(relativeTime(iso, t, lang)).toBe(
        d.toLocaleDateString(lang, { month: "2-digit", day: "2-digit" }),
      );
    }
  });

  it("formatAbsolute は言語で形を作り、null は —", () => {
    const iso = ago(3600);
    const d = new Date(iso);
    expect(formatAbsolute(iso, "ja")).toBe(
      d.toLocaleString("ja", {
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit",
      }),
    );
    expect(formatAbsolute(null, "ja")).toBe("—");
  });
});
