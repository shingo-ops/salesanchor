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
 *   MOCK_APPROVALS カンマ区切りの承認者ログインリスト（'' = 承認なし）
 */
'use strict';

const { readFileSync, existsSync } = require('fs');
const { execSync } = require('child_process');
const { join } = require('path');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();

// ─── 認可された承認者 ─────────────────────────────────────────────────────────
const AUTHORIZED_APPROVERS = ['shingo-ops', 'Hikky-dev'];

// ─── 認可された PR 作者（コード変更PR作成可） ────────────────────────────────
const AUTHORIZED_AUTHORS = ['shingo-cc', 'Hikky-dev'];

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

// ─── recon.md 検証 ────────────────────────────────────────────────────────────
const FILE_LINE_RE = /`([^`\s]+):(\d+)`/g;

function hasFileCitations(content) {
  FILE_LINE_RE.lastIndex = 0;
  return FILE_LINE_RE.test(content);
}

function validateFileCitations(content) {
  FILE_LINE_RE.lastIndex = 0;
  const errors = [];
  let match;
  while ((match = FILE_LINE_RE.exec(content)) !== null) {
    const filePath = match[1];
    const lineNum = parseInt(match[2], 10);
    const fullPath = join(repoRoot, filePath);
    if (!existsSync(fullPath)) {
      errors.push(`  ❌ ${filePath}:${lineNum} — ファイルが存在しません`);
      continue;
    }
    const lines = readFileSync(fullPath, 'utf8').split('\n');
    if (lineNum < 1 || lineNum > lines.length) {
      errors.push(`  ❌ ${filePath}:${lineNum} — 行番号が範囲外（ファイルは ${lines.length} 行）`);
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

// ─── 自動起票（緊急承認時） ───────────────────────────────────────────────────
function createFollowupIssue(prNumber, repo) {
  if (!repo || !prNumber) return;
  try {
    const deadline = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString().split('T')[0];
    const title = `[sop-followup] PR #${prNumber} 緊急承認 — 宿題期限: ${deadline}`;
    const body = [
      `## 宿題待ち（緊急承認による先行マージ）`,
      ``,
      `PR #${prNumber} が緊急承認で先行マージされました。`,
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

  // 危ない変更の処理
  if (hasDangerous) {
    let approvals = [];
    if (process.env.MOCK_APPROVALS !== undefined) {
      approvals = process.env.MOCK_APPROVALS ? process.env.MOCK_APPROVALS.split(',').filter(Boolean) : [];
    } else if (prNumber && repo) {
      try {
        const json = execSync(
          `gh api "repos/${repo}/pulls/${prNumber}/reviews" --jq '[.[] | select(.state == "APPROVED") | .user.login]'`,
          { encoding: 'utf8' }
        ).trim();
        approvals = JSON.parse(json);
      } catch {
        console.warn('⚠️  PR承認状態の取得に失敗 — 承認なしとして扱います');
      }
    }

    const hasAuth = approvals.some(a => AUTHORIZED_APPROVERS.includes(a));

    if (!hasAuth) {
      printFailure([
        `❌ 危険変更（migrations/ / deploy.yml / 本番スクリプト等）には`,
        `   認可された承認者（${AUTHORIZED_APPROVERS.join(' / ')}）の PR Approve が必要です。`,
        `   現在の承認者: ${approvals.length > 0 ? approvals.join(', ') : 'なし'}`,
        `   → shingo-ops に PR の Approve を依頼してください。`,
        `   ※ 本番障害の緊急対応は EMERGENCY: をPRタイトルに明記し、Shingo承認後にマージしてください。`,
      ]);
    }

    const mode = declaration ? declaration.mode : null;
    if (mode === '緊急') {
      console.log(`✅ 危ない変更：緊急承認（${approvals.join(', ')}）— pass＋宿題待ち起票`);
      createFollowupIssue(prNumber, repo);
    } else {
      console.log(`✅ 危ない変更：承認（${approvals.join(', ')}）些細 — pass`);
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
  hasFileCitations,
  validateFileCitations,
  validateDesignDoc,
};

// CLI として直接実行された場合のみ main() を呼ぶ
if (require.main === module) {
  main();
}
