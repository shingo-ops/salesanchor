#!/usr/bin/env node
/**
 * check-i18n-missing-keys.js
 *
 * frontend/src 内の literal な t() 参照が
 * ja.json / en.json の両方に存在するかを検証する（全 prefix 対象）。
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const SRC_DIR = join(ROOT, "src");
const LOCALE_FILES = [
  join(SRC_DIR, "locales/ja.json"),
  join(SRC_DIR, "locales/en.json"),
];
const T_CALL_PATTERN = /(?:\b(?:[A-Za-z_$][\w$]*\.)?t)\(\s*([`'"])([^`'"]+)\1\s*(?:,|\))/g;

function walk(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      if (entry === "coverage" || entry === "dist") continue;
      results.push(...walk(full));
    } else if (/\.(ts|tsx|js|jsx)$/.test(entry)) {
      results.push(full);
    }
  }
  return results;
}

function flattenLocale(node, prefix = "") {
  const keys = new Set();
  for (const [key, value] of Object.entries(node)) {
    const next = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      for (const child of flattenLocale(value, next)) keys.add(child);
    } else {
      keys.add(next);
    }
  }
  return keys;
}

const localeKeySets = LOCALE_FILES.map((file) => flattenLocale(JSON.parse(readFileSync(file, "utf8"))));
const issues = [];

for (const file of walk(SRC_DIR)) {
  const lines = readFileSync(file, "utf8").split("\n");
  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    let match;
    T_CALL_PATTERN.lastIndex = 0;
    while ((match = T_CALL_PATTERN.exec(line))) {
      const key = match[2];
      if (key.includes("${")) continue;
      if (!key.includes(".")) continue; // ドットなしは i18n キーでない（コメント内プレースホルダ等）
      const missing = localeKeySets.map((set) => !set.has(key));
      if (missing.some(Boolean)) {
        issues.push({ file: relative(ROOT, file), line: lineIndex + 1, key, missingJa: missing[0], missingEn: missing[1] });
      }
    }
  }
}

if (issues.length > 0) {
  console.error("❌ i18n key check FAILED");
  for (const issue of issues) {
    console.error(`   ${issue.file}:${issue.line}  ${issue.key} (ja:${issue.missingJa ? "missing" : "ok"}, en:${issue.missingEn ? "missing" : "ok"})`);
  }
  process.exit(1);
}

console.log("✅ i18n key check PASSED (all prefixes)");
