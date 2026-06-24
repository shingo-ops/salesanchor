#!/usr/bin/env node
/**
 * test-dangling-routes.js
 *
 * scripts/check-dangling-routes.js の planted violation テスト。
 * MOCK_BACKEND_BASE / MOCK_BACKEND_HEAD / MOCK_FRONTEND_REFS 環境変数で
 * git への依存なしにアルゴリズムを検証する。
 *
 * 3ケース:
 *   KPI1: weekly-advisor-defensive 削除 × フロント参照あり → exit 1 (赤)
 *   KPI2: 未参照ルート削除               × フロント参照なし → exit 0 (緑)
 *   KPI3: ルート削除なし（追加のみ）                        → exit 0 (緑)
 *
 * CI から: node scripts/tests/test-dangling-routes.js
 */

'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const SCRIPT = path.resolve(__dirname, '..', 'check-dangling-routes.js');

// ---------------------------------------------------------------------------
// ヘルパー
// ---------------------------------------------------------------------------

function runWithMock({ baseRoutes, headRoutes, frontendRefs }) {
  const env = {
    ...process.env,
    MOCK_BACKEND_BASE: JSON.stringify(baseRoutes),
    MOCK_BACKEND_HEAD: JSON.stringify(headRoutes),
    MOCK_FRONTEND_REFS: JSON.stringify(frontendRefs),
    // SHA は不要（MOCK_* が優先される）
    BASE_SHA: 'mock-base',
    HEAD_SHA: 'mock-head',
  };

  const result = spawnSync('node', [SCRIPT], {
    env,
    encoding: 'utf8',
  });

  return {
    exitCode: result.status,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
  };
}

let passed = 0;
let failed = 0;

function assert(label, condition, detail = '') {
  if (condition) {
    console.log(`  ✅ PASS: ${label}`);
    passed++;
  } else {
    console.error(`  ❌ FAIL: ${label}${detail ? ' — ' + detail : ''}`);
    failed++;
  }
}

// ---------------------------------------------------------------------------
// KPI1: weekly-advisor-defensive 削除 × フロント参照あり → exit 1 (赤)
// ---------------------------------------------------------------------------
console.log('\n[KPI1] weekly-advisor-defensive 削除 × フロント参照あり → exit 1 (赤)');

{
  // BASE にはルートあり、HEAD からは削除済み
  const BASE_ROUTES = [
    '/api/v1/analytics/weekly-advisor-defensive',
    '/api/v1/analytics/funnel',
    '/api/v1/leads',
  ];
  const HEAD_ROUTES = [
    // /analytics/weekly-advisor-defensive が HEAD で削除された
    '/api/v1/analytics/funnel',
    '/api/v1/leads',
  ];
  // フロントエンドは weekly-advisor-defensive を参照している（funnel.ts:210 相当）
  const FRONTEND_REFS = [
    '/api/v1/analytics/weekly-advisor-defensive',
    '/api/v1/analytics/funnel',
    '/api/v1/analytics/priority-prospects',
  ];

  const { exitCode, stderr } = runWithMock({
    baseRoutes: BASE_ROUTES,
    headRoutes: HEAD_ROUTES,
    frontendRefs: FRONTEND_REFS,
  });

  assert('exit code は 1', exitCode === 1, `actual: ${exitCode}`);
  assert(
    'stderr に dangling route が表示される',
    stderr.includes('/api/v1/analytics/weekly-advisor-defensive'),
    `stderr: ${stderr.slice(0, 200)}`
  );
}

// ---------------------------------------------------------------------------
// KPI2: 未参照ルート削除 × フロント参照なし → exit 0 (緑)
// ---------------------------------------------------------------------------
console.log('\n[KPI2] 未参照ルート削除 × フロント参照なし → exit 0 (緑)');

{
  const BASE_ROUTES = [
    '/api/v1/analytics/legacy-unused-endpoint',
    '/api/v1/analytics/funnel',
    '/api/v1/leads',
  ];
  const HEAD_ROUTES = [
    // /analytics/legacy-unused-endpoint を削除（フロントから参照なし）
    '/api/v1/analytics/funnel',
    '/api/v1/leads',
  ];
  const FRONTEND_REFS = [
    // legacy-unused-endpoint への参照はない
    '/api/v1/analytics/funnel',
    '/api/v1/analytics/priority-prospects',
    '/api/v1/leads',
  ];

  const { exitCode, stdout } = runWithMock({
    baseRoutes: BASE_ROUTES,
    headRoutes: HEAD_ROUTES,
    frontendRefs: FRONTEND_REFS,
  });

  assert('exit code は 0', exitCode === 0, `actual: ${exitCode}`);
  assert(
    'stdout に "dangling route なし" が含まれる',
    stdout.includes('dangling route なし'),
    `stdout: ${stdout.slice(0, 200)}`
  );
}

// ---------------------------------------------------------------------------
// KPI3: ルート削除なし（追加のみ） → exit 0 (緑)
// ---------------------------------------------------------------------------
console.log('\n[KPI3] ルート削除なし（追加のみ） → exit 0 (緑)');

{
  const BASE_ROUTES = [
    '/api/v1/analytics/funnel',
    '/api/v1/leads',
  ];
  const HEAD_ROUTES = [
    // HEAD では新規ルートが追加されるのみ、削除はない
    '/api/v1/analytics/funnel',
    '/api/v1/leads',
    '/api/v1/analytics/new-feature-endpoint',
  ];
  const FRONTEND_REFS = [
    '/api/v1/analytics/funnel',
    '/api/v1/analytics/priority-prospects',
  ];

  const { exitCode, stdout } = runWithMock({
    baseRoutes: BASE_ROUTES,
    headRoutes: HEAD_ROUTES,
    frontendRefs: FRONTEND_REFS,
  });

  assert('exit code は 0', exitCode === 0, `actual: ${exitCode}`);
  assert(
    'stdout に "dangling route なし" が含まれる',
    stdout.includes('dangling route なし'),
    `stdout: ${stdout.slice(0, 200)}`
  );
}

// ---------------------------------------------------------------------------
// 結果サマリ
// ---------------------------------------------------------------------------
console.log(`\n========================================`);
console.log(`テスト結果: ${passed} passed, ${failed} failed`);
console.log(`========================================`);

if (failed > 0) {
  process.exit(1);
}
process.exit(0);
