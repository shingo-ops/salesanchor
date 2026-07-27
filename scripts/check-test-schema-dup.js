#!/usr/bin/env node
/**
 * check-test-schema-dup.js
 *
 * テスト（backend/tests/）が本番テーブル定義を新規にコピー（独自 CREATE TABLE）
 * したら検出して赤にする。柱3-a/b（docs/specs/process-hardening/design-pillar3.md）。
 *
 * アルゴリズム:
 *   変更された backend/tests/*.py の各ファイルについて
 *   本物のCREATE TABLE数を BASE と HEAD で数え、HEAD > BASE なら赤。
 *
 * 本物の定義: execute(text(...)) の複数行文字列内の CREATE TABLE。
 *   sql=文字列 / assert / docstring / コメント 内は除外（design §4-2, recon §4）。
 *
 * 集約先 backend/tests/conftest.py は対象外（共通定義の置き場）。
 *
 * 実行（CIから）: BASE_SHA=<sha> HEAD_SHA=<sha> node scripts/check-test-schema-dup.js
 * テスト用モック:
 *   MOCK_CHANGED_FILES=<改行区切り>  変更ファイル一覧を注入
 *   MOCK_FILE_<safe>_BASE / _HEAD    各ファイルのBASE/HEAD内容を注入（git迂回）
 *   （safe = パスの非英数字を _ に置換した大文字表現）
 */
'use strict';

const { execSync, spawnSync } = require('child_process');

const TESTS_DIR = 'backend/tests/';
const EXCLUDE = new Set(['backend/tests/conftest.py']);

function countRealCreateTable(source) {
  if (!source) return 0;
  const lines = source.split('\n');
  let inExecuteBlock = false;
  let count = 0;
  for (const line of lines) {
    if (/execute\(\s*text\(\s*f?"""/.test(line)) inExecuteBlock = true;
    if (/CREATE\s+TABLE/i.test(line) && inExecuteBlock) count++;
    if (inExecuteBlock && /^\s*"""\s*\)?\)?/.test(line)) inExecuteBlock = false;
  }
  return count;
}

function safeKey(filePath) {
  return filePath.replace(/[^A-Za-z0-9]/g, '_').toUpperCase();
}

function fileAt(sha, filePath) {
  const mockKey = `MOCK_FILE_${safeKey(filePath)}_${sha === process.env.BASE_SHA ? 'BASE' : 'HEAD'}`;
  if (process.env[mockKey] !== undefined) return process.env[mockKey];
  const r = spawnSync('git', ['show', `${sha}:${filePath}`], { encoding: 'utf8' });
  if (r.status !== 0) return ''; // BASEに存在しない新規ファイル等は空扱い
  return r.stdout || '';
}

function getChangedTestFiles() {
  if (process.env.MOCK_CHANGED_FILES !== undefined) {
    return process.env.MOCK_CHANGED_FILES.split('\n').map(s => s.trim()).filter(Boolean)
      .filter(f => f.startsWith(TESTS_DIR) && f.endsWith('.py') && !EXCLUDE.has(f));
  }
  const base = process.env.BASE_SHA;
  const head = process.env.HEAD_SHA;
  if (!base || !head) {
    console.error('❌ BASE_SHA / HEAD_SHA が設定されていません');
    process.exit(1);
  }
  const out = execSync(`git diff --name-only "${base}...${head}"`, { encoding: 'utf8' }).trim();
  if (!out) return [];
  return out.split('\n').map(s => s.trim())
    .filter(f => f.startsWith(TESTS_DIR) && f.endsWith('.py') && !EXCLUDE.has(f));
}

function main() {
  const base = process.env.BASE_SHA;
  const head = process.env.HEAD_SHA;
  const changed = getChangedTestFiles();

  if (changed.length === 0) {
    console.log('✅ 対象テストファイルの変更なし — スキップ（pass）');
    process.exit(0);
  }

  const offenders = [];
  for (const f of changed) {
    const baseCount = countRealCreateTable(fileAt(base, f));
    const headCount = countRealCreateTable(fileAt(head, f));
    console.log(`[INFO] ${f}: BASE=${baseCount} HEAD=${headCount}`);
    if (headCount > baseCount) {
      offenders.push(`${f}（本物のCREATE TABLE: ${baseCount} → ${headCount}）`);
    }
  }

  if (offenders.length > 0) {
    console.error('');
    console.error('❌ テストに本番テーブル定義の新規コピー（独自 CREATE TABLE）が増えています:');
    for (const o of offenders) console.error(`   ${o}`);
    console.error('');
    console.error('→ 定義は backend/tests/conftest.py に集約してください（柱3・design-pillar3.md）。');
    process.exit(1);
  }

  console.log('✅ テストへの新規スキーマ複製なし（pass）');
  process.exit(0);
}

main();
