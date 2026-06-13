#!/usr/bin/env node
/**
 * check-process-artifacts.js
 *
 * SOP/KPI2 プロセス成果物ゲート
 * docs/handoff/sop-kpi2/design.md §4 の実装
 *
 * 使用方法（CI）: node scripts/check-process-artifacts.js
 * 環境変数:
 *   BASE_SHA      git diff の起点 SHA
 *   HEAD_SHA      git diff の終点 SHA
 *   PR_NUMBER     GitHub PR 番号
 *   REPO          owner/repo 形式（例: shingo-ops/salesanchor）
 *   GH_TOKEN      GitHub API トークン（CI では自動設定）
 * テスト用モック変数:
 *   CHANGED_FILES 改行区切りのファイルパスリスト（BASE_SHA/HEAD_SHA の代替）
 *   MOCK_PR_BODY  PR 本文テキスト（GitHub API の代替）
 *   MOCK_PR_AUTHOR PR 作者ログイン（GitHub API の代替）
 */
'use strict';

const { readFileSync, existsSync } = require('fs');
const { execSync } = require('child_process');
const { join } = require('path');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();

// ─── 認可された PR 作者（コード変更PR作成可） ────────────────────────────────
const AUTHORIZED_AUTHORS = ['shingo-cc', 'Hikky-dev'];

// ─── GO権限（PO単独）────────────────────────────────────────────────────────
const AUTHORIZED_GO_ISSUERS = ['shingo-ops', 'Shingo'];

// ─── パス区分定義（design.md §1） ────────────────────────────────────────────
const DOCS_PATTERNS = [
  /^docs\//,
  /\.md$/,
  /^CLAUDE\.md$/,
  /^[^/]+\/CLAUDE\.md$/,
  /^AGENTS\.md$/,
  /^[^/]+\/AGENTS\.md$/,
  /^\.codex\//,
  /^\.github\/(?!workflows\/)/,
];

const DANGEROUS_PATTERNS = [
  /^migrations\//,                       // DBマイグレーション（ADR-135）
  /^scripts\//,                          // 本番スクリプト全般（ADR-135 B-2）
  /^\.github\/workflows\/deploy\.yml$/,  // デプロイワークフロー
];

const REAL_CODE_PATTERNS = [
  /^frontend\/src\//,
  /^frontend\/public\//,
  /^backend\/app\//,
  /^backend\/tests\//,
  /^lp\/src\//,
  /^\.github\/workflows\//,
  /^scripts\//,
];

function classifyFile(filePath) {
  if (DANGEROUS_PATTERNS.some(r => r.test(filePath))) return 'dangerous';
  if (DOCS_PATTERNS.some(r => r.test(filePath))) return 'docs';
  if (REAL_CODE_PATTERNS.some(r => r.test(filePath))) return 'real-code';
  return 'unknown'; // 安全側：本検査へ
}

function classifyChanges(files) {
  const hasDangerous = files.some(f => classifyFile(f) === 'dangerous');
  const hasRealCode = files.some(f => ['real-code', 'unknown'].includes(classifyFile(f)));
  const hasDocsOnly = !hasDangerous && !hasRealCode;
  return { hasDangerous, hasRealCode, hasDocsOnly };
}

// ─── PR 本文パース ────────────────────────────────────────────────────────────
function parseSOPDeclaration(prBody) {
  if (!prBody) return null;
  const sectionMatch = prBody.match(
    /###\s*標準ワークフロー確認\s*\n([\s\S]*?)(?=\n###|\n##|\n#|$)/
  );
  if (!sectionMatch) return null;
  const section = sectionMatch[1];

  const isExempt = /- \[x\]\s*免除/i.test(section);
  const adrMatch = section.match(/対象ADR:\s*(ADR-[\w-]+)/);
  const reconMatch = section.match(/recon:\s*(docs\/handoff\/[^\s\n]+\.md)/);
  const designMatch = section.match(/設計:\s*([^\n（]+)/);
  const modeMatch = section.match(/モード:\s*(些細|緊急)/);

  return {
    isExempt,
    adr: adrMatch ? adrMatch[1].trim() : null,
    reconPath: reconMatch ? reconMatch[1].trim() : null,
    designPath: designMatch ? designMatch[1].trim() : null,
    mode: modeMatch ? modeMatch[1] : null,
  };
}

// ─── GO記録パース ─────────────────────────────────────────────────────────────
/**
 * PR本文からGO記録セクションをパースする。
 * 書式:
 *   ### GO記録
 *   - GO発行者: Shingo（shingo-ops）
 *   - 日時: 2026-06-13 10:00 JST
 *   - GO原文: GO #<PR番号>
 *   - バックアップ確認: あり  ← DB変更なしの危険変更は「該当なし」も可
 */
function parseGORecord(prBody) {
  if (!prBody) return null;
  const sectionMatch = prBody.match(
    /###\s*GO記録\s*\n([\s\S]*?)(?=\n###|\n##|\n#|$)/
  );
  if (!sectionMatch) return null;
  const section = sectionMatch[1];

  const issuerMatch = section.match(/GO発行者:\s*(.+)/);
  const dateMatch = section.match(/日時:\s*(.+)/);
  const goTextMatch = section.match(/GO原文:\s*(.+)/);
  const backupMatch = section.match(/バックアップ確認:\s*(.+)/);

  return {
    issuer: issuerMatch ? issuerMatch[1].trim() : null,
    date: dateMatch ? dateMatch[1].trim() : null,
    goText: goTextMatch ? goTextMatch[1].trim() : null,
    backup: backupMatch ? backupMatch[1].trim() : null,
  };
}

// ─── GO記録検証 ──────────────────────────────────────────────────────────────
/**
 * GO記録の必須要素を検証する。
 * 必須: GO発行者（PO）・日時・GO #<PR番号>原文・バックアップ確認の有無
 * バックアップ確認: 「あり」「なし」「該当なし」いずれも可（DB非接触の危険変更は「該当なし」でよい）
 * GOの正式書式: 「GO #<PR番号>」（番号必須。番号のない曖昧な肯定はGOとみなさない）
 */
function validateGORecord(goRecord, prNumber) {
  if (!goRecord) {
    return [
      '❌ PR本文に「### GO記録」セクションがありません',
      '   → 危険変更はマージ前にチャットで「3行サマリ＋バックアップ確認」をPOに提示し、',
      '     「GO #<PR番号>」を受領してからPR本文の「### GO記録」セクションに転記してください',
      '   → 詳細: CLAUDE.md §ブランチ運用ルール',
    ];
  }

  const errors = [];

  if (!goRecord.issuer || !AUTHORIZED_GO_ISSUERS.some(a => goRecord.issuer.includes(a))) {
    errors.push(`❌ GO発行者が未記入または権限外です（「${goRecord.issuer || '未記入'}」）`);
    errors.push('   → GO権限はPO（Shingo / shingo-ops）のみです（Hikky-devによるバイパスは廃止）');
  }

  if (!goRecord.date || goRecord.date.trim().length < 5) {
    errors.push('❌ GO日時が記入されていません（「日時: YYYY-MM-DD HH:MM JST」形式）');
  }

  if (!goRecord.goText) {
    errors.push('❌ GO原文が記入されていません（「GO原文: GO #<PR番号>」必須）');
  } else {
    const goNumberMatch = goRecord.goText.match(/GO\s*#(\d+)/i);
    if (!goNumberMatch) {
      errors.push(`❌ GO原文の書式不正（「${goRecord.goText}」）: 「GO #<PR番号>」形式が必須（番号のないGOは無効）`);
    } else if (prNumber && goNumberMatch[1] !== String(prNumber)) {
      errors.push(`❌ GO原文のPR番号不一致（原文: GO #${goNumberMatch[1]} / 現在のPR: #${prNumber}）`);
      errors.push('   → GO #番号はこのPRの番号と完全に一致している必要があります');
    }
  }

  if (!goRecord.backup || goRecord.backup.trim().length < 2) {
    errors.push('❌ バックアップ確認が記入されていません（「バックアップ確認: あり/なし/該当なし」）');
  }

  return errors;
}

// ─── recon.md 検証 ────────────────────────────────────────────────────────────

/**
 * 生パス文字列をリポジトリルート相対パスに正規化する。
 * './path' → 'path'、それ以外はそのまま。
 */
function normalizeCitationPath(rawPath) {
  return rawPath.startsWith('./') ? rawPath.slice(2) : rawPath;
}

/**
 * recon コンテンツから file パス引用をすべて抽出する。
 * 以下の書式を認識する:
 *   - `path:N`, `path:N-M`, `path`  (バッククォート付き、行番号任意)
 *   - path/to/file:N, path/to/file:N-M  (バッククォートなし・スラッシュ必須・行番号あり)
 *   - ./path/to/file:N  (相対パス、行番号あり)
 * 行番号の妥当性チェックは行わない（ファイル実在確認のみ）。
 */
function extractFileCitations(content) {
  const paths = new Set();

  // バッククォート付き（行番号はオプション、単数・範囲どちらも可）
  const backtickRe = /`([^`\s]+?)(?::[\d]+(?:-[\d]+)?)?`/g;
  let m;
  while ((m = backtickRe.exec(content)) !== null) {
    const raw = m[1];
    if (/^https?:\/\//.test(raw)) continue; // URL スキップ
    paths.add(normalizeCitationPath(raw));
  }

  // バッククォートなし + スラッシュ入りパス + 行番号（スラッシュ必須で誤検知を抑制）
  // 先行する文字でパス開始を判定（空白・記号・行頭）
  // 例: `frontend/src/foo.tsx:42-50`, `./scripts/foo.js:10`
  const plainRe = /(?:^|[\s(,|[\n])((\.\/)?[a-zA-Z0-9_][\w.\-]*(?:\/[\w.\-]+)+)(?::[\d]+(?:-[\d]+)?)/gm;
  while ((m = plainRe.exec(content)) !== null) {
    const raw = m[1];
    if (/^https?:\/\//.test(raw)) continue;
    paths.add(normalizeCitationPath(raw));
  }

  return [...paths];
}

function hasFileCitations(content) {
  return extractFileCitations(content).length > 0;
}

function validateFileCitations(content) {
  const errors = [];
  for (const filePath of extractFileCitations(content)) {
    const fullPath = join(repoRoot, filePath);
    if (!existsSync(fullPath)) {
      errors.push(`  ❌ ${filePath} — ファイルが存在しません`);
    }
  }
  return errors;
}

// ─── 設計doc 検証 ─────────────────────────────────────────────────────────────
function validateDesignDoc(designContent, reconPath, adr) {
  const errors = [];

  // 受け入れ基準表の存在確認（| 基準 | 検証方法 | パターン）
  if (!/\|\s*基準\s*\|/.test(designContent)) {
    errors.push('  ❌ 設計docに受け入れ基準の表（| 基準 | 検証方法 |）が見つかりません');
  } else {
    // 検証方法が空のセルを検出（split 後に空セルを保持して検査）
    const allRows = designContent.split('\n').filter(line => /^\s*\|/.test(line));
    const hasEmpty = allRows.some(row => {
      if (/基準|検証方法/.test(row)) return false;
      if (/^[\s|:-]+$/.test(row)) return false; // separator row
      const cells = row.split('|').slice(1, -1); // 先頭末尾の空文字除去
      return cells.length >= 2 && cells[1].trim().length === 0;
    });
    if (hasEmpty) {
      errors.push('  ❌ 受け入れ基準の表に検証方法が空の行があります（空欄不可）');
    }
  }

  // recon 相互参照
  if (reconPath && !designContent.includes(reconPath)) {
    errors.push(`  ❌ 設計docに recon.md（${reconPath}）への参照がありません（相互参照必須）`);
  }

  // ADR 参照
  if (adr && !designContent.includes(adr)) {
    errors.push(`  ❌ 設計docに ADR 参照（${adr}）がありません（相互参照必須）`);
  }

  // 外部・過去事例欄の存在と非空確認
  const caseHeadingMatch = /^##[^\n]*外部[・・]過去事例[^\n]*/m.exec(designContent);
  if (!caseHeadingMatch) {
    errors.push('  ❌ 設計docに「外部・過去事例の参照と我々への応用」欄がありません（空欄不可）');
  } else {
    const afterHeading = designContent.slice(caseHeadingMatch.index + caseHeadingMatch[0].length);
    const nextSectionMatch = afterHeading.match(/\n##/);
    const sectionContent = nextSectionMatch
      ? afterHeading.slice(0, nextSectionMatch.index)
      : afterHeading;
    if (sectionContent.trim().length < 5) {
      errors.push('  ❌ 「外部・過去事例と応用」欄が空欄です（「該当なし＋理由」でも必要）');
    }
  }

  return errors;
}

// ─── 自動起票（緊急GO時） ────────────────────────────────────────────────────
function createFollowupIssue(prNumber, repo) {
  if (!repo || !prNumber) return;
  try {
    const deadline = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString().split('T')[0];
    const title = `[sop-followup] PR #${prNumber} 緊急GO — 宿題期限: ${deadline}`;
    const body = [
      `## 宿題待ち（緊急GOによる先行マージ）`,
      ``,
      `PR #${prNumber} が緊急GOで先行マージされました。`,
      `**期限**: ${deadline} までに以下の成果物を揃えて後追い提出してください。`,
      ``,
      `### 提出が必要なもの`,
      `- [ ] recon.md（\`docs/handoff/<仕事名>/recon.md\`）— file:line引用付き`,
      `- [ ] 設計doc — 受け入れ基準＋検証方法付き`,
      `- [ ] 上記を参照したPR（SOP宣言あり）`,
      ``,
      `期限超過は \`sop-followup-monitor\` ワークフローが自動警告します。`,
    ].join('\n');

    // 重複起票防止（同PR番号のopenイシューがあればスキップ）
    const existingIssues = JSON.parse(
      execSync(
        `gh issue list --label "sop-followup" --state open --json number,title --repo "${repo}"`,
        { encoding: 'utf8' }
      ).trim()
    );
    if (existingIssues.some(i => i.title.includes(`PR #${prNumber}`))) {
      console.log(`  ℹ️  PR #${prNumber} の sop-followup issue が既にあるためスキップ`);
      return;
    }

    execSync(
      `gh issue create --title "${title}" --body '${body.replace(/'/g, "'\\''")}' --label "sop-followup" --repo "${repo}"`,
      { encoding: 'utf8' }
    );
    console.log(`  📌 宿題待ち issue を起票しました（期限: ${deadline}）`);
  } catch (e) {
    console.warn(`  ⚠️  issue 起票に失敗: ${e.message}`);
  }
}

// ─── fail 出力 ───────────────────────────────────────────────────────────────
function printFailure(errors) {
  console.error('');
  console.error('❌ PROCESS ARTIFACTS GATE FAILED');
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  for (const e of errors) console.error(e);
  console.error('');
  console.error('【直し方】docs/handoff/sop-kpi2/design.md §2〜§4 を参照してください');
  console.error('　テンプレ: docs/handoff/_templates/recon.md, design.md');
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  process.exit(1);
}

// ─── 本検査 ──────────────────────────────────────────────────────────────────
function runFullCheck(declaration) {
  const errors = [];

  if (!declaration) {
    errors.push('❌ PR本文に「### 標準ワークフロー確認」セクションがありません');
    errors.push('   → PRテンプレートの「標準ワークフロー確認」セクションに記入してください');
    printFailure(errors);
  }

  const { adr, reconPath, designPath } = declaration;

  // a. ADR 参照
  if (!adr || adr === 'ADR-____') {
    errors.push('❌ 対象ADRが記入されていません（ADR-NNN の形式で記入）');
  } else {
    const adrGlob = join(repoRoot, 'docs/adr');
    const adrPattern = new RegExp(`^${adr}[\\w-]*\\.md$`, 'i');
    try {
      const adrFiles = execSync(`ls "${adrGlob}" 2>/dev/null`, { encoding: 'utf8' })
        .split('\n').filter(f => adrPattern.test(f));
      if (adrFiles.length === 0) {
        errors.push(`❌ ADR ${adr} のファイルが docs/adr/ に存在しません`);
      }
    } catch {
      errors.push(`❌ docs/adr/ が読み取れません`);
    }
  }

  // b. recon 検証
  if (!reconPath || reconPath.includes('<仕事名>')) {
    errors.push('❌ recon パスが記入されていません（docs/handoff/<仕事名>/recon.md）');
  } else {
    const fullReconPath = join(repoRoot, reconPath);
    if (!existsSync(fullReconPath)) {
      errors.push(`❌ recon.md が存在しません: ${reconPath}`);
    } else {
      const reconContent = readFileSync(fullReconPath, 'utf8');
      if (!hasFileCitations(reconContent)) {
        errors.push(`❌ recon.md に file:line 引用（\`path:N\` 形式）が1件もありません`);
      } else {
        const citationErrors = validateFileCitations(reconContent);
        errors.push(...citationErrors);
      }
    }
  }

  // c. 設計doc 検証
  if (!designPath || designPath.trim() === '____') {
    errors.push('❌ 設計docのパスが記入されていません');
  } else {
    const fullDesignPath = join(repoRoot, designPath.trim());
    if (!existsSync(fullDesignPath)) {
      errors.push(`❌ 設計docが存在しません: ${designPath}`);
    } else {
      const designContent = readFileSync(fullDesignPath, 'utf8');
      const designErrors = validateDesignDoc(designContent, reconPath, adr);
      errors.push(...designErrors);
    }
  }

  if (errors.length > 0) {
    printFailure(errors);
  }

  console.log('✅ process-artifacts gate PASSED');
}

// ─── メイン ──────────────────────────────────────────────────────────────────
function main() {
  // develop→main リリースPR は develop 段階で通過済み → スキップ
  // その他の →main PR（hotfix 等）は通常どおり検査
  const headRef = process.env.MOCK_HEAD_REF !== undefined ? process.env.MOCK_HEAD_REF : (process.env.HEAD_REF || '');
  const baseRef = process.env.MOCK_BASE_REF !== undefined ? process.env.MOCK_BASE_REF : (process.env.BASE_REF || '');
  if (baseRef === 'main' && headRef === 'develop') {
    console.log('✅ develop→main リリースPR — スキップ（develop段階で通過済み）');
    process.exit(0);
  }

  // 変更ファイルリストを取得
  let changedFiles;
  if (process.env.CHANGED_FILES !== undefined) {
    changedFiles = process.env.CHANGED_FILES.split('\n').filter(Boolean);
  } else {
    const base = process.env.BASE_SHA;
    const head = process.env.HEAD_SHA;
    if (!base || !head) {
      console.error('❌ BASE_SHA / HEAD_SHA が設定されていません');
      process.exit(1);
    }
    changedFiles = execSync(`git diff --name-only "${base}" "${head}"`, { encoding: 'utf8' })
      .trim().split('\n').filter(Boolean);
  }

  if (changedFiles.length === 0) {
    console.log('✅ 変更ファイルなし — スキップ（pass）');
    process.exit(0);
  }

  const { hasDangerous, hasRealCode, hasDocsOnly } = classifyChanges(changedFiles);

  if (hasDocsOnly) {
    console.log('✅ 書類のみの変更 — 自動スキップ（pass）');
    process.exit(0);
  }

  // PR 作者チェック（コード変更を含む PR のみ）
  const prNumber = process.env.PR_NUMBER;
  const repo = process.env.REPO;
  let prAuthor = '';
  if (process.env.MOCK_PR_AUTHOR !== undefined) {
    prAuthor = process.env.MOCK_PR_AUTHOR;
  } else if (prNumber && repo) {
    try {
      prAuthor = execSync(
        `gh api "repos/${repo}/pulls/${prNumber}" --jq '.user.login'`,
        { encoding: 'utf8' }
      ).trim();
    } catch {
      console.warn('⚠️  PR作者の取得に失敗 — スキップ');
    }
  }

  if (prAuthor && !AUTHORIZED_AUTHORS.includes(prAuthor)) {
    console.error(`❌ PR作者 "${prAuthor}" はコード変更PRの作成を許可されていません。`);
    console.error('   shingo-cc 名義で作り直してください（gh auth login で切り替え）。');
    console.error(`   許容作者: ${AUTHORIZED_AUTHORS.join(', ')}`);
    process.exit(1);
  }

  // PR 本文取得
  let prBody = '';
  if (process.env.MOCK_PR_BODY !== undefined) {
    prBody = process.env.MOCK_PR_BODY;
  } else if (prNumber && repo) {
    try {
      prBody = execSync(
        `gh api "repos/${repo}/pulls/${prNumber}" --jq '.body // ""'`,
        { encoding: 'utf8' }
      ).trim();
    } catch {
      console.warn('⚠️  PR本文の取得に失敗 — 空として扱います');
    }
  }

  const declaration = parseSOPDeclaration(prBody);

  // 危ない変更の処理（GO記録チェック）
  if (hasDangerous) {
    const goRecord = parseGORecord(prBody);
    const goErrors = validateGORecord(goRecord, prNumber);

    if (goErrors.length > 0) {
      printFailure(goErrors);
    }

    const mode = declaration ? declaration.mode : null;
    if (mode === '緊急') {
      console.log(`✅ 危ない変更：GO記録確認済み（緊急）— pass＋宿題待ち起票`);
      createFollowupIssue(prNumber, repo);
    } else {
      console.log(`✅ 危ない変更：GO記録確認済み — pass`);
    }
    process.exit(0);
  }

  // 実コード変更の処理
  if (declaration && declaration.isExempt) {
    console.log('✅ 自律クラフト免除宣言あり — pass（記録）');
    process.exit(0);
  }

  runFullCheck(declaration);
}

// テスト用にエクスポート
module.exports = {
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
};

// CLI として直接実行された場合のみ main() を呼ぶ
if (require.main === module) {
  main();
}
