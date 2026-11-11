/**
 * 守り手: 範囲の札 `gcal-colors` と Google の色のトークン `--gcal-` は、決めた場所だけで使う
 * （ADR-1074・docs/handoff/schedule-gcal-clone/design.md §3.20・card-bin14.md §8）。
 * frontend/src 配下の .ts・.tsx・.css を読む。数えるのはこの試験のファイル自身を除いた物。
 */
import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const SRC_ROOT = join(__dirname, "..");
const SELF = "components/gcalColorsUsage.test.ts";

/** `gcal-colors` の文字を書いてよい場所 */
const SCOPE_ALLOWED = [
  "pages/schedule/SchedulePageImpl.tsx",
  "components/EditorPage.tsx",
  "components/EditorPage.stories.tsx",
  "components/EditorPage.test.tsx",
  SELF,
  "pages/schedule/SchedulePageImpl.test.tsx",
  "tokens.css",
];

/** `--gcal-` の文字を書いてよい場所 */
const TOKEN_ALLOWED = ["index.css", "tokens.css", SELF];

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      if (name === "node_modules") continue;
      walk(full, out);
    } else if (/\.(?:ts|tsx|css)$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

const FILES = walk(SRC_ROOT).map((f) => relative(SRC_ROOT, f).split(sep).join("/"));

function filesWith(needle: string): string[] {
  return FILES.filter((rel) => rel !== SELF).filter((rel) => readFileSync(join(SRC_ROOT, rel), "utf-8").includes(needle));
}

describe("gcal-colors scope class", () => {
  const found = filesWith("gcal-colors");

  it("is found where it must be (the search itself works)", () => {
    expect(found).toContain("tokens.css");
    expect(found).toContain("pages/schedule/SchedulePageImpl.tsx");
  });

  it("appears only in the allowed files", () => {
    expect(found.filter((rel) => !SCOPE_ALLOWED.includes(rel))).toEqual([]);
  });
});

describe("--gcal- tokens", () => {
  const found = filesWith("--gcal-");

  it("are found where they must be (the search itself works)", () => {
    expect(found).toContain("index.css");
    expect(found).toContain("tokens.css");
  });

  it("appear only in the allowed files", () => {
    expect(found.filter((rel) => !TOKEN_ALLOWED.includes(rel))).toEqual([]);
  });
});
