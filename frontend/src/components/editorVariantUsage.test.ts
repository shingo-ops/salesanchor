/**
 * 守り手: 欄の種類 `editor-filled` / `editor-title` は、金型 EditorPage の中の欄だけで使う
 * （ADR-1074・docs/handoff/schedule-gcal-clone/card-bin14.md §8）。
 * frontend/src 配下の tsx を読み、使ってよい場所以外にこの書き方が 1 件も無いことを確かめる。
 */
import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const SRC_ROOT = join(__dirname, "..");

/** 使ってよい場所（frontend/src からの相対。ディレクトリは末尾 `/`） */
const ALLOWED = [
  "components/TextField.tsx",
  "components/Select.tsx",
  "components/Textarea.tsx",
  "components/TextField.stories.tsx",
  "components/Select.stories.tsx",
  "components/Textarea.stories.tsx",
  "components/EditorPage.tsx", // 説明の文に種類の名前が出る
  "components/EditorPage.stories.tsx",
  "components/EditorPage.test.tsx",
  "pages/schedule/ScheduleDraftFields.tsx",
  "pages/schedule/ScheduleFullEditor.tsx",
  "pages/schedule/SchedulePageImpl.test.tsx",
  "pages/design-preview/",
];

const PATTERN = /["']editor-(?:filled|title)["']/;

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      if (name === "node_modules") continue;
      walk(full, out);
    } else if (/\.tsx$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

function isAllowed(rel: string): boolean {
  return ALLOWED.some((a) => (a.endsWith("/") ? rel.startsWith(a) : rel === a));
}

describe("editor-filled / editor-title variant usage", () => {
  const files = walk(SRC_ROOT)
    .map((f) => relative(SRC_ROOT, f).split(sep).join("/"))
    .filter((rel) => PATTERN.test(readFileSync(join(SRC_ROOT, rel), "utf-8")));

  it("is found at least once (the search itself works)", () => {
    expect(files.length).toBeGreaterThan(0);
  });

  it("appears only in the allowed paths", () => {
    expect(files.filter((rel) => !isAllowed(rel))).toEqual([]);
  });
});
