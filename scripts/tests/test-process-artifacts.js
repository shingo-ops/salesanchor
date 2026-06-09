#!/usr/bin/env node
/**
 * test-process-artifacts.js
 *
 * process-artifacts gate（check-process-artifacts.js）の受け入れ基準テスト
 * docs/handoff/sop-kpi2/design.md §7 対応
 *
 * 実行方法: node scripts/tests/test-process-artifacts.js
 * 終了コード: 0=全PASS / 1=FAILあり
 */
'use strict';

const { execSync, spawnSync } = require('child_process');
const { writeFileSync, mkdirSync, rmSync, existsSync } = require('fs');
const { join } = require('path');
const assert = require('assert');
const path = require('path');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
const SCRIPT = join(repoRoot, 'scripts/check-process-artifacts.js');

// ─── テスト用モジュール直接インポート ────────────────────────────────────────
const {
  classifyFile,
  classifyChanges,
  parseSOPDeclaration,
  hasFileCitations,
  validateFileCitations,
  validateDesignDoc,
} = require(SCRIPT);

// ─── テストユーティリティ ─────────────────────────────────────────────────────
let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✅ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ❌ ${name}`);
    console.error(`     ${e.message}`);
    failed++;
  }
}

function runScript(env = {}) {
  const result = spawnSync('node', [SCRIPT], {
    env: { ...process.env, ...env },
    encoding: 'utf8',
  });
  return { code: result.status, stdout: result.stdout, stderr: result.stderr };
}

// ─── 一時ファイル管理 ─────────────────────────────────────────────────────────
const TMP = join(repoRoot, 'docs/handoff/_test_tmp');

function setupTmp() {
  mkdirSync(TMP, { recursive: true });
}

function cleanupTmp() {
  if (existsSync(TMP)) rmSync(TMP, { recursive: true, force: true });
}

function writeTmp(name, content) {
  const p = join(TMP, name);
  mkdirSync(path.dirname(p), { recursive: true });
  writeFileSync(p, content, 'utf8');
  return p.replace(repoRoot + '/', '');
}

// ─── フィクスチャ ─────────────────────────────────────────────────────────────

/** 存在するファイル/行のfile:line引用を含む正常なrecon */
function validReconContent(filePath, lineNum) {
  return `# recon — test\n**対象ADR**: ADR-999\n\n## file:line 引用表\n| 引用先 | 確認内容 |\n|---|---|\n| \`${filePath}:${lineNum}\` | 確認済み |\n\n## 不明点リスト\n未解決ゼロ確認: 該当なし\n`;
}

/** 設計docの正常形 */
function validDesignContent(reconPath, adr) {
  return `# 設計 — test\n**対象ADR**: ${adr}\n**recon**: ${reconPath}\n\n## 外部・過去事例の参照と我々への応用\n該当なし：今回は小規模修正のため外部事例は不要と判断\n\n## 受け入れ基準\n| 基準 | 検証方法 |\n|---|---|\n| テストが通る | pytest tests/test_xxx.py |\n`;
}

// ─── テストスイート ───────────────────────────────────────────────────────────

console.log('\n=== process-artifacts gate テスト（design.md §7）===\n');

// ── ユニットテスト: パス区分 ──────────────────────────────────────────────────
console.log('【パス区分テスト】');

test('docs/以下は docs 区分', () => {
  assert.strictEqual(classifyFile('docs/adr/ADR-001.md'), 'docs');
});

test('.md ファイルは docs 区分', () => {
  assert.strictEqual(classifyFile('README.md'), 'docs');
  assert.strictEqual(classifyFile('CLAUDE.md'), 'docs');
});

test('migrations/ は dangerous 区分', () => {
  assert.strictEqual(classifyFile('migrations/001_add_table.sql'), 'dangerous');
});

test('deploy.yml は dangerous 区分', () => {
  assert.strictEqual(classifyFile('.github/workflows/deploy.yml'), 'dangerous');
});

test('aeon-dispatch.sh は dangerous 区分', () => {
  assert.strictEqual(classifyFile('scripts/aeon-dispatch.sh'), 'dangerous');
});

test('frontend/src/ は real-code 区分', () => {
  assert.strictEqual(classifyFile('frontend/src/App.tsx'), 'real-code');
});

test('backend/app/ は real-code 区分', () => {
  assert.strictEqual(classifyFile('backend/app/main.py'), 'real-code');
});

test('未知のパスは unknown（安全側）', () => {
  assert.strictEqual(classifyFile('some/unknown/path.xyz'), 'unknown');
});

test('書類のみのリストは hasDocsOnly=true', () => {
  const { hasDocsOnly } = classifyChanges(['docs/adr/ADR-001.md', 'CLAUDE.md']);
  assert.ok(hasDocsOnly);
});

test('コードを含む場合は hasDocsOnly=false', () => {
  const { hasDocsOnly } = classifyChanges(['docs/adr/ADR-001.md', 'frontend/src/App.tsx']);
  assert.ok(!hasDocsOnly);
});

// ── ユニットテスト: PR 本文パース ─────────────────────────────────────────────
console.log('\n【PR本文パーステスト】');

test('標準ワークフロー確認セクションをパース', () => {
  const body = `## なぜ\nテスト\n\n### 標準ワークフロー確認\n- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n- 対象ADR: ADR-123\n- recon: docs/handoff/my-job/recon.md\n- 設計: docs/handoff/my-job/design.md\n`;
  const d = parseSOPDeclaration(body);
  assert.ok(d, 'declaration が null');
  assert.strictEqual(d.adr, 'ADR-123');
  assert.strictEqual(d.reconPath, 'docs/handoff/my-job/recon.md');
  assert.strictEqual(d.designPath, 'docs/handoff/my-job/design.md');
  assert.strictEqual(d.isExempt, false);
});

test('免除チェック済みを検出', () => {
  const body = `### 標準ワークフロー確認\n- [x] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n`;
  const d = parseSOPDeclaration(body);
  assert.ok(d && d.isExempt);
});

test('緊急モードを検出', () => {
  const body = `### 標準ワークフロー確認\n- 対象ADR: ADR-1\n- recon: docs/handoff/x/recon.md\n- 設計: docs/handoff/x/design.md\n- （危ない変更の特例時）モード: 緊急 ＋ 承認者: shingo-ops\n`;
  const d = parseSOPDeclaration(body);
  assert.ok(d && d.mode === '緊急');
});

test('セクションがない場合は null', () => {
  const d = parseSOPDeclaration('## なぜ\nなし\n');
  assert.strictEqual(d, null);
});

// ── ユニットテスト: file:line 引用検証 ───────────────────────────────────────
console.log('\n【file:line引用テスト】');

test('有効なfile:line引用は引用ありと判定', () => {
  const content = '| `backend/app/main.py:1` | 確認済み |';
  assert.ok(hasFileCitations(content));
});

test('引用のないreconは hasFileCitations=false', () => {
  assert.ok(!hasFileCitations('# recon\n## 引用表\n| なし |'));
});

test('存在するファイル・有効な行番号は validateFileCitations がエラーなし', () => {
  // SCRIPT ファイル自体を引用（確実に存在する）
  const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
  const content = `| \`${scriptRelPath}:1\` | 確認済み |`;
  const errors = validateFileCitations(content);
  assert.deepStrictEqual(errors, []);
});

// ── §7 受け入れ基準 AC1: 偽のfile:lineはfail ─────────────────────────────────
console.log('\n【§7 受け入れ基準テスト】');

test('AC1: 偽のfile:line（存在しないファイル）を含むreconはfail', () => {
  const content = '| `nonexistent/fake/file.py:42` | テスト |';
  const errors = validateFileCitations(content);
  assert.ok(errors.length > 0, 'エラーが返るべき');
  assert.ok(errors[0].includes('存在しません'));
});

test('AC1: 偽のfile:line（存在しない行番号）を含むreconはfail', () => {
  // 存在するファイルだが行番号が明らかに大きすぎる
  const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
  const content = `| \`${scriptRelPath}:999999\` | テスト |`;
  const errors = validateFileCitations(content);
  assert.ok(errors.length > 0, 'エラーが返るべき');
  assert.ok(errors[0].includes('範囲外'));
});

// ── §7 AC2: 外部・過去事例欄が空欄の設計はfail ──────────────────────────────
test('AC2: 「外部・過去事例と応用」欄が空欄の設計はfail', () => {
  const content = `# 設計\n**対象ADR**: ADR-1\n**recon**: docs/handoff/x/recon.md\n\n## 外部・過去事例の参照と我々への応用\n\n\n## 受け入れ基準\n| 基準 | 検証方法 |\n|---|---|\n| テスト | pytest |\n`;
  const errors = validateDesignDoc(content, 'docs/handoff/x/recon.md', 'ADR-1');
  assert.ok(errors.some(e => e.includes('外部') && e.includes('空欄')));
});

test('AC2: 「外部・過去事例と応用」欄セクション自体が無い場合もfail', () => {
  const content = `# 設計\n## 受け入れ基準\n| 基準 | 検証方法 |\n|---|---|\n| テスト | pytest |\n`;
  const errors = validateDesignDoc(content, null, null);
  assert.ok(errors.some(e => e.includes('外部')));
});

// ── §7 AC3: 検証リンク無しの受入基準はfail ───────────────────────────────────
test('AC3: 検証方法が空の受け入れ基準はfail', () => {
  const content = `# 設計\n**対象ADR**: ADR-1\n**recon**: docs/handoff/x/recon.md\n\n## 外部・過去事例の参照と我々への応用\n該当なし：テスト\n\n## 受け入れ基準\n| 基準 | 検証方法 |\n|---|---|\n| テストが通る | |\n`;
  const errors = validateDesignDoc(content, 'docs/handoff/x/recon.md', 'ADR-1');
  assert.ok(errors.some(e => e.includes('検証方法が空')));
});

// ── §7 AC4: 危ない変更で承認なしは本検査を要求 ───────────────────────────────
test('AC4: 危ない変更＋承認なし → 本検査（fail with missing artifacts）', () => {
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_APPROVALS: '',
    MOCK_PR_BODY: '',
  });
  assert.notStrictEqual(result.code, 0, '本検査でfailするべき（exit != 0）');
  assert.ok(
    result.stderr.includes('PROCESS ARTIFACTS GATE FAILED') ||
    result.stderr.includes('標準ワークフロー確認'),
    '本検査のfailメッセージが出るべき'
  );
});

test('AC4: 危ない変更で自己申告免除"だけ"はfail', () => {
  const body = `### 標準ワークフロー確認\n- [x] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n`;
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_APPROVALS: '',
    MOCK_PR_BODY: body,
  });
  // 免除は honorされず本検査になる → PR本文が不完全でfail
  assert.notStrictEqual(result.code, 0);
});

// ── §7 AC5: 緊急承認PRはpass＋宿題待ち起票 ──────────────────────────────────
test('AC5: 緊急承認PRはpass（issue起票はPR_NUMBER未設定時にスキップ）', () => {
  const body = `### 標準ワークフロー確認\n- 対象ADR: ADR-1\n- recon: docs/handoff/x/recon.md\n- 設計: docs/handoff/x/design.md\n- （危ない変更の特例時）モード: 緊急 ＋ 承認者: shingo-ops\n`;
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_APPROVALS: 'shingo-ops',
    MOCK_PR_BODY: body,
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
  assert.ok(result.stdout.includes('緊急承認') || result.stdout.includes('pass'));
});

// ── §7 AC6: 書類のみPRは自動スキップ ────────────────────────────────────────
test('AC6: 書類のみのPRは自動スキップ（pass）', () => {
  const result = runScript({
    CHANGED_FILES: 'docs/adr/ADR-001.md\nCLAUDE.md\nREADME.md',
    MOCK_PR_BODY: '',
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
  assert.ok(result.stdout.includes('自動スキップ'));
});

// ── 統合テスト: 正常系（完全な成果物）────────────────────────────────────────
console.log('\n【統合テスト】');

test('正常系: 実在するrecon＋設計doc → pass', () => {
  setupTmp();
  try {
    // 実在するファイルを引用
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1);
    const reconRelPath = writeTmp('test-job/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-999');
    const designRelPath = writeTmp('test-job/design.md', designContent);

    const body = `### 標準ワークフロー確認\n- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n- 対象ADR: ADR-999\n- recon: ${reconRelPath}\n- 設計: ${designRelPath}\n`;

    const result = runScript({
      CHANGED_FILES: 'frontend/src/App.tsx',
      MOCK_PR_BODY: body,
    });
    assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
    assert.ok(result.stdout.includes('PASSED'));
  } finally {
    cleanupTmp();
  }
});

test('免除宣言のある低リスクPRはpass', () => {
  const body = `### 標準ワークフロー確認\n- [x] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n`;
  const result = runScript({
    CHANGED_FILES: 'backend/app/main.py',
    MOCK_PR_BODY: body,
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
  assert.ok(result.stdout.includes('免除'));
});

// ─── 結果集計 ─────────────────────────────────────────────────────────────────
console.log(`\n${'='.repeat(50)}`);
console.log(`テスト結果: ✅ ${passed} PASS / ❌ ${failed} FAIL`);
if (failed > 0) {
  console.error('FAILED');
  process.exit(1);
} else {
  console.log('ALL PASSED');
  process.exit(0);
}
