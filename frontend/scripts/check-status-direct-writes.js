#!/usr/bin/env node
/**
 * check-status-direct-writes.js (ADR-120)
 *
 * ページ側で status → badge クラスを直書きしている箇所を検出する。
 *
 * Step 1（完了）: WARN_ONLY = true — 既存違反を警告のみで報告。ビルドは緑。
 * Step 3（現在）: WARN_ONLY = false — 違反がある場合は exit 1 で CI を止める。
 *
 * 検出パターン:
 *   1. テンプレートリテラル内の `badge-${` かつ `.badgeVariant` を含まない行
 *      （getStatusPresentation().badgeVariant 経由であれば除外される）
 *   2. `badgeVariant(` の呼び出し（非推奨集約関数）
 *   3. `getStageBadge(` の呼び出し（非推奨集約関数）
 *
 * 除外ディレクトリ:
 *   - design-preview/  (デザインプレビュー — getStatusPresentation() 使用が許可済み)
 *   - design-system/   (旧デザインシステムページ — ショーケース用ハードコード)
 *
 * 除外ファイル:
 *   - *.test.tsx (テストファイル)
 *
 * 明示的な例外:
 *   違反行の直前行に `status-ssot-exempt:` コメントを置くと、その行をスキップする。
 *   用途: boolean flag (is_active, feedback_type) など、status ドメインではない箇所。
 *   例 (TSX の場合):
 *     // status-ssot-exempt: is_active boolean
 *     <span className={`badge badge-${p.is_active ? "won" : "lost"}`} ... />
 *
 * 使用方法: node scripts/check-status-direct-writes.js
 * CI: npm run check:status-direct-writes
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, extname, relative, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_DIR = join(__dirname, '../src');

const WARN_ONLY = false;

const EXCLUDE_DIRS = new Set(['design-preview', 'design-system']);

/**
 * 検出パターン定義。
 * safeguard が指定されている場合、同一行に safeguard がマッチすれば違反とみなさない。
 */
const PATTERNS = [
  {
    re: /badge-\$\{/,
    safeguard: /\.badgeVariant\b/,
    label: 'badge-${...} 直書き (getStatusPresentation().badgeVariant を使用)',
  },
  {
    re: /\bbadgeVariant\s*\(/,
    label: 'badgeVariant() 非推奨 (getStatusPresentation("quote", status) を使用)',
  },
  {
    re: /\bgetStageBadge\s*\(/,
    label: 'getStageBadge() 非推奨 (getStatusPresentation("lead", status) を使用)',
  },
];

function collectTsxFiles(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      if (!EXCLUDE_DIRS.has(entry)) {
        results.push(...collectTsxFiles(full));
      }
    } else if (extname(entry) === '.tsx' && !entry.endsWith('.test.tsx')) {
      results.push(full);
    }
  }
  return results;
}

const files = collectTsxFiles(SRC_DIR);
const violations = [];

for (const file of files) {
  const rel = relative(SRC_DIR, file);
  const lines = readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, i) => {
    const prevLine = i > 0 ? lines[i - 1] : '';
    const isExempt = prevLine.includes('status-ssot-exempt') || line.includes('status-ssot-exempt');
    if (isExempt) return;

    for (const { re, safeguard, label } of PATTERNS) {
      if (re.test(line) && (!safeguard || !safeguard.test(line))) {
        violations.push({ rel, line: i + 1, content: line.trim(), label });
        break; // 1行につき1違反
      }
    }
  });
}

if (violations.length === 0) {
  console.log('✅ status-direct-writes: 違反なし');
  process.exit(0);
}

const icon = WARN_ONLY ? '⚠️' : '❌';
for (const v of violations) {
  console.log(`${icon} src/${v.rel}:${v.line}`);
  console.log(`   [${v.label}]`);
  console.log(`   ${v.content.slice(0, 120)}`);
}

if (WARN_ONLY) {
  console.log(`\n⚠️  status-direct-writes: ${violations.length} 件の既存違反（警告モード・ビルド継続）`);
  process.exit(0);
} else {
  console.log(`\n❌ status-direct-writes: ${violations.length} 件の違反`);
  console.log('   getStatusPresentation() を使用してください（docs/handoff/decision-layer-01/design.md 参照）。');
  console.log('   boolean flag など status ドメイン外の場合は直前行に status-ssot-exempt: コメントを追加してください。');
  process.exit(1);
}
