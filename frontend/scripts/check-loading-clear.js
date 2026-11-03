#!/usr/bin/env node
/**
 * check-loading-clear.js（ADR-1054 段 4・docs/handoff/line-like-speed/stage4-guard-card.md）
 *
 * 「読み込み中に中身を消す形」の数を増やさない見張り。
 *
 * 数えるもの: src の .ts・.tsx（*.test.ts・*.test.tsx を除く）で、
 *   set〇〇Loading(true) を書いた行の数（ファイルごと・同じ行に 2 つあっても 1）。
 * 基準: scripts/loading-clear-baseline.json（src からの道すじ → 行の数）。
 *   基準に無いファイルは基準 0。
 * 赤になる時:
 *   1. 今の数が基準より多い（足した）
 *   2. 今の数が基準より少ない（直した・消した）→ 同じ変更で基準の表を下げる（0 なら行を消す）
 * 例外: その行か、すぐ上の行に `loading-clear-exempt: <理由>` があれば数えない（理由は空にしない）。
 * 自己点検: 動くたびに、まず一時フォルダの作り物で「同じ数は緑・1 本足すと赤・1 本消すと赤」を確かめる。
 *
 * 使い方: node scripts/check-loading-clear.js
 * CI: npm run check:loading-clear（check:all に入っている）
 */

import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { dirname, extname, join, relative, sep } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_DIR = join(__dirname, '../src');
const BASELINE_FILE = join(__dirname, 'loading-clear-baseline.json');
const PATTERN = /set[A-Za-z0-9]*Loading[A-Za-z0-9]*\(\s*true\s*\)/;
const EXEMPT = /loading-clear-exempt:\s*\S/;
const SKIP_DIRS = new Set(['node_modules', 'coverage', 'dist']);

function collectFiles(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(entry)) results.push(...collectFiles(full));
    } else if ((extname(entry) === '.ts' || extname(entry) === '.tsx') && !/\.test\.tsx?$/.test(entry)) {
      results.push(full);
    }
  }
  return results;
}

function countLines(srcDir) {
  const counts = {};
  for (const file of collectFiles(srcDir)) {
    const lines = readFileSync(file, 'utf8').split('\n');
    let n = 0;
    lines.forEach((line, i) => {
      if (!PATTERN.test(line)) return;
      const prevLine = i > 0 ? lines[i - 1] : '';
      if (EXEMPT.test(line) || EXEMPT.test(prevLine)) return;
      n += 1;
    });
    if (n > 0) counts[relative(srcDir, file).split(sep).join('/')] = n;
  }
  return counts;
}

function compare(counts, baseline) {
  const problems = [];
  const names = [...new Set([...Object.keys(counts), ...Object.keys(baseline)])].sort();
  for (const name of names) {
    const now = counts[name] ?? 0;
    const base = baseline[name] ?? 0;
    if (now > base) {
      problems.push(`増えた: src/${name} 基準 ${base} → 今 ${now}`);
    } else if (now < base) {
      problems.push(`減った: src/${name} 基準 ${base} → 今 ${now}（scripts/loading-clear-baseline.json のこの行を ${now} に下げる。0 なら行を消す）`);
    }
  }
  return problems;
}

function selfTest() {
  const root = mkdtempSync(join(tmpdir(), 'loading-clear-'));
  try {
    mkdirSync(join(root, 'pages'));
    const baseline = { 'pages/A.tsx': 1 };
    writeFileSync(join(root, 'pages/A.tsx'), 'setLoading(true);\nsetOpen(true);\n');
    writeFileSync(join(root, 'pages/A.test.tsx'), 'setLoading(true);\n');
    writeFileSync(join(root, 'pages/B.tsx'), '// loading-clear-exempt: 送るボタンの印\nsetSendLoading(true);\n');
    const same = compare(countLines(root), baseline).length === 0;
    writeFileSync(join(root, 'pages/A.tsx'), 'setLoading(true);\nsetListLoading( true );\n');
    const added = compare(countLines(root), baseline).length === 1;
    writeFileSync(join(root, 'pages/A.tsx'), 'setOpen(true);\n');
    const removed = compare(countLines(root), baseline).length === 1;
    return same && added && removed;
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

if (!selfTest()) {
  console.log('❌ loading-clear: 自己点検に失敗（数え方が壊れている）');
  process.exit(1);
}

const baseline = JSON.parse(readFileSync(BASELINE_FILE, 'utf8'));
const counts = countLines(SRC_DIR);
const problems = compare(counts, baseline);
const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

if (problems.length === 0) {
  console.log(`✅ loading-clear: 基準どおり（${Object.keys(counts).length} ファイル・${total} 行）`);
  process.exit(0);
}

for (const p of problems) console.log(`❌ ${p}`);
console.log(`\n❌ loading-clear: ${problems.length} 件`);
console.log('   読み込み中に中身を消す形（set〇〇Loading(true)）を増やさない（ADR-1054 段 4）。');
console.log('   新しい読み込みは src/lib/query/apiQuery.ts の useApiQuery を使う。');
console.log('   中身を消さない印（送るボタンなど）は、その行かすぐ上の行に loading-clear-exempt: <理由> を書く。');
process.exit(1);
