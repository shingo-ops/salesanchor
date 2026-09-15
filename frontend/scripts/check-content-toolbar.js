#!/usr/bin/env node
/**
 * check-content-toolbar.js
 *
 * src/pages/ 配下の tsx で、旧書き方 page-content-actions の使用を禁止する。
 * 本文上の操作行は ContentToolbar（操作台）金型を使うこと。
 *
 * 経緯: 2026-07-24 に全22画面を ContentToolbar へ統一。再発を機械で止める。
 * design: docs/specs/design-system/component-ssot/page-header-v2/design.md
 *
 * 使用方法: node scripts/check-content-toolbar.js
 * CI: npm run check:content-toolbar（check:all に含まれる）
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';
import { execSync } from 'child_process';

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
const pagesDir = join(repoRoot, 'frontend/src/pages');

/**
 * 検査から除外するページ（パスの一部でマッチ）。
 * 追加するときは理由をコメントで書くこと。
 */
const ALLOWLIST = [];

function walkTsx(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      results.push(...walkTsx(fullPath));
    } else if (entry.endsWith('.tsx')) {
      results.push(fullPath);
    }
  }
  return results;
}

const files = walkTsx(pagesDir);
const violations = [];

for (const file of files) {
  const relPath = relative(repoRoot, file);
  if (ALLOWLIST.some((pattern) => relPath.includes(pattern))) continue;

  const lines = readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, i) => {
    if (line.includes('page-content-actions')) {
      violations.push(`${relPath}:${i + 1}`);
    }
  });
}

if (violations.length > 0) {
  console.error('❌ 操作台チェック FAILED: 旧書き方 page-content-actions が使われています');
  console.error('   本文上の操作行は ContentToolbar（操作台）を使ってください');
  console.error('   例: <ContentToolbar left={フィルタ} right={ボタン} />');
  console.error('');
  for (const v of violations) {
    console.error(`   ${v}`);
  }
  console.error('');
  process.exit(1);
} else {
  console.log('✅ 操作台チェック PASSED（page-content-actions の使用なし）');
  process.exit(0);
}
