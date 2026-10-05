#!/usr/bin/env node
/**
 * test-migration-column-churn.js
 *
 * check-migration-column-churn.js の回帰テスト。
 * 実リポジトリに依存せず、各テストごとに一時ディレクトリに
 * scripts/run_all_migrations.sh 相当 + migrations/*.sql + allowlist を作り、
 * REPO_ROOT_OVERRIDE / MIGRATIONS_SCRIPT_OVERRIDE / ALLOWLIST_OVERRIDE で
 * check-migration-column-churn.js を呼び出す。
 *
 * 実行方法: node scripts/tests/test-migration-column-churn.js
 * 終了コード: 0=全PASS / 1=FAILあり
 */
'use strict';

const assert = require('assert');
const { execSync, spawnSync } = require('child_process');
const { mkdtempSync, mkdirSync, writeFileSync, rmSync } = require('fs');
const { join } = require('path');
const os = require('os');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
const SCRIPT = join(repoRoot, 'scripts/check-migration-column-churn.js');

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

/**
 * fixture: { 'scripts/run_all_migrations.sh': '...', 'migrations/foo.sql': '...', ... }
 * allowlist: array or undefined（undefined の場合は allowlist ファイル自体を作らない＝空扱い）
 */
function makeFixture(files, allowlist) {
  const dir = mkdtempSync(join(os.tmpdir(), 'migration-column-churn-'));
  for (const [relPath, content] of Object.entries(files)) {
    const abs = join(dir, relPath);
    mkdirSync(join(abs, '..'), { recursive: true });
    writeFileSync(abs, content, 'utf8');
  }
  const allowlistPath = join(dir, 'scripts/migration-column-churn-allowlist.json');
  if (allowlist !== undefined) {
    mkdirSync(join(dir, 'scripts'), { recursive: true });
    writeFileSync(allowlistPath, JSON.stringify(allowlist), 'utf8');
  } else {
    mkdirSync(join(dir, 'scripts'), { recursive: true });
    writeFileSync(allowlistPath, '[]', 'utf8');
  }
  return {
    dir,
    migrationsScript: join(dir, 'scripts/run_all_migrations.sh'),
    allowlistPath,
  };
}

function cleanup(dir) {
  rmSync(dir, { recursive: true, force: true });
}

function run(fixture) {
  const result = spawnSync('node', [SCRIPT], {
    encoding: 'utf8',
    env: {
      ...process.env,
      REPO_ROOT_OVERRIDE: fixture.dir,
      MIGRATIONS_SCRIPT_OVERRIDE: fixture.migrationsScript,
      ALLOWLIST_OVERRIDE: fixture.allowlistPath,
    },
  });
  return { code: result.status, stdout: result.stdout || '', stderr: result.stderr || '' };
}

console.log('\n=== migration-column-churn 回帰テスト ===\n');

// (a) add-then-drop → fail
test('(a) add-then-drop は allowlist なしで fail する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add.sql',
      'run_sql migrations/002_drop.sql',
    ].join('\n'),
    'migrations/001_add.sql': 'ALTER TABLE public.foo ADD COLUMN bar INTEGER;\n',
    'migrations/002_drop.sql': 'ALTER TABLE public.foo DROP COLUMN bar;\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(result.stdout.includes('public.foo.bar'), 'churn 対象が出力されていない');
    assert.ok(result.stdout.includes('UNALLOWED'), 'UNALLOWED 表示がない');
  } finally {
    cleanup(fixture.dir);
  }
});

// (b) allowlisted pair → pass
test('(b) allowlist に登録済みの pair は pass する', () => {
  const fixture = makeFixture(
    {
      'scripts/run_all_migrations.sh': [
        'run_sql migrations/001_add.sql',
        'run_sql migrations/002_drop.sql',
      ].join('\n'),
      'migrations/001_add.sql': 'ALTER TABLE public.foo ADD COLUMN bar INTEGER;\n',
      'migrations/002_drop.sql': 'ALTER TABLE public.foo DROP COLUMN bar;\n',
    },
    [{ table: 'public.foo', column: 'bar', reason: 'test', reference: 'TEST-1' }],
  );
  try {
    const result = run(fixture);
    assert.strictEqual(result.code, 0, result.stdout);
    assert.ok(result.stdout.includes('allowlisted'), 'allowlisted 表示がない');
  } finally {
    cleanup(fixture.dir);
  }
});

// (c) stale allowlist → fail
test('(c) 現在の churn に該当しない allowlist エントリは stale で fail する', () => {
  const fixture = makeFixture(
    {
      'scripts/run_all_migrations.sh': ['run_sql migrations/001_only_add.sql'].join('\n'),
      'migrations/001_only_add.sql': 'ALTER TABLE public.foo ADD COLUMN bar INTEGER;\n',
    },
    [{ table: 'public.foo', column: 'bar', reason: 'test', reference: 'TEST-1' }],
  );
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(result.stdout.includes('stale'), 'stale 表示がない');
  } finally {
    cleanup(fixture.dir);
  }
});

// (d) ADD/DROP CONSTRAINT not counted
test('(d) ADD CONSTRAINT / DROP CONSTRAINT はカラムとして数えない', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add_constraint.sql',
      'run_sql migrations/002_drop_constraint.sql',
    ].join('\n'),
    'migrations/001_add_constraint.sql':
      'ALTER TABLE public.foo ADD CONSTRAINT chk_foo CHECK (bar > 0);\n',
    'migrations/002_drop_constraint.sql':
      'ALTER TABLE public.foo DROP CONSTRAINT IF EXISTS chk_foo;\n',
  });
  try {
    const result = run(fixture);
    assert.strictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('churn は検出されませんでした'),
      'CONSTRAINT が誤ってカラムとして検出されている',
    );
  } finally {
    cleanup(fixture.dir);
  }
});

// (e) multi-clause ALTER
test('(e) 1つの ALTER TABLE 内の複数カンマ区切り句を個別に検出する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_multi.sql',
      'run_sql migrations/002_drop_both.sql',
    ].join('\n'),
    'migrations/001_multi.sql':
      'ALTER TABLE public.foo ADD COLUMN a INTEGER, ADD COLUMN b INTEGER, ADD CONSTRAINT chk_a CHECK (a > 0);\n',
    'migrations/002_drop_both.sql':
      'ALTER TABLE public.foo DROP COLUMN a, DROP COLUMN b;\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(result.stdout.includes('public.foo.a'), 'カラム a が検出されていない');
    assert.ok(result.stdout.includes('public.foo.b'), 'カラム b が検出されていない');
  } finally {
    cleanup(fixture.dir);
  }
});

// (f) EXECUTE format with %I
test('(f) EXECUTE format(\'ALTER TABLE %I...\') 内の ADD/DROP COLUMN を検出し tenant.* に正規化する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add_dynamic.sql',
      'run_sql migrations/002_drop_dynamic.sql',
    ].join('\n'),
    'migrations/001_add_dynamic.sql': [
      "DO $$",
      "DECLARE schema_record RECORD;",
      "BEGIN",
      "  FOR schema_record IN SELECT nspname FROM pg_namespace LOOP",
      "    EXECUTE format('ALTER TABLE %I.deals ADD COLUMN IF NOT EXISTS lost_reason_code VARCHAR(30)', schema_record.nspname);",
      "  END LOOP;",
      "END $$;",
    ].join('\n'),
    'migrations/002_drop_dynamic.sql': [
      "DO $$",
      "DECLARE schema_record RECORD;",
      "BEGIN",
      "  FOR schema_record IN SELECT nspname FROM pg_namespace LOOP",
      "    EXECUTE format('ALTER TABLE %I.deals DROP COLUMN IF EXISTS lost_reason_code', schema_record.nspname);",
      "  END LOOP;",
      "END $$;",
    ].join('\n'),
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('tenant.deals.lost_reason_code'),
      '%I.deals が tenant.deals に正規化されて検出されていない',
    );
  } finally {
    cleanup(fixture.dir);
  }
});

// (g) run_py reading a SQL file
test('(g) run_py が読む .sql ファイルの ADD/DROP COLUMN も検出する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_py  scripts/migrate_fixture.py',
      'run_sql migrations/999_drop_later.sql',
    ].join('\n'),
    'scripts/migrate_fixture.py': [
      'from pathlib import Path',
      'BASE_DIR = Path(__file__).resolve().parent.parent',
      'MIGRATIONS_DIR = BASE_DIR / "migrations"',
      'tmpl = (MIGRATIONS_DIR / "900_add_via_py.sql").read_text("utf-8")',
    ].join('\n'),
    'migrations/900_add_via_py.sql': 'ALTER TABLE public.widgets ADD COLUMN gizmo TEXT;\n',
    'migrations/999_drop_later.sql': 'ALTER TABLE public.widgets DROP COLUMN gizmo;\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('public.widgets.gizmo'),
      'run_py 経由で参照された .sql のカラムが検出されていない',
    );
  } finally {
    cleanup(fixture.dir);
  }
});

// (h) drop-then-add warning
test('(h) drop-then-add は警告として出力されるが exit 0 を維持する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': ['run_sql migrations/001_drop_then_add.sql'].join('\n'),
    'migrations/001_drop_then_add.sql': [
      'ALTER TABLE public.foo DROP COLUMN bar;',
      'ALTER TABLE public.foo ADD COLUMN bar INTEGER;',
    ].join('\n'),
  });
  try {
    const result = run(fixture);
    assert.strictEqual(result.code, 0, result.stdout);
    assert.ok(result.stdout.includes('drop-then-add 警告'), '警告メッセージが出ていない');
    assert.ok(result.stdout.includes('public.foo.bar'), '対象カラムが出力されていない');
  } finally {
    cleanup(fixture.dir);
  }
});

// (i) 引用識別子のカラム名
test('(i) ADD COLUMN "Col" / DROP COLUMN "Col" は大小文字を保持して検出する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add_quoted_col.sql',
      'run_sql migrations/002_drop_quoted_col.sql',
    ].join('\n'),
    'migrations/001_add_quoted_col.sql': 'ALTER TABLE public.foo ADD COLUMN "Col" INTEGER;\n',
    'migrations/002_drop_quoted_col.sql': 'ALTER TABLE public.foo DROP COLUMN "Col";\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('public.foo.Col'),
      '引用カラム名が大小文字保持で検出されていない（COLUMN キーワード誤検出の可能性）',
    );
    assert.ok(!result.stdout.includes('public.foo.column'), 'COLUMN キーワードを列名として誤検出している');
  } finally {
    cleanup(fixture.dir);
  }
});

// (j) 引用識別子のテーブル名
test('(j) public."Tbl" のような引用テーブル名を大小文字保持で正規化する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add_quoted_table.sql',
      'run_sql migrations/002_drop_quoted_table.sql',
    ].join('\n'),
    'migrations/001_add_quoted_table.sql': 'ALTER TABLE public."Tbl" ADD COLUMN bar INTEGER;\n',
    'migrations/002_drop_quoted_table.sql': 'ALTER TABLE public."Tbl" DROP COLUMN bar;\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('public.Tbl.bar'),
      '引用テーブル名が大小文字保持で正規化されていない',
    );
  } finally {
    cleanup(fixture.dir);
  }
});

// (k) 単一引用符リテラル内の -- が同一行の後続の実コードを巻き込まない
test('(k) 単一引用符リテラル内の -- の後、同一行の実際の ADD を検出する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add_after_literal_dashdash.sql',
      'run_sql migrations/002_drop_secret_col.sql',
    ].join('\n'),
    'migrations/001_add_after_literal_dashdash.sql':
      "ALTER TABLE public.decoy ADD COLUMN label TEXT DEFAULT 'oops -- not a comment'; ALTER TABLE public.secret_table ADD COLUMN secret_col INTEGER;\n",
    'migrations/002_drop_secret_col.sql':
      'ALTER TABLE public.secret_table DROP COLUMN secret_col;\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('public.secret_table.secret_col'),
      'リテラル内の -- に巻き込まれて同一行後続の ADD が消えている',
    );
  } finally {
    cleanup(fixture.dir);
  }
});

// (l) EXECUTE format 文字列（dollar-quote）内の -- が同一行の後続の実コードを巻き込まない
test('(l) EXECUTE format 文字列内の -- の後、同一行の実際の ADD を検出する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add_exec_format_dashdash.sql',
      'run_sql migrations/002_drop_trailing_col.sql',
    ].join('\n'),
    'migrations/001_add_exec_format_dashdash.sql': [
      'DO $$',
      'BEGIN',
      "  EXECUTE format('ALTER TABLE %I.widgets ADD COLUMN gizmo TEXT -- inline note, not a real comment', 'tenant_001'); EXECUTE format('ALTER TABLE %I.after_block ADD COLUMN trailing_col INTEGER', 'tenant_001');",
      'END $$;',
    ].join('\n'),
    'migrations/002_drop_trailing_col.sql':
      'ALTER TABLE tenant_001.after_block DROP COLUMN trailing_col;\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('tenant.after_block.trailing_col'),
      'EXECUTE format 文字列内の -- に巻き込まれて同一行後続の EXECUTE が消えている',
    );
  } finally {
    cleanup(fixture.dir);
  }
});

// (m) 単一引用符リテラル内の /* */ が同一行の後続の実コードを巻き込まない
test('(m) 単一引用符リテラル内の /* */ の後、同一行の実際の ADD を検出する', () => {
  const fixture = makeFixture({
    'scripts/run_all_migrations.sh': [
      'run_sql migrations/001_add_after_literal_blockcomment.sql',
      'run_sql migrations/002_drop_secret_col2.sql',
    ].join('\n'),
    'migrations/001_add_after_literal_blockcomment.sql':
      "ALTER TABLE public.decoy2 ADD COLUMN label TEXT DEFAULT '/* not a real comment */ trailing'; ALTER TABLE public.secret_table2 ADD COLUMN secret_col2 INTEGER;\n",
    'migrations/002_drop_secret_col2.sql':
      'ALTER TABLE public.secret_table2 DROP COLUMN secret_col2;\n',
  });
  try {
    const result = run(fixture);
    assert.notStrictEqual(result.code, 0, result.stdout);
    assert.ok(
      result.stdout.includes('public.secret_table2.secret_col2'),
      'リテラル内の /* */ に巻き込まれて同一行後続の ADD が消えている',
    );
  } finally {
    cleanup(fixture.dir);
  }
});

if (failed > 0) {
  console.error(`\n${passed} passed, ${failed} failed`);
  process.exit(1);
}

console.log(`\n${passed} passed, ${failed} failed`);
