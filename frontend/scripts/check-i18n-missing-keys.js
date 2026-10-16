#!/usr/bin/env node
/**
 * check-i18n-missing-keys.js
 *
 * frontend/src 内の literal な t() 参照が辞書に存在するかを検証する（全 prefix 対象）。
 * 閲覧ページ（/viewer/・ADR-1019）は専用の辞書 src/locales/viewer/{ja,en}.json を持つため、ファイルを3つに分ける。
 *   ① src/pages/viewer/ の中のファイル        → viewer 辞書だけに必要
 *   ② viewer の入口から import をたどって届く、viewer 外のファイル（金型など）
 *                                            → 本体辞書と viewer 辞書の両方に必要
 *   ③ それ以外                                → 本体辞書だけに必要（従来どおり）
 * import type は辿らない。動的 import() は辿る。
 * あわせて viewer の ja / en のキー集合が一致することも検査する。
 */

import { existsSync, readFileSync, readdirSync, statSync } from "fs";
import { join, relative, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const SRC_DIR = join(ROOT, "src");
const LOCALE_FILES = [
  join(SRC_DIR, "locales/ja.json"),
  join(SRC_DIR, "locales/en.json"),
];
const VIEWER_LOCALE_FILES = [
  join(SRC_DIR, "locales/viewer/ja.json"),
  join(SRC_DIR, "locales/viewer/en.json"),
];
const VIEWER_DIR = join(SRC_DIR, "pages/viewer");
const VIEWER_ENTRY = join(VIEWER_DIR, "main.tsx");
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

const IMPORT_PATTERNS = [
  /(?:^|[\s;])import\s+(?!type\b)[^'"`;]*?\sfrom\s*['"]([^'"]+)['"]/g, // import x from "…"
  /(?:^|[\s;])export\s+(?!type\b)[^'"`;]*?\sfrom\s*['"]([^'"]+)['"]/g, // export … from "…"
  /(?:^|[\s;])import\s*['"]([^'"]+)['"]/g, // import "…"
  /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g, // import("…")
];
const EXTS = [".ts", ".tsx", ".js", ".jsx"];

function resolveImport(fromFile, spec) {
  if (!spec.startsWith(".")) return null;
  const base = join(dirname(fromFile), spec);
  const candidates = [base, ...EXTS.map((e) => base + e), ...EXTS.map((e) => join(base, "index" + e))];
  for (const c of candidates) {
    if (existsSync(c) && statSync(c).isFile() && /\.(ts|tsx|js|jsx)$/.test(c)) return c;
  }
  return null;
}

/** viewer の入口から届くファイルの集合（入口を含む） */
function reachableFromViewer() {
  const seen = new Set();
  const stack = [VIEWER_ENTRY];
  while (stack.length > 0) {
    const file = stack.pop();
    if (seen.has(file)) continue;
    seen.add(file);
    const text = readFileSync(file, "utf8");
    for (const pattern of IMPORT_PATTERNS) {
      pattern.lastIndex = 0;
      let m;
      while ((m = pattern.exec(text))) {
        const target = resolveImport(file, m[1]);
        if (target && !seen.has(target)) stack.push(target);
      }
    }
  }
  return seen;
}

const localeKeySets = LOCALE_FILES.map((file) => flattenLocale(JSON.parse(readFileSync(file, "utf8"))));
const viewerKeySets = VIEWER_LOCALE_FILES.map((file) => flattenLocale(JSON.parse(readFileSync(file, "utf8"))));
const issues = [];

// viewer の ja / en のキー集合が一致すること
for (const [a, b, name] of [
  [viewerKeySets[0], viewerKeySets[1], "ja にあって en に無い"],
  [viewerKeySets[1], viewerKeySets[0], "en にあって ja に無い"],
]) {
  for (const key of a) {
    if (!b.has(key)) issues.push({ file: "src/locales/viewer", line: 0, key: `${key} (${name})`, sets: [] });
  }
}

const viewerReach = reachableFromViewer();

for (const file of walk(SRC_DIR)) {
  const inViewerDir = file.startsWith(VIEWER_DIR + "/");
  const reachedByViewer = !inViewerDir && viewerReach.has(file);
  // 検査に使う辞書の組：① viewer だけ ② 本体＋viewer ③ 本体だけ
  const sets = inViewerDir ? viewerKeySets : reachedByViewer ? [...localeKeySets, ...viewerKeySets] : localeKeySets;
  const labels = inViewerDir ? ["viewer-ja", "viewer-en"] : reachedByViewer ? ["ja", "en", "viewer-ja", "viewer-en"] : ["ja", "en"];
  const lines = readFileSync(file, "utf8").split("\n");
  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    let match;
    T_CALL_PATTERN.lastIndex = 0;
    while ((match = T_CALL_PATTERN.exec(line))) {
      const key = match[2];
      if (key.includes("${")) continue;
      if (!key.includes(".")) continue; // ドットなしは i18n キーでない（コメント内プレースホルダ等）
      const missing = sets.map((set) => !set.has(key));
      if (missing.some(Boolean)) {
        issues.push({ file: relative(ROOT, file), line: lineIndex + 1, key, sets: labels.map((l, i) => `${l}:${missing[i] ? "missing" : "ok"}`) });
      }
    }
  }
}

if (issues.length > 0) {
  console.error("❌ i18n key check FAILED");
  for (const issue of issues) {
    console.error(`   ${issue.file}:${issue.line}  ${issue.key} (${issue.sets.join(", ")})`);
  }
  process.exit(1);
}

console.log("✅ i18n key check PASSED (all prefixes)");
console.log(`   viewer 入口から届く viewer 外のファイル: ${[...viewerReach].filter((f) => !f.startsWith(VIEWER_DIR + "/")).length} 件`);
