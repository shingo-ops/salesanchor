#!/usr/bin/env node
/**
 * test-check-test-schema-dup.js
 * scripts/check-test-schema-dup.js の planted violation テスト（柱3-e）。
 * MOCK_CHANGED_FILES と MOCK_FILE_*_BASE/_HEAD で git 非依存に検証。
 */
'use strict';
const { spawnSync } = require('child_process');
const path = require('path');
const SCRIPT = path.resolve(__dirname, '..', 'check-test-schema-dup.js');

let passed = 0, failed = 0;
function check(label, cond, detail = '') {
  if (cond) { console.log(`  PASS: ${label}`); passed++; }
  else { console.error(`  FAIL: ${label}${detail ? ' — ' + detail : ''}`); failed++; }
}
function safeKey(p) { return p.replace(/[^A-Za-z0-9]/g, '_').toUpperCase(); }
function run(changed, files) {
  const env = { ...process.env, BASE_SHA: 'mock-base', HEAD_SHA: 'mock-head',
    MOCK_CHANGED_FILES: changed.join('\n') };
  for (const [p, v] of Object.entries(files)) {
    env[`MOCK_FILE_${safeKey(p)}_BASE`] = v.base;
    env[`MOCK_FILE_${safeKey(p)}_HEAD`] = v.head;
  }
  const r = spawnSync('node', [SCRIPT], { env, encoding: 'utf8' });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

const REAL_DDL_BASE = 'async def s(conn):\n    await conn.execute(text("""\n        CREATE TABLE IF NOT EXISTS leads (id INT)\n    """))\n';
const REAL_DDL_ADD = REAL_DDL_BASE + '    await conn.execute(text("""\n        CREATE TABLE IF NOT EXISTS staff (id INT)\n    """))\n';
const TRAP = 'def test_x():\n    sql = "CREATE TABLE foo (id INT)"\n    assert "CREATE TABLE a" in sql\n';

// 1: 本物の複製を新規追加 → 赤
let r1 = run(['backend/tests/test_x.py'],
  { 'backend/tests/test_x.py': { base: REAL_DDL_BASE, head: REAL_DDL_ADD } });
check('充足版: 本物のCREATE TABLE新規追加で赤(exit1)', r1.code === 1, `code=${r1.code}`);

// 2: 罠（sql=/assert）を追加しても複製ではない → 緑
let r2 = run(['backend/tests/test_x.py'],
  { 'backend/tests/test_x.py': { base: REAL_DDL_BASE, head: REAL_DDL_BASE + TRAP } });
check('罠版: sql=/assert追加は複製でない→緑(exit0)', r2.code === 0, `code=${r2.code}`);

// 3: 変更なし（同一）→ 緑
let r3 = run(['backend/tests/test_x.py'],
  { 'backend/tests/test_x.py': { base: REAL_DDL_BASE, head: REAL_DDL_BASE } });
check('不変版: 増減なし→緑(exit0)', r3.code === 0, `code=${r3.code}`);

// 4: conftest.py は対象外 → 緑
let r4 = run(['backend/tests/conftest.py'],
  { 'backend/tests/conftest.py': { base: REAL_DDL_BASE, head: REAL_DDL_ADD } });
check('除外版: conftest.pyは対象外→緑(exit0)', r4.code === 0, `code=${r4.code}`);

// 5: プレースホルダ {schema} の本物追加 → 赤（変種取りこぼさない・柱3-b）
const PH_BASE = 'async def s(conn):\n    await conn.execute(text(f"""\n        CREATE TABLE IF NOT EXISTS {schema}.leads (id INT)\n    """))\n';
const PH_ADD = PH_BASE + '    await conn.execute(text(f"""\n        CREATE TABLE IF NOT EXISTS {schema}.staff (id INT)\n    """))\n';
let r5 = run(['backend/tests/test_ph.py'],
  { 'backend/tests/test_ph.py': { base: PH_BASE, head: PH_ADD } });
check('変種版: プレースホルダ{schema}の複製追加で赤(exit1)', r5.code === 1, `code=${r5.code}`);

console.log('');
console.log(`結果: PASS=${passed} FAIL=${failed}`);
if (failed === 0) console.log('ALL PASS');
process.exit(failed === 0 ? 0 : 1);
