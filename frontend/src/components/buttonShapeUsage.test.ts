/**
 * 守り手: Button / ButtonLink の `shape="pill"` と `size="auth"` は、ログイン画面だけで使う
 * （docs/handoff/login-round-inputs/design.md §5・§7.4・K8）。
 * frontend/src 配下の tsx を読み、許可パス以外にこの書き方が 1 件も無いことを確かめる。
 */
import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const SRC_ROOT = join(__dirname, "..");

/** 使ってよい場所（frontend/src からの相対。ディレクトリは末尾 `/`） */
const ALLOWED = [
  "pages/login/",
  "components/Button.stories.tsx",
  "components/Button.test.tsx",
  "components/ButtonLink.test.tsx",
  "pages/design-preview/",
];

const PATTERNS = [
  /\bshape\s*=\s*(?:"pill"|\{\s*"pill"\s*\}|\{\s*'pill'\s*\})/,
  /\bsize\s*=\s*(?:"auth"|\{\s*"auth"\s*\}|\{\s*'auth'\s*\})/,
];

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

describe("Button shape=pill / size=auth usage", () => {
  it("appears only in the allowed paths", () => {
    const offenders = walk(SRC_ROOT)
      .map((f) => relative(SRC_ROOT, f).split(sep).join("/"))
      .filter((rel) => !isAllowed(rel))
      .filter((rel) => {
        const text = readFileSync(join(SRC_ROOT, rel), "utf-8");
        return PATTERNS.some((p) => p.test(text));
      });
    expect(offenders).toEqual([]);
  });
});
