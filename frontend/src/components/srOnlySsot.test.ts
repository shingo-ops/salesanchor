/**
 * SSOT 守り手: .sr-only の「定義」は frontend/src 全体で1か所だけ
 * （docs/handoff/viewer-header-remove/design.md 4-2・⑤C17）。
 * クラス名が JSX 等に出てくるだけ（利用側）は対象外。CSS が実際に .sr-only を
 * 定義している（セレクタとして使っている）ファイルだけを数える。
 */
import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const SRC_ROOT = join(__dirname, "..");

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      if (name === "node_modules") continue;
      walk(full, out);
    } else if (/\.css$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

/** コメントを除いた上で、.sr-only がセレクタとして使われている（直後が `,` `{` `:` のいずれか）かを見る */
function definesSrOnly(cssText: string): boolean {
  const withoutComments = cssText.replace(/\/\*[\s\S]*?\*\//g, "");
  return /\.sr-only\s*[,{:]/.test(withoutComments);
}

describe(".sr-only SSOT (definition exists in exactly one file)", () => {
  it("C17: exactly one .css under frontend/src defines .sr-only", () => {
    const definers = walk(SRC_ROOT)
      .filter((file) => definesSrOnly(readFileSync(file, "utf8")))
      .map((file) => file.replace(SRC_ROOT, "frontend/src"));
    expect(definers).toEqual(["frontend/src/components/sr-only.css"]);
  });
});
