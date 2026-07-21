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

// ── 柱2: 正本を含む書類PRは自動スキップさせない（宣言照合へ到達） ──────────────
test('柱2-欠落版: 正本(.md)を触る書類PRで宣言なし → fail想定', () => {
  const result = runScript({
    CHANGED_FILES: 'docs/ai-agents/design-partner.md',
    PR_NUMBER: '9999',
    MOCK_PR_BODY: '### 標準ワークフロー確認\n（宣言なし）',
  });
  assert.notStrictEqual(result.code, 0, `正本変更で宣言なしは fail すべき: stdout=${result.stdout}`);
});

test('柱2-充足版: 正本(.md)を触り触る/削除欄が実diffと一致 → pass想定', () => {
  const result = runScript({
    CHANGED_FILES: 'docs/ai-agents/design-partner.md',
    PR_NUMBER: '9999',
    MOCK_PR_BODY: '### 標準ワークフロー確認\n触るファイル: docs/ai-agents/design-partner.md\n削除するファイル: docs/ai-agents/design-partner.md\n対象ADR: ADR-121',
  });
  assert.strictEqual(result.code, 0, `正本変更で宣言完備は pass すべき: stdout=${result.stdout} stderr=${result.stderr}`);
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
