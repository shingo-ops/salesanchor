#!/usr/bin/env node
/**
 * check-viewer-bundle.js（ADR-1019 段3）
 *
 * 閲覧ページ（/viewer/）のビルド結果を検査する。`npx vite build --manifest` の後に実行する。
 *   1. manifest の viewer 入口から imports / dynamicImports / css をたどり、JS の合計が 300KB 以下
 *   2. 本体の辞書にだけある葉キー名の目印5つが、viewer の JS（たどった全部）に含まれない
 *   3. 自己点検：目印が本体辞書にあり、viewer 辞書の葉キーには無く、本体の入口 JS には含まれる
 *      （検査の見方が壊れていないことの確認）
 */
import { existsSync, readFileSync, statSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const DIST = join(ROOT, "dist");
const MANIFEST = join(DIST, ".vite/manifest.json");
const VIEWER_ENTRY = "viewer/index.html";
const MAIN_ENTRY = "index.html";
const LIMIT_KB = 300;
/** 本体の辞書にだけある葉キー名（viewer の辞書には無い） */
const MARKERS = ["searchNameCode", "distributionOff", "expiryWarning", "windowUnlimited", "resetSort"];

function leafKeys(node, out = new Set()) {
  for (const [key, value] of Object.entries(node)) {
    if (value && typeof value === "object" && !Array.isArray(value)) leafKeys(value, out);
    else out.add(key);
  }
  return out;
}

const errors = [];
if (!existsSync(MANIFEST)) {
  console.error(`❌ viewer bundle check FAILED: ${MANIFEST} がありません（npx vite build --manifest を先に実行）`);
  process.exit(1);
}
const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
if (!manifest[VIEWER_ENTRY]) {
  console.error(`❌ viewer bundle check FAILED: manifest に ${VIEWER_ENTRY} がありません`);
  process.exit(1);
}

// viewer の入口からたどる
const seen = new Set();
const jsFiles = new Set();
const cssFiles = new Set();
(function walk(key) {
  if (seen.has(key)) return;
  seen.add(key);
  const chunk = manifest[key];
  if (!chunk) return;
  if (chunk.file && chunk.file.endsWith(".js")) jsFiles.add(chunk.file);
  for (const css of chunk.css ?? []) cssFiles.add(css);
  for (const next of [...(chunk.imports ?? []), ...(chunk.dynamicImports ?? [])]) walk(next);
})(VIEWER_ENTRY);

let totalBytes = 0;
const contents = new Map();
for (const file of jsFiles) {
  const full = join(DIST, file);
  totalBytes += statSync(full).size;
  contents.set(file, readFileSync(full, "utf8"));
}
const totalKb = totalBytes / 1024;
console.log(`viewer JS: ${jsFiles.size} ファイル, 合計 ${totalKb.toFixed(1)} KB（上限 ${LIMIT_KB} KB）`);
for (const file of jsFiles) console.log(`   ${file}  ${(statSync(join(DIST, file)).size / 1024).toFixed(1)} KB`);
console.log(`viewer CSS: ${cssFiles.size} ファイル`);
if (totalKb > LIMIT_KB) errors.push(`JS 合計 ${totalKb.toFixed(1)} KB が上限 ${LIMIT_KB} KB を超えています`);

// 自己点検
const mainKeys = leafKeys(JSON.parse(readFileSync(join(ROOT, "src/locales/ja.json"), "utf8")));
const viewerKeys = leafKeys(JSON.parse(readFileSync(join(ROOT, "src/locales/viewer/ja.json"), "utf8")));
const mainEntryFile = manifest[MAIN_ENTRY]?.file;
const mainEntryText = mainEntryFile ? readFileSync(join(DIST, mainEntryFile), "utf8") : "";
for (const m of MARKERS) {
  if (!mainKeys.has(m)) errors.push(`自己点検: 目印 ${m} が本体辞書の葉キーにありません`);
  if (viewerKeys.has(m)) errors.push(`自己点検: 目印 ${m} が viewer 辞書の葉キーにもあります`);
  if (!mainEntryText.includes(m)) errors.push(`自己点検: 目印 ${m} が本体の入口 JS に見つかりません（検査の見方が壊れています）`);
}

// 本体の辞書が混ざっていないこと
for (const m of MARKERS) {
  for (const [file, text] of contents) {
    if (text.includes(m)) errors.push(`目印 ${m} が viewer の JS ${file} に含まれています（本体の辞書を読み込んでいます）`);
  }
}

if (errors.length > 0) {
  console.error("❌ viewer bundle check FAILED");
  for (const e of errors) console.error(`   ${e}`);
  process.exit(1);
}
console.log("✅ viewer bundle check PASSED");
