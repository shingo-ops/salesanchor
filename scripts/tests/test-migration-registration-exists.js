#!/usr/bin/env node
/**
 * test-migration-registration-exists.js
 *
 * check-migration-registration-exists.sh の回帰テスト
 *
 * 実行方法: node scripts/tests/test-migration-registration-exists.js
 * 終了コード: 0=全PASS / 1=FAILあり
 */
'use strict';

const assert = require('assert');
const { execSync, spawnSync } = require('child_process');
const { mkdtempSync, cpSync, writeFileSync, rmSync } = require('fs');
const { join } = require('path');
const os = require('os');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
const SCRIPT = join(repoRoot, 'scripts/check-migration-registration-exists.sh');
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

function runChecker({ mode = 'host', repoRootArg = repoRoot, migrationsScript = MIGRATIONS_SCRIPT, backendContainer } = {}) {
  const args = [SCRIPT, '--mode', mode, '--repo-root', repoRootArg, '--migrations-script', migrationsScript];
  if (backendContainer) {
    args.push('--backend-container', backendContainer);
  }
  const result = spawnSync('bash', args, {
    encoding: 'utf8',
    env: { ...process.env },
  });
  return {
    code: result.status,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
  };
}

function makeTempMigrationsScript(extraLines) {
  const dir = mkdtempSync(join(os.tmpdir(), 'migration-registration-exists-'));
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

console.log('\n=== migration-registration-exists 回帰テスト ===\n');

test('正常系: 実リポジトリの登録ファイルが全件揃っている', () => {
  const result = runChecker();
  assert.strictEqual(result.code, 0, result.stderr || result.stdout);
  assert.ok(result.stdout.includes('preflight OK'), 'preflight OK が出力されていない');
});

test('異常系: 欠品が 1 件あると fail し、欠品名を出す', () => {
  const tmp = makeTempMigrationsScript(['run_py  scripts/does_not_exist.py']);
  try {
    const result = runChecker({ migrationsScript: tmp.target });
    assert.notStrictEqual(result.code, 0, '欠品時に exit 0 になっている');
    assert.ok(
      result.stdout.includes('MIGRATION REGISTRATION EXISTENCE CHECK FAILED'),
      '失敗メッセージが出ていない',
    );
    assert.ok(
      result.stdout.includes('run_py') && result.stdout.includes('does_not_exist.py'),
      '欠品ファイル名が出力されていない',
    );
  } finally {
    cleanupTemp(tmp.dir);
  }
});

test('異常系: 複数欠品を全件列挙する', () => {
  const tmp = makeTempMigrationsScript([
    'run_py  scripts/does_not_exist_a.py',
    'run_sql migrations/does_not_exist_b.sql',
  ]);
  try {
    const result = runChecker({ migrationsScript: tmp.target });
    assert.notStrictEqual(result.code, 0, '複数欠品時に exit 0 になっている');
    assert.ok(
      result.stdout.includes('MIGRATION REGISTRATION EXISTENCE CHECK FAILED'),
      '失敗メッセージが出ていない',
    );
    assert.ok(
      result.stdout.includes('does_not_exist_a.py'),
      'run_py 欠品が列挙されていない',
    );
    assert.ok(
      result.stdout.includes('does_not_exist_b.sql'),
      'run_sql 欠品が列挙されていない',
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
