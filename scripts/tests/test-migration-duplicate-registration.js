#!/usr/bin/env node
/**
 * test-migration-duplicate-registration.js
 *
 * check-migration-duplicate-registration.sh の回帰テスト
 *
 * 実行方法: node scripts/tests/test-migration-duplicate-registration.js
 * 終了コード: 0=全PASS / 1=FAILあり
 */
'use strict';

const assert = require('assert');
const { execSync, spawnSync } = require('child_process');
const { mkdtempSync, cpSync, writeFileSync, rmSync } = require('fs');
const { join } = require('path');
const os = require('os');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
const SCRIPT = join(repoRoot, 'scripts/check-migration-duplicate-registration.sh');
const MIGRATIONS_SCRIPT = join(repoRoot, 'scripts/run_all_migrations.sh');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✅ ${name}`);
    passed += 1;
  } catch (error) {
    console.error(`  ❌ ${name}`);
    console.error(`     ${error.message}`);
    failed += 1;
  }
}

function runChecker(migrationsScript) {
  const result = spawnSync('bash', [SCRIPT, '--migrations-script', migrationsScript], {
    encoding: 'utf8',
    env: { ...process.env },
  });
  return { code: result.status, stdout: result.stdout || '', stderr: result.stderr || '' };
}

function makeTempMigrationsScript(extraLines) {
  const dir = mkdtempSync(join(os.tmpdir(), 'migration-duplicate-registration-'));
  const target = join(dir, 'run_all_migrations.sh');
  cpSync(MIGRATIONS_SCRIPT, target);
  if (extraLines && extraLines.length > 0) {
    writeFileSync(target, `\n${extraLines.join('\n')}\n`, { flag: 'a' });
  }
  return { dir, target };
}

function cleanupTemp(dir) {
  rmSync(dir, { recursive: true, force: true });
}

console.log('\n=== migration-duplicate-registration 回帰テスト ===\n');

test('正常系: 実リポジトリの run_all_migrations.sh に重複登録がない', () => {
  const result = runChecker(MIGRATIONS_SCRIPT);
  assert.strictEqual(result.code, 0, result.stderr || result.stdout);
  assert.ok(result.stdout.includes('二重登録なし'), '成功メッセージが出ていない');
});

test('異常系: 同一パスを2回登録すると fail し、パス名を出す', () => {
  const tmp = makeTempMigrationsScript([
    'run_sql migrations/999_dup_test_fixture_only.sql',
    'run_sql migrations/999_dup_test_fixture_only.sql',
  ]);
  try {
    const result = runChecker(tmp.target);
    assert.notStrictEqual(result.code, 0, '重複時に exit 0 になっている');
    assert.ok(
      result.stdout.includes('MIGRATION DUPLICATE REGISTRATION CHECK FAILED'),
      '失敗メッセージが出ていない',
    );
    assert.ok(
      result.stdout.includes('999_dup_test_fixture_only.sql'),
      '重複ファイル名が出力されていない',
    );
  } finally {
    cleanupTemp(tmp.dir);
  }
});

test('異常系: run_py の重複も検出する', () => {
  const tmp = makeTempMigrationsScript([
    'run_py  scripts/dup_test_fixture_only.py',
    'run_py  scripts/dup_test_fixture_only.py',
  ]);
  try {
    const result = runChecker(tmp.target);
    assert.notStrictEqual(result.code, 0, '重複時に exit 0 になっている');
    assert.ok(
      result.stdout.includes('dup_test_fixture_only.py'),
      'run_py 重複ファイル名が出力されていない',
    );
  } finally {
    cleanupTemp(tmp.dir);
  }
});

if (failed > 0) {
  console.error(`\n${passed} passed, ${failed} failed`);
  process.exit(1);
}

console.log(`\n${passed} passed, ${failed} failed`);
