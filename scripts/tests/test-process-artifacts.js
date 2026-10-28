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
  hasUserImpactingChange,
  isUserImpactingFile,
  getExternalApiChangeReport,
  parseSOPDeclaration,
  parseGORecord,
  validateGORecord,
  normalizeCitationPath,
  extractFileCitations,
  hasFileCitations,
  validateFileCitations,
  validateDesignDoc,
  hasPoOnlyExceptionPath,
  migrationsContainDropStatement,
  sqlTextHasDestructiveStatement,
  requiresPoOnlyGo,
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

function runScript(env = {}, args = []) {
  const result = spawnSync('node', [SCRIPT, ...args], {
    env: { ...process.env, ...env },
    encoding: 'utf8',
  });
  return { code: result.status, stdout: result.stdout, stderr: result.stderr };
}

function runScriptWithPath(env, args, pathValue) {
  return spawnSync('node', [SCRIPT, ...args], {
    env: { ...process.env, ...env, PATH: pathValue },
    encoding: 'utf8',
  });
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

function normalizeAdrs(adrs) {
  if (!adrs) return ['ADR-999'];
  return Array.isArray(adrs) ? adrs : [adrs];
}

/** 存在するファイル/行のfile:line引用を含む正常なrecon */
function validReconContent(filePath, lineNum, adrs = 'ADR-999') {
  const adrLines = normalizeAdrs(adrs).map(adr => `**対象ADR**: ${adr}`).join('\n');
  return `# recon — test\n${adrLines}\n\n## file:line 引用表\n| 引用先 | 確認内容 |\n|---|---|\n| \`${filePath}:${lineNum}\` | 確認済み |\n\n## 不明点リスト\n未解決ゼロ確認: 該当なし\n`;
}

/** 設計docの正常形 */
function validDesignContent(reconPath, adrs) {
  const adrLines = normalizeAdrs(adrs).map(adr => `**対象ADR**: ${adr}`).join('\n');
  return `# 設計 — test\n${adrLines}\n**recon**: ${reconPath}\n\n## 外部・過去事例の参照と我々への応用\n該当なし：今回は小規模修正のため外部事例は不要と判断\n\n## 受け入れ基準\n| 基準 | 検証方法 |\n|---|---|\n| テストが通る | pytest tests/test_xxx.py |\n`;
}

function validSOPBody(reconPath, designPath, adrs) {
  const adrLines = normalizeAdrs(adrs).map(adr => `- 対象ADR: ${adr}`).join('\n');
  return `### 標準ワークフロー確認\n- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n${adrLines}\n- recon: ${reconPath}\n- 設計: ${designPath}\n`;
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

test('ops/launchd/ は dangerous 区分', () => {
  assert.strictEqual(classifyFile('ops/launchd/jp.salesanchor.disk-janitor.plist'), 'dangerous');
});

test('ADR-1024 台本 backend/app/ops/ は dangerous 区分', () => {
  assert.strictEqual(classifyFile('backend/app/ops/readonly_query.py'), 'dangerous');
});

test('ADR-1024 docker-compose.ai-reader.yml は dangerous 区分', () => {
  assert.strictEqual(classifyFile('docker-compose.ai-reader.yml'), 'dangerous');
});

test('ADR-1042 docker-compose.ai-reader-http.yml は dangerous 区分', () => {
  assert.strictEqual(classifyFile('docker-compose.ai-reader-http.yml'), 'dangerous');
});

test('ADR-1047 決まり台帳の4ファイルは dangerous 区分', () => {
  for (const n of ['rules.yml', 'rule-docs.txt', 'required-checks.txt', 'prod-secrets.txt']) {
    assert.strictEqual(classifyFile('docs/specs/rule-enforcement/' + n), 'dangerous');
  }
  assert.notStrictEqual(classifyFile('docs/specs/rule-enforcement/README.md'), 'dangerous');
});

test('backend/app/opsx/ は dangerous にならない（real-code）', () => {
  assert.strictEqual(classifyFile('backend/app/opsx/a.py'), 'real-code');
});

test('docker-compose.yml は dangerous にならない（unknown）', () => {
  assert.strictEqual(classifyFile('docker-compose.yml'), 'unknown');
});

test('backend/app/routers/ は dangerous にならない（real-code）', () => {
  assert.strictEqual(classifyFile('backend/app/routers/x.py'), 'real-code');
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

test('frontend/src/ は user-impacting 区分', () => {
  assert.ok(isUserImpactingFile('frontend/src/pages/schedule/SchedulePage.tsx'));
  assert.ok(hasUserImpactingChange(['frontend/src/pages/schedule/SchedulePage.tsx']));
});

test('backend/app/routers/ は user-impacting 区分', () => {
  assert.ok(isUserImpactingFile('backend/app/routers/leads.py'));
  assert.ok(hasUserImpactingChange(['backend/app/routers/leads.py']));
});

test('backend/app/services/ は user-impacting 区分', () => {
  assert.ok(isUserImpactingFile('backend/app/services/message_translator.py'));
  assert.ok(hasUserImpactingChange(['backend/app/services/message_translator.py']));
});

test('backend/app/auth/ は user-impacting 区分', () => {
  assert.ok(isUserImpactingFile('backend/app/auth/dependencies.py'));
  assert.ok(hasUserImpactingChange(['backend/app/auth/dependencies.py']));
});

test('backend/app/tasks/ は user-impacting 区分', () => {
  assert.ok(isUserImpactingFile('backend/app/tasks/refresh_meta_tokens.py'));
  assert.ok(hasUserImpactingChange(['backend/app/tasks/refresh_meta_tokens.py']));
});

test('backend/app/discord_gateway/ は user-impacting 区分', () => {
  assert.ok(isUserImpactingFile('backend/app/discord_gateway/client.py'));
  assert.ok(hasUserImpactingChange(['backend/app/discord_gateway/client.py']));
});

test('PR-C の外部API検出レポートを読み込める', () => {
  const prev = process.env.MOCK_EXTERNAL_API_CHANGE;
  process.env.MOCK_EXTERNAL_API_CHANGE = 'true';
  const report = getExternalApiChangeReport();
  assert.ok(report.hasExternalChange);
  assert.ok(report.detectedApis.includes('mock_external_api'));
  if (prev === undefined) {
    delete process.env.MOCK_EXTERNAL_API_CHANGE;
  } else {
    process.env.MOCK_EXTERNAL_API_CHANGE = prev;
  }
});

test('backend/app/schemas/ は user-impacting ではない', () => {
  assert.ok(!isUserImpactingFile('backend/app/schemas/lead.py'));
  assert.ok(!hasUserImpactingChange(['backend/app/schemas/lead.py']));
});

// ── ユニットテスト: PR 本文パース ─────────────────────────────────────────────
console.log('\n【PR本文パーステスト】');

test('標準ワークフロー確認セクションをパース', () => {
  const body = `## なぜ\nテスト\n\n### 標準ワークフロー確認\n- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ\n- 対象ADR: ADR-123\n- recon: docs/handoff/my-job/recon.md\n- 設計: docs/handoff/my-job/design.md\n`;
  const d = parseSOPDeclaration(body);
  assert.ok(d, 'declaration が null');
  assert.strictEqual(d.adr, 'ADR-123');
  assert.deepStrictEqual(d.adrs, ['ADR-123']);
  assert.strictEqual(d.reconPath, 'docs/handoff/my-job/recon.md');
  assert.strictEqual(d.designPath, 'docs/handoff/my-job/design.md');
  assert.strictEqual(d.isExempt, false);
});

test('標準ワークフロー確認セクションで複数ADRをパース', () => {
  const body = `### 標準ワークフロー確認\n- 対象ADR: ADR-009\n- 対象ADR: ADR-011\n- recon: docs/handoff/my-job/recon.md\n- 設計: docs/handoff/my-job/design.md\n`;
  const d = parseSOPDeclaration(body);
  assert.ok(d, 'declaration が null');
  assert.deepStrictEqual(d.adrs, ['ADR-009', 'ADR-011']);
  assert.strictEqual(d.adr, 'ADR-009');
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

// ── ユニットテスト: 注記かっこの除去（全角・半角） ───────────────────────────
console.log('\n【注記かっこ除去テスト】');

function parenBody(touch, del) {
  return `### 標準ワークフロー確認\n- 対象ADR: ADR-1\n- recon: docs/handoff/x/recon.md\n- 設計: docs/handoff/x/design.md\n触るファイル:\n${touch}\n削除するファイル:\n${del}\n`;
}

test('削除するファイル: 半角かっこの注記を外す (a)', () => {
  const d = parseSOPDeclaration(parenBody('- docs/t.md', '- migrations/a.sql (22行削除)'));
  assert.deepStrictEqual(d.deleteFiles, ['migrations/a.sql']);
});

test('削除するファイル: 全角かっこの注記を外す（従来どおり） (b)', () => {
  const d = parseSOPDeclaration(parenBody('- docs/t.md', '- migrations/b.sql （22行削除）'));
  assert.deepStrictEqual(d.deleteFiles, ['migrations/b.sql']);
});

test('削除するファイル: 注記なしはそのまま (c)', () => {
  const d = parseSOPDeclaration(parenBody('- docs/t.md', '- docs/c.md'));
  assert.deepStrictEqual(d.deleteFiles, ['docs/c.md']);
});

test('触るファイル: 半角かっこの注記を外す (d)', () => {
  const d = parseSOPDeclaration(parenBody('- migrations/d.sql (新規)\n- docs/e.md （修正）', '- なし'));
  assert.deepStrictEqual(d.touchFiles, ['migrations/d.sql', 'docs/e.md']);
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

// ── ユニットテスト: ADR-1003 GO委任 ───────────────────────────────────────
console.log('\n【ADR-1003 GO委任テスト】');

/** 委譲名義のGO記録セクション */
function delegatedGORecordSection(prNumber) {
  return `### GO記録\n- GO発行者: POの委任に基づくClaude Opus発行\n- 日時: 2026-09-29 10:00 JST\n- GO原文: GO #${prNumber}\n- バックアップ確認: あり\n`;
}

test('ADR-1003: 委譲の名義（例外対象でない）はエラーなしで通る', () => {
  const r = parseGORecord(delegatedGORecordSection(2099));
  const errors = validateGORecord(r, '2099', { requiresPoOnly: false });
  assert.deepStrictEqual(errors, []);
});

test('ADR-1003: 例外対象で委譲の名義を使うとfailする', () => {
  const r = parseGORecord(delegatedGORecordSection(2099));
  const errors = validateGORecord(r, '2099', { requiresPoOnly: true });
  assert.ok(errors.length > 0);
  assert.ok(errors.some(e => e.includes('例外対象') && e.includes('PO本人')));
});

test('ADR-1003: PO名義は例外対象でも従来どおり通る', () => {
  const r = parseGORecord(validGORecordSection(2099)); // Shingo（shingo-ops）名義
  const errors = validateGORecord(r, '2099', { requiresPoOnly: true });
  assert.deepStrictEqual(errors, []);
});

test('ADR-1003: hasPoOnlyExceptionPath は workflow-lint.yml を例外対象と判定する', () => {
  assert.ok(hasPoOnlyExceptionPath(['.github/workflows/workflow-lint.yml']));
  assert.ok(!hasPoOnlyExceptionPath(['.github/workflows/deploy.yml']));
});

test('ADR-1003: migrationsContainDropStatement はMOCK変数で判定できる', () => {
  process.env.MOCK_MIGRATION_DROP_DETECTED = 'true';
  try {
    assert.strictEqual(migrationsContainDropStatement(['migrations/001_test.sql']), true);
  } finally {
    delete process.env.MOCK_MIGRATION_DROP_DETECTED;
  }
});

test('ADR-1003: requiresPoOnlyGo はmigrationファイルが無ければfalse（DROP検出をスキップ）', () => {
  assert.strictEqual(requiresPoOnlyGo(['backend/app/schemas/lead.py']), false);
});

test('ADR-1003: migration有り＋BASE_SHA/HEAD_SHA無し → fail-closed（true）', () => {
  const savedBase = process.env.BASE_SHA;
  const savedHead = process.env.HEAD_SHA;
  delete process.env.BASE_SHA;
  delete process.env.HEAD_SHA;
  try {
    assert.strictEqual(migrationsContainDropStatement(['migrations/001_test.sql']), true);
  } finally {
    if (savedBase !== undefined) process.env.BASE_SHA = savedBase; else delete process.env.BASE_SHA;
    if (savedHead !== undefined) process.env.HEAD_SHA = savedHead; else delete process.env.HEAD_SHA;
  }
});

test('ADR-1003: migrationファイルが無ければBASE_SHA/HEAD_SHA無しでもfalse', () => {
  const savedBase = process.env.BASE_SHA;
  const savedHead = process.env.HEAD_SHA;
  delete process.env.BASE_SHA;
  delete process.env.HEAD_SHA;
  try {
    assert.strictEqual(migrationsContainDropStatement(['backend/app/schemas/lead.py']), false);
  } finally {
    if (savedBase !== undefined) process.env.BASE_SHA = savedBase; else delete process.env.BASE_SHA;
    if (savedHead !== undefined) process.env.HEAD_SHA = savedHead; else delete process.env.HEAD_SHA;
  }
});

// ── ユニットテスト: R6a 本人GOが要るPRの見分け（本物の git 差分で試す） ──────
console.log('\n【R6a 本人GO見分けテスト】');

const { mkdtempSync } = require('fs');
const os = require('os');

/** 一時 git リポジトリで「空の土台 → files を足した頭」の差分を作り、見分けの結果を返す */
function detectInTempRepo(files) {
  const dir = mkdtempSync(join(os.tmpdir(), 'r6a-'));
  const git = (args) => execSync(`git ${args}`, { cwd: dir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  const savedCwd = process.cwd();
  const savedBase = process.env.BASE_SHA;
  const savedHead = process.env.HEAD_SHA;
  try {
    git('init -q');
    git('config user.email t@example.com');
    git('config user.name t');
    git('config commit.gpgsign false');
    writeFileSync(join(dir, 'README.txt'), 'base\n', 'utf8');
    git('add -A');
    git('commit -q -m base');
    const base = git('rev-parse HEAD');
    for (const [name, content] of Object.entries(files)) {
      mkdirSync(path.dirname(join(dir, name)), { recursive: true });
      writeFileSync(join(dir, name), content, 'utf8');
    }
    git('add -A');
    git('commit -q -m head');
    const head = git('rev-parse HEAD');
    process.env.BASE_SHA = base;
    process.env.HEAD_SHA = head;
    process.chdir(dir);
    return migrationsContainDropStatement(Object.keys(files));
  } finally {
    process.chdir(savedCwd);
    if (savedBase !== undefined) process.env.BASE_SHA = savedBase; else delete process.env.BASE_SHA;
    if (savedHead !== undefined) process.env.HEAD_SHA = savedHead; else delete process.env.HEAD_SHA;
    rmSync(dir, { recursive: true, force: true });
  }
}

// [名前, ファイル名, 中身, 期待値]
const R6A_MIGRATION_CASES = [
  // ○ 見分ける
  ['○ 1行の表削除', 'migrations/001_a.sql', 'DROP TABLE users;\n', true],
  ['○ 小文字・複数行にまたがる表削除', 'migrations/001_b.sql', 'drop\n  table\n  if exists users;\n', true],
  ['○ 列削除', 'migrations/001_c.sql', 'ALTER TABLE t\n  DROP COLUMN c;\n', true],
  ['○ スキーマ削除', 'migrations/001_d.sql', 'DROP SCHEMA tenant_x CASCADE;\n', true],
  ['○ データベース削除', 'migrations/001_e.sql', 'DROP DATABASE x;\n', true],
  ['○ ブロックコメントの外の表削除', 'migrations/001_f.sql', '/* 説明 */ DROP TABLE t;\n', true],
  ['○ TRUNCATE（先頭）', 'migrations/001_g.sql', 'TRUNCATE TABLE leads;\n', true],
  ['○ TRUNCATE（; の直後）', 'migrations/001_h.sql', 'SELECT 1;\nTRUNCATE leads;\n', true],
  ['○ WHERE の無い DELETE', 'migrations/001_i.sql', 'DELETE FROM leads;\n', true],
  ['○ WHERE の無い DELETE（; の直後・複数行）', 'migrations/001_j.sql', 'SELECT 1;\nDELETE\n  FROM leads\n  ;\n', true],
  ['○ 後ろの文にだけ WHERE がある（前の DELETE は無条件）', 'migrations/001_k.sql', 'DELETE FROM a; DELETE FROM b WHERE x = 1;\n', true],
  ['○ scripts/migrate_*.py の中の表削除', 'scripts/migrate_zz_test.py', 'cur.execute("DROP TABLE old_t")\n', true],
  ['○ scripts/run_all_migrations.sh の中の表削除', 'scripts/run_all_migrations.sh', 'psql -c "DROP TABLE old_t"\n', true],
  ['○ migrate_*.py の execute("TRUNCATE x")', 'scripts/migrate_zz_q1.py', 'cur.execute("TRUNCATE x")\n', true],
  ["○ migrate_*.py の execute('DELETE FROM x')（WHERE なし）", 'scripts/migrate_zz_q2.py', "cur.execute('DELETE FROM x')\ncur.execute('SELECT 1 WHERE a')\n", true],
  // × 見分けない
  ['× migrate_*.py の execute("DELETE FROM x WHERE id=1")', 'scripts/migrate_zz_q3.py', 'cur.execute("DELETE FROM x WHERE id=1")\n', false],
  ['× 引用符つきの表名で WHERE のある DELETE', 'scripts/migrate_zz_q4.py', 'cur.execute(\'DELETE FROM "x" WHERE id=1\')\n', false],
  ['× 通常の CREATE', 'migrations/002_a.sql', 'CREATE TABLE t (id int);\n', false],
  ['× WHERE のある DELETE', 'migrations/002_b.sql', 'DELETE FROM leads WHERE id = 1;\n', false],
  ['× 複数行で WHERE のある DELETE', 'migrations/002_c.sql', 'DELETE FROM leads\n  USING x\n  WHERE leads.id = x.id;\n', false],
  ['× 行コメントの中だけの表削除', 'migrations/002_d.sql', '-- DROP TABLE users;\nSELECT 1;\n', false],
  ['× ブロックコメントの中だけの表削除', 'migrations/002_e.sql', '/*\n DROP TABLE users;\n*/\nSELECT 1;\n', false],
  ['× 文の始めでない語（GRANT の中の TRUNCATE）', 'migrations/002_f.sql', 'GRANT TRUNCATE ON leads TO app;\n', false],
  ['× 文の始めでない語（権限の中の DELETE）', 'migrations/002_g.sql', 'GRANT SELECT, DELETE ON leads TO app;\n', false],
  ['× UPDATE は対象外', 'migrations/002_h.sql', 'UPDATE leads SET a = 1;\n', false],
  ['× migrations と関係ない場所の SQL', 'docs/notes/example.sql', 'DROP TABLE users;\nTRUNCATE t;\nDELETE FROM t;\n', false],
  ['× scripts/ の migrate でない python', 'scripts/other_tool.py', 'cur.execute("DROP TABLE x")\n', false],
];

for (const [name, file, content, expected] of R6A_MIGRATION_CASES) {
  test(`R6a migration: ${name}`, () => {
    assert.strictEqual(detectInTempRepo({ [file]: content }), expected);
  });
}

test('R6a migration: 複数ファイルのうち 1 つだけ該当しても見分ける', () => {
  assert.strictEqual(
    detectInTempRepo({ 'migrations/003_a.sql': 'SELECT 1;\n', 'migrations/003_b.sql': 'DROP TABLE t;\n' }),
    true
  );
});

test('R6a migration: ファイルをまたいでも別ファイルの語はつながない（a の末尾と b の先頭）', () => {
  assert.strictEqual(
    detectInTempRepo({ 'migrations/003_c.sql': 'DELETE FROM t WHERE id = 1', 'migrations/003_d.sql': 'DELETE FROM t2 WHERE id = 2' }),
    false
  );
});

test('R6a migration: 差分が取れないとき（不正な SHA）は本人GO側に倒す', () => {
  const savedBase = process.env.BASE_SHA;
  const savedHead = process.env.HEAD_SHA;
  process.env.BASE_SHA = '0000000000000000000000000000000000000000';
  process.env.HEAD_SHA = '1111111111111111111111111111111111111111';
  try {
    assert.strictEqual(migrationsContainDropStatement(['migrations/009_x.sql']), true);
  } finally {
    if (savedBase !== undefined) process.env.BASE_SHA = savedBase; else delete process.env.BASE_SHA;
    if (savedHead !== undefined) process.env.HEAD_SHA = savedHead; else delete process.env.HEAD_SHA;
  }
});

test('R6a workflow-lint: 大文字・先頭 ./ ・.yaml の書き方も見分ける', () => {
  assert.ok(hasPoOnlyExceptionPath(['.github/workflows/workflow-lint.yaml']));
  assert.ok(hasPoOnlyExceptionPath(['./.github/workflows/workflow-lint.yml']));
  assert.ok(hasPoOnlyExceptionPath(['.GitHub/Workflows/Workflow-Lint.YML']));
  assert.ok(requiresPoOnlyGo(['.github/workflows/workflow-lint.yaml']));
});

test('R6a workflow-lint: 別のワークフロー・別の名前は見分けない', () => {
  assert.ok(!hasPoOnlyExceptionPath(['.github/workflows/deploy.yml']));
  assert.ok(!hasPoOnlyExceptionPath(['.github/workflows/workflow-lint-extra.yml']));
  assert.ok(!hasPoOnlyExceptionPath(['docs/.github/workflows/workflow-lint.yml']));
  assert.ok(!hasPoOnlyExceptionPath(['docs/workflow-lint.yml']));
});

// ── R6b: コメントの扱い・文の始まり・列を消す略記（本物の git 差分で試す） ──
console.log('\n【R6b 本人GO見分けテスト】');

const R6B_CASES = [
  // 1 コメントの扱い ○
  ['○ 1: sh の長い指定の後ろの表削除', 'scripts/run_all_migrations.sh', 'psql --set ON_ERROR_STOP=1 -c "DROP TABLE x"\n', true],
  ['○ 1: sh の長い指定の後ろの TRUNCATE', 'scripts/run_all_migrations.sh', 'psql -v ON_ERROR_STOP=1 --command "TRUNCATE x"\n', true],
  ['○ 1: py の引数リストの長い指定の後ろ', 'scripts/migrate_zz_r6b1.py', 'subprocess.run(["psql", "--command", "DROP TABLE x"])\n', true],
  ['○ 1: py の # コメントの中の表削除も素の文なので当たる', 'scripts/migrate_zz_r6b2.py', '# DROP TABLE x\n', true],
  ["○ 1: .sql の単引用符の中の -- の後ろの表削除", 'migrations/r6b_a.sql', "SELECT '--'; DROP TABLE x;\n", true],
  ["○ 1: .sql の '' の重ねを含む文字列の中の -- の後ろ", 'migrations/r6b_b.sql', "SELECT 'it''s -- x'; DROP TABLE x;\n", true],
  ["○ 1: .sql の単引用符の中の /* の後ろ", 'migrations/r6b_c.sql', "SELECT '/*'; DROP TABLE x;\n", true],
  ['○ 1: .sql の二重引用符の中の -- の後ろ', 'migrations/r6b_d.sql', 'SELECT "a--b"; DROP TABLE x;\n', true],
  ['○ 1: .sql の $$ の中の行コメントの次の行の表削除', 'migrations/r6b_e.sql', 'DO $$ BEGIN\n -- 説明\n DROP TABLE x;\nEND $$;\n', true],
  // 1 コメントの扱い ×
  ['× 1: .sql の行コメントだけ（後ろに文字列あり）', 'migrations/r6b_f.sql', "SELECT 'a--b'; -- DROP TABLE x\n", false],
  ['× 1: .sql の $$ の中の -- は本物のコメント', 'migrations/r6b_g.sql', 'DO $$ BEGIN\n -- DROP TABLE x\n NULL;\nEND $$;\n', false],
  ['× 1: .sql のブロックコメントだけ（前に文字列あり）', 'migrations/r6b_h.sql', "SELECT '/* a */'; /* DROP TABLE x */\n", false],
  ['× 1: .sql の ロールバック手順をコメントで書いただけ', 'migrations/r6b_i.sql', 'CREATE TABLE t (id int);\n-- ロールバック: DROP TABLE t;\n', false],
  ['○ 1: .sql の閉じの無いブロックコメントの後ろの表削除（R6a と同じ扱い）', 'migrations/r6b_ag.sql', 'SELECT 1; /* 説明\nDROP TABLE x;\n', true],
  ['○ 1: .sql の引用符の後ろで閉じの無い /* の後ろの表削除', 'migrations/r6b_ah.sql', "SELECT 'a'; /* DROP TABLE x;\n", true],
  ['○ 1: py の文字列の中でコメントに挟まれた表削除（素の文でもコメントを除いた文でも当たる）', 'scripts/migrate_zz_r6b3.py', 'cur.execute("DROP/**/TABLE x")\n', true],
  ['× 1: .sql の閉じのあるブロックコメントだけ', 'migrations/r6b_ai.sql', 'SELECT 1; /* 説明 DROP TABLE x; */\n', false],
  // 2 文の始まり ○
  ['○ 2: DO ブロックの中の WHERE なし DELETE', 'migrations/r6b_j.sql', 'DO $$ BEGIN DELETE FROM t; END $$;\n', true],
  ['○ 2: DO ブロックの中の TRUNCATE', 'migrations/r6b_k.sql', 'DO $$ BEGIN TRUNCATE t; END $$;\n', true],
  ['○ 2: WITH の後ろの WHERE なし DELETE', 'migrations/r6b_l.sql', 'WITH a AS (SELECT 1) DELETE FROM t;\n', true],
  ['○ 2: WHERE がかっこの中の副問い合わせにだけある DELETE', 'migrations/r6b_m.sql', 'DELETE FROM t USING (SELECT id FROM s WHERE x) q;\n', true],
  ['○ 2: IF の THEN の後ろの WHERE なし DELETE', 'migrations/r6b_n.sql', 'DO $$ BEGIN IF true THEN DELETE FROM t; END IF; END $$;\n', true],
  ['○ 2: ELSE の後ろの WHERE なし DELETE', 'migrations/r6b_o.sql', 'DO $$ BEGIN IF false THEN NULL; ELSE DELETE FROM t; END IF; END $$;\n', true],
  ['○ 2: LOOP の後ろの TRUNCATE', 'migrations/r6b_p.sql', 'DO $$ BEGIN LOOP TRUNCATE t; EXIT; END LOOP; END $$;\n', true],
  ['○ 2: 閉じかっこの手前で終わる DELETE（外の WHERE につられない）', 'migrations/r6b_q.sql', 'WITH d AS (DELETE FROM t RETURNING *) SELECT 1 FROM d WHERE true;\n', true],
  // 2 文の始まり ×
  ['× 2: DO ブロックの中の WHERE ありの DELETE', 'migrations/r6b_r.sql', 'DO $$ BEGIN DELETE FROM t WHERE id = 1; END $$;\n', false],
  ['× 2: かっこの外に WHERE がある USING 付き DELETE', 'migrations/r6b_s.sql', 'DELETE FROM t USING (SELECT 1 AS id) q WHERE t.id = q.id;\n', false],
  ['× 2: WITH の中の WHERE あり DELETE', 'migrations/r6b_t.sql', 'WITH d AS (DELETE FROM t WHERE id = 1 RETURNING *) SELECT 1 FROM d;\n', false],
  ['× 2: トリガー定義の中の DELETE / TRUNCATE', 'migrations/r6b_u.sql', 'CREATE TRIGGER a AFTER DELETE ON t FOR EACH STATEMENT EXECUTE FUNCTION f();\nCREATE TRIGGER b AFTER TRUNCATE ON t FOR EACH STATEMENT EXECUTE FUNCTION f();\n', false],
  ['× 2: 外部キーの ON DELETE', 'migrations/r6b_v.sql', 'ALTER TABLE t ADD CONSTRAINT fk FOREIGN KEY (a) REFERENCES s(id) ON DELETE CASCADE;\n', false],
  // 3 列を消す略記 ○
  ['○ 3: COLUMN を省いた列の削除', 'migrations/r6b_w.sql', 'ALTER TABLE t DROP c;\n', true],
  ['○ 3: IF EXISTS・ONLY・スキーマ付きで COLUMN 省略', 'migrations/r6b_x.sql', 'ALTER TABLE IF EXISTS ONLY public.t DROP IF EXISTS c;\n', true],
  ['○ 3: 2 つ目の操作で COLUMN 省略', 'migrations/r6b_y.sql', 'ALTER TABLE t ADD d int, DROP c;\n', true],
  ['○ 3: 引用符つきの名前で COLUMN 省略', 'migrations/r6b_z.sql', 'ALTER TABLE "t" DROP "c";\n', true],
  // 3 列を消す略記 ×
  ['× 3: 制約の削除', 'migrations/r6b_aa.sql', 'ALTER TABLE t DROP CONSTRAINT fk;\n', false],
  ['× 3: IF EXISTS 付きの制約の削除（2 つ目の操作）', 'migrations/r6b_ab.sql', 'ALTER TABLE t ADD d int, DROP CONSTRAINT IF EXISTS fk;\n', false],
  ['× 3: NOT NULL の削除', 'migrations/r6b_ac.sql', 'ALTER TABLE t ALTER COLUMN c DROP NOT NULL;\n', false],
  ['× 3: 既定値の削除（複数の操作）', 'migrations/r6b_ad.sql', 'ALTER TABLE t ALTER COLUMN a DROP NOT NULL, ALTER COLUMN b DROP DEFAULT;\n', false],
  ['× 3: IDENTITY の削除', 'migrations/r6b_ae.sql', 'ALTER TABLE t ALTER COLUMN c DROP IDENTITY;\n', false],
  ['× 3: 索引・トリガー・ポリシーの削除', 'migrations/r6b_af.sql', 'DROP INDEX i;\nDROP TRIGGER tr ON t;\nDROP POLICY p ON t;\n', false],
];

for (const [name, file, content, expected] of R6B_CASES) {
  test(`R6b migration: ${name}`, () => {
    assert.strictEqual(detectInTempRepo({ [file]: content }), expected);
  });
}

// ── R6c: PostgreSQL の字句・文の種類・中身の無い条件・.sql 以外の包み方（本物の git 差分で試す） ──
console.log('\n【R6c 本人GO見分けテスト】');

const R6C_CASES = [
  // 1 字句 ○
  ["○ 1: E 付き文字列の中の \\' の後ろの -- のあとの表削除", 'migrations/r6c_a.sql', "SELECT E'\\'--'; DROP TABLE x;\n", true],
  ["○ 1: E 付き文字列の中の \\' の後ろの /* のあとの表削除", 'migrations/r6c_b.sql', "SELECT E'\\'/*'; DROP TABLE x;\n", true],
  ['○ 1: ドル引用の中の -- のあとの表削除', 'migrations/r6c_c.sql', 'SELECT $$--$$; DROP TABLE x;\n', true],
  ['○ 1: ドル引用の中の /* のあとの表削除', 'migrations/r6c_d.sql', 'SELECT $$/*$$; DROP TABLE x;\n', true],
  ['○ 1: タグに数字を含むドル引用の中の WHERE なし DELETE', 'migrations/r6c_e.sql', 'CREATE FUNCTION f() RETURNS void LANGUAGE sql AS $f1$ DELETE FROM t $f1$; SELECT f();\n', true],
  ['○ 1: 入れ子のブロックコメントが閉じた後ろの表削除', 'migrations/r6c_f.sql', '/* a /* b */ c */ DROP TABLE x;\n', true],
  ['○ 1: 入れ子のブロックコメントが閉じていないとき後ろの表削除（止める側）', 'migrations/r6c_g.sql', '/* a /* b */ DROP TABLE x;\n', true],
  ['○ 1: ドル引用の中の文字列の中の -- は文字列なので後ろの表削除が当たる', 'migrations/r6c_h.sql', "DO $$ BEGIN PERFORM '--'; DROP TABLE x; END $$;\n", true],
  // 1 字句 ×
  ['× 1: 入れ子のブロックコメントの中だけの表削除', 'migrations/r6c_i.sql', '/* a /* b */ DROP TABLE x; */ SELECT 1;\n', false],
  ['× 1: ドル引用の中のコメントだけの表削除', 'migrations/r6c_j.sql', 'DO $f1$ BEGIN\n /* DROP TABLE x */ NULL;\nEND $f1$;\n', false],
  ["× 1: ドル引用の中の ' が閉じていなくても、後ろの行コメントは本物のコメント", 'migrations/r6c_k.sql', "SELECT $$it's$$;\n-- ロールバック: DROP TABLE t;\n", false],
  ["× 1: E 付き文字列の中の \\' の後ろの行コメントは本物のコメント", 'migrations/r6c_l.sql', "SELECT E'a\\'b';\n-- ロールバック: DROP TABLE t;\n", false],
  ["× 1: ドル引用の中の '' の重ね", 'migrations/r6c_m.sql', "CREATE FUNCTION f() RETURNS void AS $$ BEGIN RAISE NOTICE 'don''t'; END $$ LANGUAGE plpgsql;\n-- ロールバック: DROP TABLE t;\n", false],
  // 2 文の種類 ○
  ['○ 2: 持ち主ごとの一括削除', 'migrations/r6c_n.sql', 'DROP OWNED BY r CASCADE;\n', true],
  ['○ 2: 外部表の削除', 'migrations/r6c_o.sql', 'DROP FOREIGN TABLE t;\n', true],
  ['○ 2: 外部表の列の削除（略記）', 'migrations/r6c_p.sql', 'ALTER FOREIGN TABLE t DROP c;\n', true],
  ['○ 2: 空白を含む引用符つきの名前での列削除の略記', 'migrations/r6c_q.sql', 'ALTER TABLE "my t" DROP c;\n', true],
  ['○ 2: スキーマ付き・空白を含む引用符つきの名前での列削除の略記', 'migrations/r6c_r.sql', 'ALTER TABLE public."a b" DROP c;\n', true],
  ['○ 2: 実行計画の測定つきの WHERE なし DELETE', 'migrations/r6c_s.sql', 'EXPLAIN ANALYZE DELETE FROM t;\n', true],
  ['○ 2: 準備文を経由した WHERE なし DELETE', 'migrations/r6c_t.sql', 'PREPARE p AS DELETE FROM t; EXECUTE p;\n', true],
  ['○ 2: 型つきの準備文を経由した WHERE なし DELETE', 'migrations/r6c_u.sql', 'PREPARE p (int) AS DELETE FROM t;\n', true],
  // 2 文の種類 ×
  ['× 2: 実行計画の測定つきでも WHERE のある DELETE', 'migrations/r6c_v.sql', 'EXPLAIN ANALYZE DELETE FROM t WHERE id = 1;\n', false],
  ['× 2: 準備文を経由しても WHERE のある DELETE', 'migrations/r6c_w.sql', 'PREPARE p AS DELETE FROM t WHERE id = $1;\n', false],
  ['× 2: 実行計画だけ（DELETE を含まない）', 'migrations/r6c_x.sql', 'EXPLAIN ANALYZE SELECT 1;\n', false],
  ['× 2: 空白を含む引用符つきの名前での制約の削除', 'migrations/r6c_y.sql', 'ALTER TABLE "my t" DROP CONSTRAINT c;\n', false],
  ['× 2: 外部表の既定値の削除', 'migrations/r6c_z.sql', 'ALTER FOREIGN TABLE t ALTER COLUMN c DROP DEFAULT;\n', false],
  // 3 中身の無い条件 ○
  ['○ 3: WHERE true', 'migrations/r6c_aa.sql', 'DELETE FROM t WHERE true;\n', true],
  ['○ 3: WHERE 1 = 1', 'migrations/r6c_ab.sql', 'DELETE FROM t WHERE 1 = 1;\n', true],
  ['○ 3: WHERE NOT false', 'migrations/r6c_ac.sql', 'DELETE FROM t WHERE NOT false;\n', true],
  ["○ 3: WHERE 'a' = 'a'", 'migrations/r6c_ad.sql', "DELETE FROM t WHERE 'a' = 'a';\n", true],
  ['○ 3: RETURNING の文字列に WHERE があっても条件なしと同じ', 'migrations/r6c_ae.sql', "DELETE FROM t RETURNING 'WHERE';\n", true],
  ['○ 3: RETURNING の引用符つきの名前に where があっても条件なしと同じ', 'migrations/r6c_af.sql', 'DELETE FROM t RETURNING "where";\n', true],
  // 3 中身の無い条件 ×
  ['× 3: 列を参照する条件', 'migrations/r6c_ag.sql', 'DELETE FROM t WHERE id = 1;\n', false],
  ['× 3: 列と定数を AND でつないだ条件', 'migrations/r6c_ah.sql', 'DELETE FROM t WHERE true AND id = 1;\n', false],
  ['× 3: かっこの中に列を参照する条件', 'migrations/r6c_ai.sql', 'DELETE FROM t WHERE (id = 1);\n', false],
  ['× 3: 関数を呼ぶ条件', 'migrations/r6c_aj.sql', 'DELETE FROM t WHERE f(1);\n', false],
  ['○ 3: 全体を1重のかっこで包んだ定数だけの条件', 'migrations/r6c_am.sql', 'DELETE FROM t WHERE (true);\n', true],
  ['○ 3: 全体を2重のかっこで包んだ定数だけの条件', 'migrations/r6c_an.sql', 'DELETE FROM t WHERE ((1 = 1));\n', true],
  ['× 3: 全体を2重のかっこで包んだ列の比較', 'migrations/r6c_ao.sql', 'DELETE FROM t WHERE ((id = 1));\n', false],
  ['× 3: 列の比較を OR で2つかっこに入れた条件', 'migrations/r6c_ap.sql', 'DELETE FROM t WHERE (a = 1) OR (b = 2);\n', false],
  ['× 3: 途中にかっこがある普通の条件', 'migrations/r6c_aq.sql', 'DELETE FROM t WHERE (a = 1 OR b = 2) AND c = 3;\n', false],
  ['× 3: WHERE CURRENT OF','migrations/r6c_ak.sql', 'DELETE FROM t WHERE CURRENT OF c;\n', false],
  ['× 3: 副問い合わせを使う条件', 'migrations/r6c_al.sql', 'DELETE FROM t WHERE id IN (SELECT id FROM s);\n', false],
  // 4 .sql 以外 ○
  ['○ 4: シェルのヒアドキュメントの中の WHERE なし DELETE', 'scripts/run_all_migrations.sh', 'psql <<SQL\nDELETE FROM t;\nSQL\n', true],
  ['○ 4: シェルのヒアドキュメント（引用符つきの語）の中の TRUNCATE', 'scripts/run_all_migrations.sh', "psql <<'EOF'\nTRUNCATE t;\nEOF\n", true],
  ['○ 4: シェルのヒアドキュメントの中の WHERE true の DELETE', 'scripts/run_all_migrations.sh', 'psql <<SQL\nDELETE FROM t WHERE true;\nSQL\n', true],
  ['○ 4: python の改行の記号から始まる文字列の中の WHERE なし DELETE', 'scripts/migrate_zz_r6c1.py', 'cur.execute("\\nDELETE FROM t")\n', true],
  ['○ 4: python の改行の記号の後ろの TRUNCATE', 'scripts/migrate_zz_r6c2.py', "cur.execute('\\n  TRUNCATE t')\n", true],
  // 4 .sql 以外 ×
  ['× 4: シェルのヒアドキュメントの中の WHERE のある DELETE', 'scripts/run_all_migrations.sh', 'psql <<SQL\nDELETE FROM t WHERE id = 1;\nSQL\n', false],
  ['× 4: シェルのヒアドキュメントの中の SELECT だけ', 'scripts/run_all_migrations.sh', 'psql <<SQL\nSELECT 1;\nSQL\n', false],
  ['× 4: シェルのヒアドキュメントではない echo', 'scripts/run_all_migrations.sh', "echo 'DELETE log check'\n", false],
  ['× 4: python の改行の記号から始まる文字列の中の WHERE のある DELETE', 'scripts/migrate_zz_r6c3.py', 'cur.execute("\\nDELETE FROM t WHERE id = 1")\n', false],
  // 5 誤検知の解消
  ["× 5: ALTER TABLE の既定値の文字列の中のコンマと DROP", 'migrations/r6c_am.sql', "ALTER TABLE t ADD c text DEFAULT 'a, DROP b';\n", false],
  ["× 5: ALTER TABLE の既定値の二重引用符の中のコンマと DROP", 'migrations/r6c_an.sql', 'ALTER TABLE t ADD "a, DROP b" text;\n', false],
  ["○ 5: ALTER TABLE の文字列の後ろの操作の列削除の略記", 'migrations/r6c_ao.sql', "ALTER TABLE t ADD c text DEFAULT 'a, b', DROP d;\n", true],
  ["× 5: E 付き文字列の中の \\' の後ろの行コメント", 'migrations/r6c_ap.sql', "SELECT E'a\\'b'; -- DROP TABLE t\n", false],
  ['○ 5: 閉じの無い単引用符から後ろは素の文として当てる', 'migrations/r6c_aq.sql', "SELECT 'a; DROP TABLE t;\n", true],
  ['○ 5: 閉じの無いドル引用から後ろも当てる', 'migrations/r6c_ar.sql', 'SELECT $$ a; DROP TABLE t;\n', true],
];

for (const [name, file, content, expected] of R6C_CASES) {
  test(`R6c migration: ${name}`, () => {
    assert.strictEqual(detectInTempRepo({ [file]: content }), expected);
  });
}

test('R6c migration: 同じ内容でも .sql 以外の場所の SQL は migration として当てない', () => {
  assert.strictEqual(detectInTempRepo({ 'docs/notes/r6c.sql': 'DELETE FROM t WHERE true;\nDROP OWNED BY r;\n' }), false);
});

// ── R6d: 中身の無い条件の見分け方・文の種類・standard_conforming_strings・.sql 以外・長い入力 ──
console.log('\n【R6d 本人GO見分けテスト】');

const R6D_CASES = [
  // 1 中身の無い条件 ○
  ['○ 1: 型変換つきの真偽値', 'migrations/r6d_a.sql', 'DELETE FROM t WHERE 1::bool;\n', true],
  ['○ 1: 型変換つきの true', 'migrations/r6d_b.sql', 'DELETE FROM t WHERE true::boolean;\n', true],
  ['○ 1: 定数だけの IN', 'migrations/r6d_c.sql', 'DELETE FROM t WHERE 1 IN (1);\n', true],
  ['○ 1: 定数だけの BETWEEN', 'migrations/r6d_d.sql', 'DELETE FROM t WHERE 1 BETWEEN 0 AND 2;\n', true],
  ['○ 1: かっこで包んだ定数どうしの AND', 'migrations/r6d_e.sql', 'DELETE FROM t WHERE (1=1) AND (2=2);\n', true],
  ['○ 1: NOT (false)', 'migrations/r6d_f.sql', 'DELETE FROM t WHERE NOT (false);\n', true],
  ['○ 1: OR の枝の 1 つが定数', 'migrations/r6d_g.sql', 'DELETE FROM t WHERE TRUE OR id = 1;\n', true],
  ['○ 1: 指数つきの数', 'migrations/r6d_h.sql', 'DELETE FROM t WHERE 1e0 = 1e0;\n', true],
  ['○ 1: E 付き文字列どうしの比較', 'migrations/r6d_i.sql', "DELETE FROM t WHERE E'a' = E'a';\n", true],
  // 1 中身の無い条件 ×
  ['× 1: 列の IS NULL', 'migrations/r6d_j.sql', 'DELETE FROM t WHERE col IS NULL;\n', false],
  ['× 1: 引数 $1 を使う条件', 'migrations/r6d_k.sql', 'DELETE FROM t WHERE id = $1;\n', false],
  ['× 1: 引用符つきの列名', 'migrations/r6d_l.sql', 'DELETE FROM t WHERE "Id" = 1;\n', false],
  ['× 1: 列の IN', 'migrations/r6d_m.sql', 'DELETE FROM t WHERE c IN (1, 2);\n', false],
  ['× 1: 負の数との比較', 'migrations/r6d_n.sql', 'DELETE FROM t WHERE c = -1;\n', false],
  ['× 1: 関数を使う条件', 'migrations/r6d_o.sql', 'DELETE FROM t WHERE tenant_id = current_setting(\'x\');\n', false],
  ['× 1: python の差し込み記号', 'scripts/migrate_zz_r6d1.py', 'cur.execute("DELETE FROM t WHERE id = %s", (1,))\n', false],
  // 2 文の種類
  ['○ 2: かっこが入れ子の型指定の準備文', 'migrations/r6d_p.sql', 'PREPARE p (numeric(10,2)) AS DELETE FROM t;\n', true],
  ['○ 2: ルールの DO ALSO の WHERE なし DELETE', 'migrations/r6d_q.sql', 'CREATE RULE r AS ON INSERT TO v DO ALSO DELETE FROM t;\n', true],
  ['× 2: かっこが入れ子の型指定の準備文でも WHERE のある DELETE', 'migrations/r6d_r.sql', 'PREPARE p (numeric(10,2)) AS DELETE FROM t WHERE id = $1;\n', false],
  ['× 2: ルールの DO ALSO の WHERE のある DELETE', 'migrations/r6d_s.sql', 'CREATE RULE r AS ON INSERT TO v DO ALSO DELETE FROM t WHERE id = 1;\n', false],
  ['○ 2: ルールの DO INSTEAD でかっこに複数の文を並べた中の WHERE なし DELETE', 'migrations/r6d_v.sql', 'CREATE RULE r AS ON UPDATE TO v DO INSTEAD (DELETE FROM t WHERE id = 1; DELETE FROM u);\n', true],
  ['× 2: ルールの DO INSTEAD でかっこに複数の文を並べても全部に WHERE がある', 'migrations/r6d_w.sql', 'CREATE RULE r AS ON UPDATE TO v DO INSTEAD (DELETE FROM t WHERE id = 1; DELETE FROM u WHERE id = 2);\n', false],
  ['× 1: OR の枝がすべて列を参照する条件', 'migrations/r6d_x.sql', 'DELETE FROM t WHERE (a OR b) OR (c AND d = 1);\n', false],
  // 3 ドル引用のタグは大文字小文字を区別する
  ['○ 3: 大文字のタグのドル引用の中の WHERE なし DELETE', 'migrations/r6d_y.sql', 'DO $A$ BEGIN DELETE FROM t; END $A$;\n', true],
  ['× 3: 大文字小文字違いのタグでは閉じず、同じタグで閉じたあとの行コメントは本物のコメント', 'migrations/r6d_z.sql', 'SELECT $A$ x $a$ y $A$; -- DROP TABLE t\n', false],
  ['○ 3: 閉じの無いブロックコメントの後ろの行コメントも R6c と同じに扱う（コメントの外の表削除）', 'migrations/r6d_za.sql', '/* a\nSELECT 1; -- memo\nDROP TABLE t;\n', true],
  // 引用符の中に ALTER TABLE の字がある形でも、列を消す略記を見逃さない
  ['○ 6: 既定値の文字列に ALTER TABLE と 2 語があり、その後ろに列の削除（.sql）', 'migrations/r6d_zb.sql', "ALTER TABLE t ALTER COLUMN a SET DEFAULT 'alter table x y', DROP b;\n", true],
  ['○ 6: 引用符つきの名前に ALTER TABLE があり、その後ろに列の削除（.sql）', 'migrations/r6d_zc.sql', 'ALTER TABLE t ADD COLUMN "ALTER TABLE q r" int, DROP b;\n', true],
  ['○ 6: 既定値の文字列に ALTER TABLE と 2 語があり、その後ろに列の削除（python）', 'scripts/migrate_zz_r6d5.py', 'op.execute("ALTER TABLE t ALTER COLUMN a SET DEFAULT \'ALTER TABLE x y\', DROP b")\n', true],
  ['× 6: 列以外（制約）の削除だけの ALTER TABLE', 'migrations/r6d_zd.sql', 'ALTER TABLE t DROP CONSTRAINT k;\n', false],
  ['× 6: ALTER TABLE が 400 個並ぶ python の migration（列の削除なし）', 'scripts/migrate_zz_r6d6.py', 'def upgrade():\n' + 'op.execute("ALTER TABLE t ADD COLUMN c int")\n'.repeat(400), false],
  // 4 standard_conforming_strings
  ["○ 3: standard_conforming_strings を off にした同じ行の \\' の後ろ", 'migrations/r6d_t.sql', "SET standard_conforming_strings = off; SELECT 'a\\'--'; DROP TABLE x;\n", true],
  ["× 3: 設定が無ければ文字列が閉じて後ろがコメント", 'migrations/r6d_u.sql', "SELECT 'a\\'-- DROP TABLE x;\n", false],
  // 5 .sql 以外
  ['○ 5: ヒアドキュメントの終わりの語がバックスラッシュ始まり', 'scripts/run_all_migrations.sh', 'psql <<\\EOF\nDELETE FROM t;\nEOF\n', true],
  ['○ 5: ヒアドキュメントの最初の行が psql 命令', 'scripts/run_all_migrations.sh', 'psql <<EOF\n\\set x 1\nDELETE FROM t\nEOF\n', true],
  ['× 5: ヒアドキュメントの中の psql 命令の後ろの WHERE のある DELETE', 'scripts/run_all_migrations.sh', 'psql <<EOF\n\\set x 1\nDELETE FROM t WHERE id = 1;\nEOF\n', false],
  ['○ 5: python の # コメント行の次の行に \\n で始まる WHERE なし DELETE', 'scripts/migrate_zz_r6d2.py', '# memo\ncur.execute("\\nDELETE FROM t")\n', true],
  ['○ 5: python の \\r\\n の後ろの WHERE なし DELETE', 'scripts/migrate_zz_r6d3.py', 'cur.execute("\\r\\nDELETE FROM t")\n', true],
  ['× 5: python の \\t の後ろの WHERE のある DELETE', 'scripts/migrate_zz_r6d4.py', 'cur.execute("\\tDELETE FROM t WHERE id = 1")\n', false],
];

for (const [name, file, content, expected] of R6D_CASES) {
  test(`R6d migration: ${name}`, () => {
    assert.strictEqual(detectInTempRepo({ [file]: content }), expected);
  });
}

test('R6d 長い入力: 入れ子の深いかっこの条件が 1 秒以内に終わり例外を出さない', () => {
  const n = 10000;
  const sql = 'DELETE FROM t WHERE ' + '('.repeat(n) + 'true' + ')'.repeat(n) + ';\n';
  const t0 = Date.now();
  const result = sqlTextHasDestructiveStatement(sql, 'migrations/r6d_deep1.sql');
  const ms = Date.now() - t0;
  assert.strictEqual(result, true);
  assert.ok(ms < 1000, `${ms}ms`);
});

test('R6d 長い入力: 入れ子の深いドル引用が 1 秒以内に終わり例外を出さない', () => {
  const n = 5000;
  let open = '';
  let close = '';
  for (let i = 0; i < n; i++) { open += `$t${i}$ `; close = ` $t${i}$` + close; }
  const sql = open + 'SELECT 1' + close + ';\n';
  const t0 = Date.now();
  const result = sqlTextHasDestructiveStatement(sql, 'migrations/r6d_deep2.sql');
  const ms = Date.now() - t0;
  assert.strictEqual(result, false);
  assert.ok(ms < 1000, `${ms}ms`);
});

test('R6d 長い入力: 閉じの無いブロックコメントが大量にあっても 1 秒以内に終わる', () => {
  const sql = '/*'.repeat(20000) + '\n';
  const t0 = Date.now();
  const result = sqlTextHasDestructiveStatement(sql, 'migrations/r6d_deep3.sql');
  const ms = Date.now() - t0;
  assert.strictEqual(result, false);
  assert.ok(ms < 1000, `${ms}ms`);
});

test('R6b GO発行者: PO の名前入りで委任語により止めたとき、書き写した注記は別の欄に書くと案内する', () => {
  const errors = validateGORecord(
    parseGORecord(goSectionWithIssuer('PO（Shingo）本人がチャットで発行。転記は Claude Opus', 2099)),
    '2099',
    { requiresPoOnly: true }
  );
  assert.ok(errors.some(e => e.includes('別の欄')), errors.join('\n'));
});

test('R6b GO発行者: 委任名義だけの書き方には PO の名前の案内は出さない', () => {
  const errors = validateGORecord(
    parseGORecord(goSectionWithIssuer('POの委任に基づくClaude Opus発行', 2099)),
    '2099',
    { requiresPoOnly: true }
  );
  assert.ok(errors.some(e => e.includes('PO本人')));
  assert.ok(!errors.some(e => e.includes('別の欄')));
});

function goSectionWithIssuer(issuer, prNumber) {
  return `### GO記録\n- GO発行者: ${issuer}\n- 日時: 2026-10-27 10:00 JST\n- GO原文: GO #${prNumber}\n- バックアップ確認: 該当なし\n`;
}

test('R6a GO発行者: 委任名義の語に PO の名前が混ざっていても例外対象では通らない', () => {
  for (const issuer of ['Shingo の委任に基づく Claude Opus 発行', 'shingo-ops 代理', 'Shingo（Opus）', 'Shingo委任']) {
    const errors = validateGORecord(parseGORecord(goSectionWithIssuer(issuer, 2099)), '2099', { requiresPoOnly: true });
    assert.ok(errors.some(e => e.includes('PO本人')), `通ってはいけない: ${issuer}`);
  }
});

test('R6a GO発行者: 例外対象でなければ委任名義の混ざった書き方も今までどおり通る', () => {
  const errors = validateGORecord(
    parseGORecord(goSectionWithIssuer('Shingo の委任に基づく Claude Opus 発行', 2099)),
    '2099',
    { requiresPoOnly: false }
  );
  assert.deepStrictEqual(errors, []);
});

test('R6a GO発行者: 過去の本人の書き方は例外対象でも通る', () => {
  for (const issuer of ['Shingo（shingo-ops）', 'Shingo（PO）', 'shingo-ops', 'Shingo']) {
    const errors = validateGORecord(parseGORecord(goSectionWithIssuer(issuer, 2099)), '2099', { requiresPoOnly: true });
    assert.deepStrictEqual(errors, [], `通るべき: ${issuer}`);
  }
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

test('拡張子なしのコードスパンは file citation として無視される', () => {
  const content = '| `scope=mine` | `FunnelSection` | `/analytics/weekly-advisor-defensive` | `tenant_006` |';
  assert.ok(!hasFileCitations(content));
  assert.deepStrictEqual(validateFileCitations(content), []);
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

test('AC2: 複数ADRを含む設計は全件相互参照が必要', () => {
  const content = `# 設計\n**対象ADR**: ADR-009\n**対象ADR**: ADR-011\n**recon**: docs/handoff/x/recon.md\n\n## 外部・過去事例の参照と我々への応用\n該当なし：テスト\n\n## 受け入れ基準\n| 基準 | 検証方法 |\n|---|---|\n| テスト | pytest |\n`;
  const okErrors = validateDesignDoc(content, 'docs/handoff/x/recon.md', ['ADR-009', 'ADR-011']);
  assert.deepStrictEqual(okErrors, []);

  const ngErrors = validateDesignDoc(content, 'docs/handoff/x/recon.md', ['ADR-009', 'ADR-999999']);
  assert.ok(ngErrors.some(e => e.includes('ADR-999999')));
});

test('AC2: 設計docのADR参照も境界付きで評価される', () => {
  const content = `# 設計\n**対象ADR**: ADR-1000\n**recon**: docs/handoff/x/recon.md\n\n## 外部・過去事例の参照と我々への応用\n該当なし：テスト\n\n## 受け入れ基準\n| 基準 | 検証方法 |\n|---|---|\n| テスト | pytest |\n`;
  const errors = validateDesignDoc(content, 'docs/handoff/x/recon.md', ['ADR-10']);
  assert.ok(errors.some(e => e.includes('ADR-10')), `ADR-10 が ADR-1000 に吸われてはいけない: ${errors.join(' | ')}`);
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

// ── ADR-1003: GO委任の統合テスト ────────────────────────────────────────────
console.log('\n【ADR-1003 GO委任 統合テスト】');

test('ADR-1003統合: 危ない変更（例外対象でない）＋委譲名義のGO → pass', () => {
  const body = `### GO記録\n- GO発行者: POの委任に基づくClaude Opus発行\n- 日時: 2026-09-29 10:00 JST\n- GO原文: GO #2099\n- バックアップ確認: あり\n`;
  const result = runScript({
    CHANGED_FILES: 'scripts/some-script.sh', // dangerous（scripts/）だがADR-1003例外対象ではない
    MOCK_PR_BODY: body,
    PR_NUMBER: '2099',
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
});

test('ADR-1003統合: workflow-lint.yml変更＋委譲名義のGO → fail（PO本人のGOが必要）', () => {
  const body = `### GO記録\n- GO発行者: POの委任に基づくClaude Opus発行\n- 日時: 2026-09-29 10:00 JST\n- GO原文: GO #2099\n- バックアップ確認: あり\n`;
  const result = runScript({
    CHANGED_FILES: '.github/workflows/workflow-lint.yml',
    MOCK_PR_BODY: body,
    PR_NUMBER: '2099',
  });
  assert.notStrictEqual(result.code, 0, '委譲名義では例外対象のfailになるべき');
  assert.ok(
    result.stderr.includes('例外対象') && result.stderr.includes('PO本人'),
    `例外対象メッセージが出るべき: stderr=${result.stderr}`
  );
});

test('ADR-1003統合: workflow-lint.yml変更＋PO名義のGO → pass', () => {
  const result = runScript({
    CHANGED_FILES: '.github/workflows/workflow-lint.yml',
    MOCK_PR_BODY: validGORecordSection(2099),
    PR_NUMBER: '2099',
  });
  assert.strictEqual(result.code, 0, `PO名義ならexitコードは0であるべき: stderr=${result.stderr}`);
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
    CHANGED_FILES: 'docs/adr/ADR-001.md\nREADME.md',
    MOCK_PR_BODY: '',
  });
  assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
  assert.ok(result.stdout.includes('自動スキップ'));
});

// ── 柱2: 正本を含む書類PRは自動スキップさせない（宣言照合へ到達） ──────────────
test('柱2-欠落版: 正本(.md)を触る書類PRで宣言なし → fail想定', () => {
  const result = runScript({
    CHANGED_FILES: 'docs/ai-agents/design-partner.md',
    PR_NUMBER: '9999',
    MOCK_PR_BODY: '### 標準ワークフロー確認\n（宣言なし）',
  });
  assert.notStrictEqual(result.code, 0, `正本変更で宣言なしは fail すべき: stdout=${result.stdout}`);
});

test('柱2-充足版: 正本(.md)を含む書類PRはスキップせず照合ステージへ進む', () => {
  const result = runScript({
    CHANGED_FILES: 'docs/ai-agents/design-partner.md',
    PR_NUMBER: '9999',
    MOCK_PR_BODY: '### 標準ワークフロー確認\n触るファイル: docs/ai-agents/design-partner.md',
  });
  assert.ok(
    result.stdout.includes('宣言照合へ進む'),
    `正本を含む書類PRは自動スキップせず照合へ進むべき: stdout=${result.stdout}`
  );
  assert.ok(
    !result.stdout.includes('書類のみの変更 — 自動スキップ'),
    `正本を含む場合は「自動スキップ」メッセージを出してはいけない: stdout=${result.stdout}`
  );
});

test('柱2-中立版: 正本を含まない純書類PR → 従来どおり自動スキップ(pass)', () => {
  const result = runScript({
    CHANGED_FILES: 'docs/handoff/some-work/notes.md',
    PR_NUMBER: '9999',
    MOCK_PR_BODY: '',
  });
  assert.strictEqual(result.code, 0, `正本を含まない純書類はスキップ pass すべき: stdout=${result.stdout}`);
});

// ── 追加テスト: latest main 既存パスとの二重定義検出 ─────────────────────────────
console.log('\n【二重定義検出テスト】');

test('新規作成したファイルが latest main に既にある場合は fail', () => {
  const pathOnMain = 'scripts/tmp-added-probe.js';
  const result = runScript({
    CHANGED_FILES: pathOnMain,
    MOCK_ADDED_FILES: pathOnMain,
    MOCK_ORIGIN_MAIN_FILES: `${pathOnMain}\n`,
    MOCK_PR_BODY: validGORecordSection(2099),
    MOCK_PR_AUTHOR: 'shingo-cc',
    PR_NUMBER: '2099',
  });
  assert.notStrictEqual(result.code, 0, '既存パスの新規作成は fail するべき');
  assert.ok(
    result.stderr.includes('既に存在') || result.stderr.includes('古い土台'),
    `二重定義検出メッセージが必要: ${result.stderr}`
  );
});

test('本当の新規パスは latest main 照合を通過する', () => {
  const pathNotOnMain = 'scripts/tmp-unique-probe.js';
  const result = runScript({
    CHANGED_FILES: pathNotOnMain,
    MOCK_ADDED_FILES: pathNotOnMain,
    MOCK_ORIGIN_MAIN_FILES: 'scripts/another-existing-file.js\n',
    MOCK_PR_BODY: validGORecordSection(2099),
    MOCK_PR_AUTHOR: 'shingo-cc',
    PR_NUMBER: '2099',
  });
  assert.strictEqual(result.code, 0, `新規パスは pass するべき: stderr=${result.stderr}`);
  assert.ok(result.stdout.includes('危ない変更') || result.stdout.includes('pass'));
});

test('既存ファイルの変更だけなら二重定義として誤検出しない', () => {
  const result = runScript({
    CHANGED_FILES: 'scripts/check-process-artifacts.js',
    MOCK_PR_BODY: validGORecordSection(2099),
    MOCK_PR_AUTHOR: 'shingo-cc',
    PR_NUMBER: '2099',
  });
  assert.strictEqual(result.code, 0, `既存ファイルの変更は pass するべき: stderr=${result.stderr}`);
  assert.ok(!result.stderr.includes('既に存在'), '変更のみで新規定義扱いしないこと');
});

// ── 統合テスト: 正常系（完全な成果物）────────────────────────────────────────
console.log('\n【統合テスト】');

test('内部のみのPR: 実在するrecon＋設計doc → GOなしでpass', () => {
  setupTmp();
  try {
    // 実在するファイルを引用
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1);
    const reconRelPath = writeTmp('test-job/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-999');
    const designRelPath = writeTmp('test-job/design.md', designContent);

    const body = `### 標準ワークフロー確認
- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ
- 対象ADR: ADR-999
- recon: ${reconRelPath}
- 設計: ${designRelPath}
`;

    const result = runScript({
      CHANGED_FILES: 'backend/app/schemas/lead.py',
      MOCK_PR_BODY: body,
    });
    assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
    assert.ok(result.stdout.includes('PASSED'));
  } finally {
    cleanupTmp();
  }
});

test('ユーザー影響変更: GOなしはfail', () => {
  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1);
    const reconRelPath = writeTmp('user-impact-no-go/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-999');
    const designRelPath = writeTmp('user-impact-no-go/design.md', designContent);
    const body = `### 標準ワークフロー確認
- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ
- 対象ADR: ADR-999
- recon: ${reconRelPath}
- 設計: ${designRelPath}
`;

    const result = runScript({
      CHANGED_FILES: 'frontend/src/pages/schedule/SchedulePage.tsx',
      MOCK_PR_BODY: body,
    });

    assert.notStrictEqual(result.code, 0, 'GOなしのユーザー影響変更はfailするべき');
    assert.ok(result.stderr.includes('GO記録') || result.stderr.includes('GO #'));
  } finally {
    cleanupTmp();
  }
});

test('ユーザー影響変更: GOありはpass', () => {
  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1);
    const reconRelPath = writeTmp('user-impact-with-go/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-999');
    const designRelPath = writeTmp('user-impact-with-go/design.md', designContent);
    const body = `### 標準ワークフロー確認
- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ
- 対象ADR: ADR-999
- recon: ${reconRelPath}
- 設計: ${designRelPath}

${validGORecordSection(2099)}`;

    const result = runScript({
      CHANGED_FILES: 'backend/app/services/message_translator.py',
      MOCK_PR_BODY: body,
      PR_NUMBER: '2099',
    });

    assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
    assert.ok(result.stdout.includes('ユーザー影響変更') || result.stdout.includes('PASSED'));
  } finally {
    cleanupTmp();
  }
});

test('外部API変更: GOなしはfail', () => {
  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1);
    const reconRelPath = writeTmp('external-api-no-go/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-999');
    const designRelPath = writeTmp('external-api-no-go/design.md', designContent);
    const body = `### 標準ワークフロー確認
- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ
- 対象ADR: ADR-999
- recon: ${reconRelPath}
- 設計: ${designRelPath}
`;

    const result = runScript({
      CHANGED_FILES: 'backend/app/schemas/lead.py',
      MOCK_EXTERNAL_API_CHANGE: 'true',
      MOCK_PR_BODY: body,
    });

    assert.notStrictEqual(result.code, 0, 'GOなしの外部API変更はfailするべき');
    assert.ok(result.stderr.includes('GO記録') || result.stderr.includes('GO #'));
  } finally {
    cleanupTmp();
  }
});

test('外部API変更: GOありはpass', () => {
  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1);
    const reconRelPath = writeTmp('external-api-with-go/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-999');
    const designRelPath = writeTmp('external-api-with-go/design.md', designContent);
    const body = `### 標準ワークフロー確認
- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ
- 対象ADR: ADR-999
- recon: ${reconRelPath}
- 設計: ${designRelPath}

${validGORecordSection(2099)}`;

    const result = runScript({
      CHANGED_FILES: 'backend/app/schemas/lead.py',
      MOCK_EXTERNAL_API_CHANGE: 'true',
      MOCK_PR_BODY: body,
      PR_NUMBER: '2099',
    });

    assert.strictEqual(result.code, 0, `exitコードは0であるべき: stderr=${result.stderr}`);
    assert.ok(result.stdout.includes('外部API変更') || result.stdout.includes('PASSED'));
  } finally {
    cleanupTmp();
  }
});

test('正常系: 実在するADR命名バリエーション4件は全てpass', () => {
  const cases = [
    { adr: 'ADR-009', label: 'ADR-009-discord-gateway.md' },
    { adr: 'ADR-011', label: 'ADR-011.md' },
    { adr: 'ADR-018', label: 'ADR-018_instagram_send_endpoint_fix.md' },
    { adr: 'ADR-1000', label: 'ADR-1000-external-api-smoke-mandatory.md' },
  ];

  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    for (const { adr, label } of cases) {
      const reconContent = validReconContent(scriptRelPath, 1, adr);
      const reconRelPath = writeTmp(`adr-variants/${adr}-recon.md`, reconContent);
      const designContent = validDesignContent(reconRelPath, adr);
      const designRelPath = writeTmp(`adr-variants/${adr}-design.md`, designContent);
      const body = validSOPBody(reconRelPath, designRelPath, adr);

      const result = runScript({
        CHANGED_FILES: 'backend/app/schemas/lead.py',
        MOCK_PR_BODY: body,
      });
      assert.strictEqual(result.code, 0, `${label} は pass するべき: stderr=${result.stderr}`);
      assert.ok(result.stdout.includes('PASSED'), `${label} は PASSED 出力が必要`);
    }
  } finally {
    cleanupTmp();
  }
});

test('境界: ADR-10 参照は ADR-1000-*.md だけでは pass しない', () => {
  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1, 'ADR-10');
    const reconRelPath = writeTmp('adr-boundary/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, 'ADR-10');
    const designRelPath = writeTmp('adr-boundary/design.md', designContent);
    const body = validSOPBody(reconRelPath, designRelPath, 'ADR-10');

    const result = runScript({
      CHANGED_FILES: 'backend/app/schemas/lead.py',
      MOCK_PR_BODY: body,
    });
    assert.notStrictEqual(result.code, 0, 'ADR-10 は ADR-1000 を誤検知して pass してはいけない');
    assert.ok(
      result.stderr.includes('ADR ADR-10') || result.stderr.includes('ADR-10 のファイル'),
      `境界失敗メッセージが必要: stderr=${result.stderr}`
    );
  } finally {
    cleanupTmp();
  }
});

test('複数ADR: 1件でも欠ければ fail', () => {
  setupTmp();
  try {
    const scriptRelPath = SCRIPT.replace(repoRoot + '/', '');
    const reconContent = validReconContent(scriptRelPath, 1, ['ADR-009', 'ADR-011']);
    const reconRelPath = writeTmp('adr-multi/recon.md', reconContent);
    const designContent = validDesignContent(reconRelPath, ['ADR-009', 'ADR-011']);
    const designRelPath = writeTmp('adr-multi/design.md', designContent);

    const okBody = validSOPBody(reconRelPath, designRelPath, ['ADR-009', 'ADR-011']);
    const okResult = runScript({
      CHANGED_FILES: 'backend/app/schemas/lead.py',
      MOCK_PR_BODY: okBody,
    });
    assert.strictEqual(okResult.code, 0, `両方存在すれば pass するべき: stderr=${okResult.stderr}`);

    const ngBody = validSOPBody(reconRelPath, designRelPath, ['ADR-009', 'ADR-999999']);
    const ngResult = runScript({
      CHANGED_FILES: 'backend/app/schemas/lead.py',
      MOCK_PR_BODY: ngBody,
    });
    assert.notStrictEqual(ngResult.code, 0, '欠けたADRがあれば fail するべき');
    assert.ok(ngResult.stderr.includes('ADR-999999'), `欠落したADRのエラーが必要: stderr=${ngResult.stderr}`);
  } finally {
    cleanupTmp();
  }
});

// ── §7 AC2: 複数ADRを含む設計は全件相互参照が必要 ──────────────────────────
test('AC2: 複数ADRを含む設計は全件相互参照が必要', () => {
  const content = `# 設計
**対象ADR**: ADR-009
**対象ADR**: ADR-011
**recon**: docs/handoff/x/recon.md

## 外部・過去事例の参照と我々への応用
該当なし：テスト

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| テスト | pytest |
`;
  const okErrors = validateDesignDoc(content, 'docs/handoff/x/recon.md', ['ADR-009', 'ADR-011']);
  assert.deepStrictEqual(okErrors, []);

  const ngErrors = validateDesignDoc(content, 'docs/handoff/x/recon.md', ['ADR-009', 'ADR-999999']);
  assert.ok(ngErrors.some(e => e.includes('ADR-999999')));
});

test('AC2: 設計docのADR参照も境界付きで評価される', () => {
  const content = `# 設計
**対象ADR**: ADR-1000
**recon**: docs/handoff/x/recon.md

## 外部・過去事例の参照と我々への応用
該当なし：テスト

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| テスト | pytest |
`;
  const errors = validateDesignDoc(content, 'docs/handoff/x/recon.md', ['ADR-10']);
  assert.ok(errors.some(e => e.includes('ADR-10')), `ADR-10 が ADR-1000 に吸われてはいけない: ${errors.join(' | ')}`);
});

// ── §7 AC2: 「外部・過去事例と応用」欄セクション自体が無い場合もfail ─────────────────────────────
test('AC2: 「外部・過去事例と応用」欄セクション自体が無い場合もfail', () => {
  const content = `# 設計
## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| テスト | pytest |
`;
  const errors = validateDesignDoc(content, null, null);
  assert.ok(errors.some(e => e.includes('外部')));
});

// ── §7 AC3: 検証リンク無しの受入基準はfail ───────────────────────────────────
test('AC3: 検証方法が空の受け入れ基準はfail', () => {
  const content = `# 設計
**対象ADR**: ADR-1
**recon**: docs/handoff/x/recon.md

## 外部・過去事例の参照と我々への応用
該当なし：テスト

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| テストが通る | |
`;
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
    const body = `### 標準ワークフロー確認
- 対象ADR: ADR-999
- recon: ${reconRelPath}
- 設計: ${designRelPath}
`;

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
  const body = `### GO記録
- GO発行者: Shingo（shingo-ops）
- 日時: 2026-06-13 10:00 JST
- GO原文: GO
- バックアップ確認: あり
`;
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
  const body = `### GO記録
- GO発行者: Shingo（shingo-ops）
- 日時: 2026-06-13 10:00 JST
- GO原文: GO #9999
- バックアップ確認: あり
`;
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
  const body = `### 標準ワークフロー確認
- [x] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ
`;
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
  const sopSection = `### 標準ワークフロー確認
- （危ない変更の特例時）モード: 緊急
`;
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

// ── git diff 3点形式の動作検証（古い土台の巻き込み解消） ──────────────────────
console.log('\n【git diff 3点形式テスト（gate-diff-3dot）】');

test('3点差分: 古い土台のブランチで本線側の scripts/ 変更を巻き込まない', () => {
  // 期待値先行:
  //   2点 git diff A B   → base(develop先端)～head間の "A と B の差" にdevelop側のscripts/も出る
  //   3点 git diff A...B → merge-base(A,B) から B への差分のみ = feature が実際に加えた変更だけ

  const { mkdtempSync } = require('fs');
  const tmpRepo = mkdtempSync('/tmp/gate-3dot-test-');
  try {
    // 1. 一時リポジトリ初期化
    execSync(
      `git -C "${tmpRepo}" init -q && ` +
      `git -C "${tmpRepo}" config user.email "t@t" && ` +
      `git -C "${tmpRepo}" config user.name "t"`,
      { encoding: 'utf8' }
    );

    // 2. 共通の base コミット X（ブランチ分岐点）
    execSync(
      `touch "${tmpRepo}/base.txt" && ` +
      `git -C "${tmpRepo}" add . && ` +
      `git -C "${tmpRepo}" commit -q -m "base"`,
      { encoding: 'utf8' }
    );

    // 3. develop に scripts/ の変更を追加（ブランチ分岐後に本線へ入った変更）
    execSync(
      `mkdir -p "${tmpRepo}/scripts" && ` +
      `printf '#!/bin/sh\necho hi\n' > "${tmpRepo}/scripts/reaper.sh" && ` +
      `git -C "${tmpRepo}" add . && ` +
      `git -C "${tmpRepo}" commit -q -m "develop: add scripts/reaper.sh"`,
      { encoding: 'utf8' }
    );
    const baseSha = execSync(`git -C "${tmpRepo}" rev-parse HEAD`, { encoding: 'utf8' }).trim();

    // 4. feature ブランチを X（1コミット前）から切り、docs のみ変更
    execSync(`git -C "${tmpRepo}" checkout -q -b feature HEAD~1`, { encoding: 'utf8' });
    execSync(
      `mkdir -p "${tmpRepo}/docs" && ` +
      `printf '# design\n' > "${tmpRepo}/docs/design.md" && ` +
      `git -C "${tmpRepo}" add . && ` +
      `git -C "${tmpRepo}" commit -q -m "feature: docs only"`,
      { encoding: 'utf8' }
    );
    const headSha = execSync(`git -C "${tmpRepo}" rev-parse HEAD`, { encoding: 'utf8' }).trim();

    // 5. 前提確認: 2点形式は scripts/reaper.sh を巻き込む（旧バグの再現）
    const diff2 = execSync(
      `git -C "${tmpRepo}" diff --name-only "${baseSha}" "${headSha}"`,
      { encoding: 'utf8' }
    ).trim();
    assert.ok(
      diff2.includes('scripts/reaper.sh'),
      `前提: 2点差分は scripts/reaper.sh を含むべき（旧バグ確認）: ${diff2}`
    );

    // 6. 修正確認: 3点形式は scripts/reaper.sh を巻き込まない
    const diff3 = execSync(
      `git -C "${tmpRepo}" diff --name-only "${baseSha}...${headSha}"`,
      { encoding: 'utf8' }
    ).trim();
    assert.ok(
      !diff3.includes('scripts/reaper.sh'),
      `3点差分は scripts/reaper.sh を含まないべき: ${diff3}`
    );
    assert.ok(
      diff3.includes('docs/design.md'),
      `3点差分は feature が加えた docs/design.md を含むべき: ${diff3}`
    );
  } finally {
    rmSync(tmpRepo, { recursive: true, force: true });
  }
});

test('3点差分: feature が本当に scripts/ を変更した場合は正しく検出する（検知漏れなし）', () => {
  // 期待値: feature が scripts/ を実際に変更した場合、3点差分にも出る
  const { mkdtempSync } = require('fs');
  const tmpRepo = mkdtempSync('/tmp/gate-3dot-danger-');
  try {
    execSync(
      `git -C "${tmpRepo}" init -q && ` +
      `git -C "${tmpRepo}" config user.email "t@t" && ` +
      `git -C "${tmpRepo}" config user.name "t"`,
      { encoding: 'utf8' }
    );
    execSync(
      `touch "${tmpRepo}/base.txt" && ` +
      `git -C "${tmpRepo}" add . && ` +
      `git -C "${tmpRepo}" commit -q -m "base"`,
      { encoding: 'utf8' }
    );

    // develop に別変更（docs）
    execSync(
      `printf '# changelog\n' > "${tmpRepo}/CHANGELOG.md" && ` +
      `git -C "${tmpRepo}" add . && ` +
      `git -C "${tmpRepo}" commit -q -m "develop: changelog"`,
      { encoding: 'utf8' }
    );
    const baseSha = execSync(`git -C "${tmpRepo}" rev-parse HEAD`, { encoding: 'utf8' }).trim();

    // feature は scripts/ を実際に変更する
    execSync(`git -C "${tmpRepo}" checkout -q -b feature HEAD~1`, { encoding: 'utf8' });
    execSync(
      `mkdir -p "${tmpRepo}/scripts" && ` +
      `printf '#!/bin/sh\necho deploy\n' > "${tmpRepo}/scripts/deploy.sh" && ` +
      `git -C "${tmpRepo}" add . && ` +
      `git -C "${tmpRepo}" commit -q -m "feature: add scripts/deploy.sh"`,
      { encoding: 'utf8' }
    );
    const headSha = execSync(`git -C "${tmpRepo}" rev-parse HEAD`, { encoding: 'utf8' }).trim();

    const diff3 = execSync(
      `git -C "${tmpRepo}" diff --name-only "${baseSha}...${headSha}"`,
      { encoding: 'utf8' }
    ).trim();
    assert.ok(
      diff3.includes('scripts/deploy.sh'),
      `3点差分も feature が加えた scripts/deploy.sh を検出するべき（検知漏れなし）: ${diff3}`
    );
    // develop 側の CHANGELOG.md は巻き込まない
    assert.ok(
      !diff3.includes('CHANGELOG.md'),
      `3点差分は develop 側の CHANGELOG.md を巻き込まないべき: ${diff3}`
    );
  } finally {
    rmSync(tmpRepo, { recursive: true, force: true });
  }
});

{
// ─── 維持の仕組み欄テスト（正本§1.7・maintenance-gate便） ────────────────────
console.log('\n【維持の仕組み欄テスト（単体）】');
const { validateMaintenanceSection } = require(SCRIPT);

test('維持欄: セクション自体が無い → エラー', () => {
  const errors = validateMaintenanceSection('# design\n## 受け入れ基準\n');
  assert.ok(errors.some(e => e.includes('維持の仕組み')), `期待エラーなし: ${errors}`);
});

test('維持欄: 守り手が空欄 → エラー', () => {
  const errors = validateMaintenanceSection('# design\n## 維持の仕組み\n- 守り手: \n- 対象: x\n');
  assert.ok(errors.some(e => e.includes('ファイルパス') || e.includes('守り手')), `期待エラーなし: ${errors}`);
});

test('維持欄: 架空パスの名指し → 実在エラー', () => {
  const errors = validateMaintenanceSection('# design\n## 維持の仕組み\n- 守り手: .github/workflows/no-such-guard.yml\n- 対象: x\n');
  assert.ok(errors.some(e => e.includes('存在しません')), `期待エラーなし: ${errors}`);
});

test('維持欄: 実在パスの名指し → エラーなし', () => {
  const errors = validateMaintenanceSection('# design\n## 維持の仕組み\n- 守り手: .github/workflows/migration-guard.yml\n- 対象: x\n');
  assert.strictEqual(errors.length, 0, `誤検知: ${errors}`);
});

test('維持欄: 「人手で守る」宣言 → エラーなし', () => {
  const errors = validateMaintenanceSection('# design\n## 維持の仕組み\n- 守り手: 人手で守る（理由: 専用関所なし）\n- 対象: x\n');
  assert.strictEqual(errors.length, 0, `誤検知: ${errors}`);
});

console.log('\n【維持の仕組み欄テスト（統合・猶予と段階投入）】');

function maintBody(reconPath, designPath) {
  return validSOPBody(reconPath, designPath) + '触るファイル: backend/app/util_maint_test.py\n削除するファイル: なし\n';
}

test('維持欄統合: failモード＋欄なし＋PR2700 → fail', () => {
  setupTmp();
  try {
    const reconPath = writeTmp('m1/recon.md', validReconContent('scripts/check-process-artifacts.js', 10));
    const designPath = writeTmp('m1/design.md', validDesignContent(reconPath));
    const r = runScript({
      CHANGED_FILES: 'backend/app/util_maint_test.py',
      MOCK_PR_BODY: maintBody(reconPath, designPath),
      MOCK_PR_AUTHOR: 'shingo-cc',
      MOCK_EXTERNAL_API_CHANGE: 'false',
      PR_NUMBER: '2700',
      MAINTENANCE_ENFORCE: 'fail',
    });
    assert.strictEqual(r.code, 1, `fail期待: code=${r.code}\n${r.stdout}\n${r.stderr}`);
    assert.ok(r.stderr.includes('維持の仕組み'), `理由に維持欄が出るべき: ${r.stderr}`);
  } finally { cleanupTmp(); }
});

test('維持欄統合: warnモード（未設定）＋欄なし＋PR2700 → pass＋警告表示', () => {
  setupTmp();
  try {
    const reconPath = writeTmp('m2/recon.md', validReconContent('scripts/check-process-artifacts.js', 10));
    const designPath = writeTmp('m2/design.md', validDesignContent(reconPath));
    const r = runScript({
      CHANGED_FILES: 'backend/app/util_maint_test.py',
      MOCK_PR_BODY: maintBody(reconPath, designPath),
      MOCK_PR_AUTHOR: 'shingo-cc',
      MOCK_EXTERNAL_API_CHANGE: 'false',
      PR_NUMBER: '2700',
    });
    assert.strictEqual(r.code, 0, `pass期待: code=${r.code}\n${r.stdout}\n${r.stderr}`);
    assert.ok((r.stdout + r.stderr).includes('警告モード'), `警告表示が出るべき: ${r.stdout}\n${r.stderr}`);
  } finally { cleanupTmp(); }
});

test('維持欄統合: failモード＋欄あり実在守り手＋PR2700 → pass（誤検知ゼロ）', () => {
  setupTmp();
  try {
    const reconPath = writeTmp('m3/recon.md', validReconContent('scripts/check-process-artifacts.js', 10));
    const designPath = writeTmp('m3/design.md',
      validDesignContent(reconPath) + '\n## 維持の仕組み\n- 守り手: .github/workflows/migration-guard.yml\n- 対象: テスト対象\n');
    const r = runScript({
      CHANGED_FILES: 'backend/app/util_maint_test.py',
      MOCK_PR_BODY: maintBody(reconPath, designPath),
      MOCK_PR_AUTHOR: 'shingo-cc',
      MOCK_EXTERNAL_API_CHANGE: 'false',
      PR_NUMBER: '2700',
      MAINTENANCE_ENFORCE: 'fail',
    });
    assert.strictEqual(r.code, 0, `pass期待: code=${r.code}\n${r.stdout}\n${r.stderr}`);
  } finally { cleanupTmp(); }
});

test('維持欄統合: failモード＋欄なし＋PR2599 → pass（猶予・巻き込みゼロ）', () => {
  setupTmp();
  try {
    const reconPath = writeTmp('m4/recon.md', validReconContent('scripts/check-process-artifacts.js', 10));
    const designPath = writeTmp('m4/design.md', validDesignContent(reconPath));
    const r = runScript({
      CHANGED_FILES: 'backend/app/util_maint_test.py',
      MOCK_PR_BODY: validSOPBody(reconPath, designPath),
      MOCK_PR_AUTHOR: 'shingo-cc',
      MOCK_EXTERNAL_API_CHANGE: 'false',
      PR_NUMBER: '2599',
      MAINTENANCE_ENFORCE: 'fail',
    });
    assert.strictEqual(r.code, 0, `pass期待（猶予）: code=${r.code}\n${r.stdout}\n${r.stderr}`);
  } finally { cleanupTmp(); }
});

}

console.log('\n【validation-only副作用テスト】');

test('validation-only: 緊急判定は維持しissue createは0回', () => {
  setupTmp();
  const fakeBin = join(TMP, 'fake-bin');
  const ghLog = join(TMP, 'gh.log');
  mkdirSync(fakeBin, { recursive: true });
  writeFileSync(join(fakeBin, 'gh'), `#!/bin/sh\necho "$*" >> "${ghLog}"\nif [ "$1 $2" = "issue list" ]; then echo '[]'; fi\nexit 0\n`);
  require('fs').chmodSync(join(fakeBin, 'gh'), 0o755);
  try {
    const body = `### 標準ワークフロー確認\n- 対象ADR: ADR-113\n- recon: docs/handoff/go-record-transcription/pr-lifecycle-recon.md\n- 設計: docs/handoff/go-record-transcription/pr-lifecycle-design.md\n- （危ない変更の特例時）モード: 緊急 ＋ 承認者: shingo-ops\n触るファイル: scripts/check-process-artifacts.js\n削除するファイル: scripts/check-process-artifacts.js\n\n${validGORecordSection(2700)}`;
    const env = {
      CHANGED_FILES: 'scripts/check-process-artifacts.js',
      MOCK_ADDED_FILES: '',
      MOCK_PR_BODY: body,
      MOCK_PR_AUTHOR: 'shingo-cc',
      MOCK_EXTERNAL_API_CHANGE: 'false',
      PR_NUMBER: '2700',
      REPO: 'shingo-ops/salesanchor',
    };
    const validation = runScriptWithPath(env, ['--validation-only'], `${fakeBin}:${process.env.PATH}`);
    assert.strictEqual(validation.status, 0, `${validation.stdout}\n${validation.stderr}`);
    const validationLog = existsSync(ghLog) ? require('fs').readFileSync(ghLog, 'utf8') : '';
    assert.ok(!validationLog.includes('issue create'), `issue副作用あり: ${validationLog}`);

    const duplicate = runScriptWithPath(env, ['--validation-only', '--validation-only'], `${fakeBin}:${process.env.PATH}`);
    assert.strictEqual(duplicate.status, 1, `重複引数はfailすべき: ${duplicate.stdout}\n${duplicate.stderr}`);
    const unknown = runScriptWithPath(env, ['--validation-ony'], `${fakeBin}:${process.env.PATH}`);
    assert.strictEqual(unknown.status, 1, `未知引数はfailすべき: ${unknown.stdout}\n${unknown.stderr}`);
    const rejectedLog = existsSync(ghLog) ? require('fs').readFileSync(ghLog, 'utf8') : '';
    assert.ok(!rejectedLog.includes('issue create'), `引数拒否時のissue副作用あり: ${rejectedLog}`);

    const normal = runScriptWithPath(env, [], `${fakeBin}:${process.env.PATH}`);
    assert.strictEqual(normal.status, 0, `${normal.stdout}\n${normal.stderr}`);
    const normalLog = require('fs').readFileSync(ghLog, 'utf8');
    assert.ok(normalLog.includes('issue create'), `通常modeのissue createが無い: ${normalLog}`);
    assert.ok(normalLog.includes('--repo github.com/shingo-ops/salesanchor'), `Issue送信先が固定されていない: ${normalLog}`);
  } finally { cleanupTmp(); }
});

test('対象外REPOはfull checker開始前にfail', () => {
  const r = runScript({
    CHANGED_FILES: 'scripts/check-process-artifacts.js',
    MOCK_ADDED_FILES: '',
    MOCK_PR_BODY: validGORecordSection(2700),
    MOCK_PR_AUTHOR: 'shingo-cc',
    MOCK_EXTERNAL_API_CHANGE: 'false',
    PR_NUMBER: '2700',
    REPO: 'evil/example',
  }, ['--validation-only']);
  assert.strictEqual(r.code, 1, `対象外REPOはfailすべき: ${r.stdout}\n${r.stderr}`);
  assert.ok(r.stderr.includes('対象外repo'), `拒否理由が無い: ${r.stderr}`);
});

// ─── LOCAL_PRECHECK テスト（docs/handoff/local-gate-ci-parity/design.md §2）────
console.log('\n【LOCAL_PRECHECK テスト】');

test('LOCAL_PRECHECK: 危険変更＋GO記録なしでもGO記録で落ちず先の検査に進む', () => {
  const r = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    // LOCAL_PRECHECKは触る/削除ファイル照合も猶予なし扱いになるため、
    // GO記録の検査だけを分離して見るために宣言を満たしておく
    MOCK_PR_BODY: '### 標準ワークフロー確認\n触るファイル: migrations/001_test.sql\n削除するファイル: なし\n',
    LOCAL_PRECHECK: '1',
  });
  assert.strictEqual(r.code, 0, `GO記録なしでも落ちないべき: code=${r.code}\n${r.stdout}\n${r.stderr}`);
  assert.ok(
    r.stdout.includes('GO記録は') && r.stdout.includes('PR 番号確定後'),
    `GO記録省略メッセージが出るべき: ${r.stdout}`
  );
  assert.ok(
    !r.stderr.includes('PROCESS ARTIFACTS GATE FAILED'),
    `GO記録要求でfailしてはいけない: ${r.stderr}`
  );
});

test('LOCAL_PRECHECK: GITHUB_ACTIONS=true と併用するとfail（CIでは使用不可）', () => {
  const r = runScript({
    CHANGED_FILES: 'migrations/001_test.sql',
    MOCK_PR_BODY: '',
    LOCAL_PRECHECK: '1',
    GITHUB_ACTIONS: 'true',
  });
  assert.strictEqual(r.code, 1, `CIでのLOCAL_PRECHECKはfailすべき: code=${r.code}\n${r.stdout}\n${r.stderr}`);
  assert.ok(
    r.stderr.includes('LOCAL_PRECHECK は CI では使えません'),
    `CI不可メッセージが出るべき: ${r.stderr}`
  );
});

test('LOCAL_PRECHECK: PR_NUMBERなしでも触る/削除するファイルの宣言照合が行われる', () => {
  const r = runScript({
    CHANGED_FILES: 'backend/tests/util_precheck_test.py',
    MOCK_PR_BODY: '',
    LOCAL_PRECHECK: '1',
  });
  assert.strictEqual(r.code, 1, `PR番号なしでも宣言照合が働くべき: code=${r.code}\n${r.stdout}\n${r.stderr}`);
  assert.ok(
    r.stderr.includes('触るファイル'),
    `触るファイル宣言不足のメッセージが出るべき: ${r.stderr}`
  );
});

// ─── 結果集計 ─────────────────────────────────────────────────────────────────
console.log(`
${'='.repeat(50)}`);
console.log(`テスト結果: ✅ ${passed} PASS / ❌ ${failed} FAIL`);
if (failed > 0) {
  console.error('FAILED');
  process.exit(1);
} else {
  console.log('ALL PASSED');
  process.exit(0);
}
