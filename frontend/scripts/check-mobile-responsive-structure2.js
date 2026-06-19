#!/usr/bin/env node
/**
 * check-mobile-responsive-structure2.js
 *
 * ADR-140 構造2 の検証を first-phase scope に限定する。
 *
 * 検証対象:
 *   - src/components/Drawer.css
 *   - src/components/Modal.css
 *
 * 除外理由:
 *   - src/tokens.css の 640px はトークン値定義であり、生値ではない
 *   - src/pages/** の 640px は second-phase のページ内部レイアウト
 *
 * このチェックは first-phase shell CSS 内で 640px の直書きがないことだけを確認する。
 */

import { readFileSync, existsSync } from "fs";
import { join, dirname, relative } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const TARGETS = [
  "src/components/Drawer.css",
  "src/components/Modal.css",
];

function isCommentLine(trimmed) {
  return (
    trimmed.startsWith("/*") ||
    trimmed.startsWith("*") ||
    trimmed.startsWith("//")
  );
}

let hasError = false;

for (const relPath of TARGETS) {
  const file = join(root, relPath);
  if (!existsSync(file)) {
    console.error(`[structure2] ❌ missing file: ${relPath}`);
    hasError = true;
    continue;
  }

  const lines = readFileSync(file, "utf8").split("\n");
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (isCommentLine(trimmed)) return;

    if (/\b640px\b/.test(trimmed)) {
      console.error(`[structure2] ❌ ${relative(process.cwd(), file)}:${i + 1}`);
      console.error(`   ${trimmed}`);
      console.error(
        "   → first-phase scope では Drawer.css / Modal.css から 640px を消し、767px を参照してください",
      );
      hasError = true;
    }
  });
}

if (hasError) {
  console.error("");
  console.error(
    "[structure2] FAILED: first-phase scope に 640px の直書きが残っています",
  );
  process.exit(1);
}

console.log("[structure2] PASSED: first-phase scope に 640px の直書きなし");
process.exit(0);
