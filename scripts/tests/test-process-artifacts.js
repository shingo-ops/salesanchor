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
  parseGORecord,
  validateGORecord,
  normalizeCitationPath,
  extractFileCitations,
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

/** 正常なGO記録セクション */
function validGORecordSection(prNumber) {
  return `### GO記録\n- GO発行者: Shingo（shingo-ops）\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #${prNumber}\n- バックアップ確認: あり\n`;
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

test('scripts/ は dangerous 区分', () => {
  assert.strictEqual(classifyFile('scripts/aeon-dispatch.sh'), 'dangerous');
  assert.strictEqual(classifyFile('scripts/check-process-artifacts.js'), 'dangerous');
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

// ── ユニットテスト: GO記録パース ─────────────────────────────────────────────
console.log('\n【GO記録パーステスト】');

test('全フィールド揃いのGO記録をパース', () => {
  const body = `## 変更概要\ntest\n\n${validGORecordSection(2099)}\n\n## その他\n`;
  const r = parseGORecord(body);
  assert.ok(r, 'GORecordがnull');
  assert.ok(r.issuer && r.issuer.includes('Shingo'));
  assert.ok(r.date && r.date.includes('2026'));
  assert.strictEqual(r.goText, 'GO #2099');
  assert.strictEqual(r.backup, 'あり');
});

test('GO記録セクションなし → null', () => {
  const r = parseGORecord('## 変更概要\ntest\n');
  assert.strictEqual(r, null);
});

test('GO発行者なし → issuer: null', () => {
  const body = `### GO記録\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #2099\n- バックアップ確認: あり\n`;
  const r = parseGORecord(body);
  assert.ok(r);
  assert.strictEqual(r.issuer, null);
});

test('GO原文なし → goText: null', () => {
  const body = `### GO記録\n- GO発行者: Shingo\n- 日時: 2026-06-13 10:00 JST\n- バックアップ確認: あり\n`;
  const r = parseGORecord(body);
  assert.ok(r);
  assert.strictEqual(r.goText, null);
});

test('バックアップ確認なし → backup: null', () => {
  const body = `### GO記録\n- GO発行者: Shingo\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #2099\n`;
  const r = parseGORecord(body);
  assert.ok(r);
  assert.strictEqual(r.backup, null);
});

// ── ユニットテスト: GO記録検証 ───────────────────────────────────────────────
console.log('\n【GO記録検証テスト】');

test('正常GO記録（PR番号一致）→ エラーなし', () => {
  const r = parseGORecord(validGORecordSection(2099));
  const errors = validateGORecord(r, '2099');
  assert.deepStrictEqual(errors, []);
});

test('GO記録なし（null）→ セクション未記入エラー', () => {
  const errors = validateGORecord(null, '2099');
  assert.ok(errors.length > 0);
  assert.ok(errors[0].includes('GO記録'));
});

test('GO発行者が権限外 → 権限外エラー', () => {
  const body = `### GO記録\n- GO発行者: Hikky-dev\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #2099\n- バックアップ確認: あり\n`;
  const r = parseGORecord(body);
  const errors = validateGORecord(r, '2099');
  assert.ok(errors.some(e => e.includes('権限外') || e.includes('GO権限')));
});

test('GO原文の書式不正（番号なし）→ 書式不正エラー', () => {
  const body = `### GO記録\n- GO発行者: Shingo（shingo-ops）\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO\n- バックアップ確認: あり\n`;
  const r = parseGORecord(body);
  const errors = validateGORecord(r, '2099');
  assert.ok(errors.some(e => e.includes('書式不正') || e.includes('番号のないGO')));
});

test('GO原文のPR番号不一致 → 番号不一致エラー', () => {
  const body = `### GO記録\n- GO発行者: Shingo（shingo-ops）\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #9999\n- バックアップ確認: あり\n`;
  const r = parseGORecord(body);
  const errors = validateGORecord(r, '2099');
  assert.ok(errors.some(e => e.includes('番号不一致') || e.includes('9999')));
});

test('バックアップ確認未記入 → バックアップエラー', () => {
  const body = `### GO記録\n- GO発行者: Shingo（shingo-ops）\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #2099\n`;
  const r = parseGORecord(body);
  const errors = validateGORecord(r, '2099');
  assert.ok(errors.some(e => e.includes('バックアップ')));
});

test('バックアップ確認「該当なし」→ エラーなし（DB非接触の危険変更向け）', () => {
  const body = `### GO記録\n- GO発行者: Shingo（shingo-ops）\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #2099\n- バックアップ確認: 該当なし\n`;
  const r = parseGORecord(body);
  const errors = validateGORecord(r, '2099');
  assert.deepStrictEqual(errors, [], '「該当なし」はバックアップ確認として有効');
});

test('PR番号未指定時は番号一致チェックをスキップ', () => {
  const r = parseGORecord(validGORecordSection(9999));
  const errors = validateGORecord(r, null); // prNumber=null → スキップ
  assert.deepStrictEqual(errors, []);
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

// ── 書式バリエーションテスト（パス正規化改善） ──────────────────────────────
console.log('\n【書式バリエーションテスト（パス正規化）】');

test('normalizeCitationPath: ./path を path に正規化', () => {
  assert.strictEqual(normalizeCitationPath('./scripts/foo.js'), 'scripts/foo.js');
  assert.strictEqual(normalizeCitationPath('scripts/foo.js'), 'scripts/foo.js');
  assert.strictEqual(normalizeCitationPath('./frontend/src/App.tsx'), 'frontend/src/App.tsx');
});

test('バッククォートあり・行番号なしでも hasFileCitations=true', () => {
  const content = '| `backend/app/main.py` | 確認済み |';
  assert.ok(hasFileCitations(content));
});

test('バッククォートなし・スラッシュ入りパス・行番号ありでも hasFileCitations=true', () => {
  const content = '- frontend/src/App.tsx:42 の useEffect を確認';
  assert.ok(hasFileCitations(content));
});

test('バッククォートなし・相対パス（./）でも hasFileCitations=true', () => {
  const content = '- ./scripts/check-process-artifacts.js:10 の実装';
  assert.ok(hasFileCitations(content));
});

test('テーブルセル内の行番号範囲（N-M）でも hasFileCitations=true', () => {
  const content = '| backend/app/routers/foo.py:100-200 | 確認済み |';
  assert.ok(hasFileCitations(content));
});

test('行番号なし・スラッシュなし（単純な識別子）は hasFileCitations=false', () => {
  const content = '# ADR-121 説明テキスト。function_name を確認した。';
  assert.ok(!hasFileCitations(content));
});

test('バッククォート付き・行番号超過でもエラーなし（行番号チェック廃止）', () => {
  const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
  const content = `\`${scriptRelPath}:999999\` の行`;
  const errors = validateFileCitations(content);
  assert.deepStrictEqual(errors, [], '行番号範囲外はエラーにならない（廃止済み）');
});

test('バッククォート付き・行番号範囲（N-M）超過でもエラーなし（行番号チェック廃止）', () => {
  const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
  const content = `\`${scriptRelPath}:999999-1000000\` の範囲`;
  const errors = validateFileCitations(content);
  assert.deepStrictEqual(errors, [], '行番号範囲外はエラーにならない（廃止済み）');
});

test('バッククォートなし・行番号あり・実在ファイル → エラーなし', () => {
  const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
  const content = `- ${scriptRelPath}:42 の実装を確認`;
  const errors = validateFileCitations(content);
  assert.deepStrictEqual(errors, [], 'バッククォートなしでも実在ファイルはエラーなし');
});

test('相対パス（./）の実在ファイル → エラーなし（正規化後に実在チェック）', () => {
  const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
  const content = `- ./${scriptRelPath}:10 の確認`;
  const errors = validateFileCitations(content);
  assert.deepStrictEqual(errors, [], '相対パスも正規化後に実在確認される');
});

test('バッククォートなし・存在しないファイル → エラー検出', () => {
  const content = '- nonexistent/path/file.py:42 の関数';
  const errors = validateFileCitations(content);
  assert.ok(errors.length > 0, 'エラーが返るべき');
  assert.ok(errors[0].includes('存在しません'));
});

test('URL は引用として扱わない', () => {
  const content = '参考: https://github.com/owner/repo:42 を参照';
  const errors = validateFileCitations(content);
  assert.deepStrictEqual(errors, [], 'URL はファイル引用としてチェックしない');
});

test('extractFileCitations: 重複パスはまとめられる', () => {
  const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
  const content = `\`${scriptRelPath}:1\` と \`${scriptRelPath}:2\` は同一ファイル`;
  const citations = extractFileCitations(content);
  assert.strictEqual(citations.filter(p => p === scriptRelPath).length, 1, '重複排除されている');
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

// ── §7 AC4: 危ない変更でGO記録なしはfail ────────────────────────────────────
test('AC4: 危ない変更＋GO記録なし → GO記録必須メッセージで即fail', () => {
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_PR_BODY: '',
  });
  assert.notStrictEqual(result.code, 0, 'GO記録なしでfailするべき（exit != 0）');
  assert.ok(
    result.stderr.includes('PROCESS ARTIFACTS GATE FAILED'),
    'GATE FAILED メッセージが出るべき'
  );
  assert.ok(
    result.stderr.includes('GO記録') || result.stderr.includes('GO #'),
    'GO記録要求メッセージが出るべき'
  );
});

test('AC4-edge: 危ない変更＋GO記録なし＋成果物完備でも fail', () => {
  // 成果物が完備でもGO記録がなければdangerous PRはfail
  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1);
    const reconRelPath = writeTmp('danger-no-go/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-999');
    const designRelPath = writeTmp('danger-no-go/design.md', designContent);
    const body = `### 標準ワークフロー確認\n- 対象ADR: ADR-999\n- recon: ${reconRelPath}\n- 設計: ${designRelPath}\n`;

    const result = runScript({
      CHANGED_FILES: 'migrations/001_test.sql',
      MOCK_PR_BODY: body,
    });
    assert.notStrictEqual(result.code, 0, '成果物完備でもGO記録なしはfailするべき');
    assert.ok(
      result.stderr.includes('GO記録') || result.stderr.includes('GO #'),
      'GO記録要求メッセージが出るべき'
    );
  } finally {
    cleanupTmp();
  }
});

test('AC4-bad-format: GO原文の書式不正（番号なし）→ fail', () => {
  const body = `### GO記録\n- GO発行者: Shingo（shingo-ops）\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO\n- バックアップ確認: あり\n`;
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_PR_BODY: body,
    PR_NUMBER: '2099',
  });
  assert.notStrictEqual(result.code, 0, '書式不正はfailするべき');
  assert.ok(
    result.stderr.includes('書式不正') || result.stderr.includes('番号のないGO'),
    '書式不正メッセージが出るべき'
  );
});

test('AC4-number-mismatch: GO原文のPR番号不一致 → fail', () => {
  const body = `### GO記録\n- GO発行者: Shingo（shingo-ops）\n- 日時: 2026-06-13 10:00 JST\n- GO原文: GO #9999\n- バックアップ確認: あり\n`;
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_PR_BODY: body,
    PR_NUMBER: '2099',
  });
  assert.notStrictEqual(result.code, 0, '番号不一致はfailするべき');
  assert.ok(
    result.stderr.includes('番号不一致') || result.stderr.includes('9999'),
    '番号不一致メッセージが出るべき'
  );
});

test('AC4: 危ない変更で自己申告免除"だけ"はfail（GO記録必須）', () => {
  const body = `### 標準ワークフロー確認\n- [x] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n`;
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_PR_BODY: body,
  });
  assert.notStrictEqual(result.code, 0);
});

// ── §7 AC5: GO記録あり（全フィールド正常）→ pass ────────────────────────────
test('AC5: 危ない変更＋正常GO記録（PR番号一致）→ pass', () => {
  const body = validGORecordSection(2099);
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_PR_BODY: body,
    PR_NUMBER: '2099',
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
  assert.ok(result.stdout.includes('GO記録確認済み') || result.stdout.includes('pass'));
});

test('AC5: 危ない変更＋正常GO記録（緊急モード）→ pass＋宿題起票試行', () => {
  const sopSection = `### 標準ワークフロー確認\n- （危ない変更の特例時）モード: 緊急\n`;
  const goSection = validGORecordSection(2099);
  const result = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_PR_BODY: sopSection + '\n' + goSection,
    PR_NUMBER: '2099',
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
  assert.ok(
    result.stdout.includes('緊急') || result.stdout.includes('pass'),
    '緊急GO passメッセージが出るべき'
  );
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

// ── develop→main リリースPR スキップ ─────────────────────────────────────────
test('develop→main リリースPR は自動スキップ（pass）', () => {
  const result = runScript({
    CHANGED_FILES: 'frontend/src/App.tsx',
    MOCK_PR_BODY: '',
    MOCK_HEAD_REF: 'develop',
    MOCK_BASE_REF: 'main',
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
  assert.ok(result.stdout.includes('リリースPR') || result.stdout.includes('スキップ'));
});

test('hotfix→main は通常検査（スキップしない）', () => {
  const result = runScript({
    CHANGED_FILES: 'frontend/src/App.tsx',
    MOCK_PR_BODY: '',
    MOCK_HEAD_REF: 'hotfix/fix-something',
    MOCK_BASE_REF: 'main',
  });
  assert.notStrictEqual(result.code, 0, 'hotfix→main は検査でfailするべき');
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
