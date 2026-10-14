/**
 * 再発防止: api クライアントは内部で /api/v1 を付与する（lib/api.ts API_BASE）。
 * そのため api.get / api.post 等の第1引数に /api/v1 を付けると
 * /api/v1/api/v1/... の二重になり 404 になる。ここでは0件を保証する。
 * fetch( の直書きは対象外（そちらは /api/v1 付きが正しい）。
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
    } else if (/\.(ts|tsx)$/.test(name) && !/\.(test|spec|stories)\.(ts|tsx)$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

// api.get(" / api.post<T>(\n  ` / .get<T>( などの第1引数が /api/v1 で始まるもの（複数行可）
const PATTERN = /(?:\bapi)?\s*\.\s*(?:get|post|put|patch|delete|getBlob)\s*(?:<[^()]*?>)?\s*\(\s*(["'`])\/api\/v1/g;

describe("api クライアントの /api/v1 二重付与", () => {
  it("api.get|post|put|patch|delete|getBlob の第1引数が /api/v1 で始まる呼び出しが0件", () => {
    const hits: string[] = [];
    for (const file of walk(SRC_ROOT)) {
      const text = readFileSync(file, "utf8");
      for (const m of text.matchAll(PATTERN)) {
        const line = text.slice(0, m.index).split("\n").length;
        hits.push(`${file.replace(SRC_ROOT, "frontend/src")}:${line}`);
      }
    }
    expect(hits).toEqual([]);
  });
});
