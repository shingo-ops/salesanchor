#!/usr/bin/env node
/**
 * check-ui-governance.js
 *
 * PRで追加・変更された frontend/src/pages/ 配下の .tsx ファイルに
 * 新規の「生UI部品」が増えていないかを検査する。
 *
 * 検出対象（3種）:
 *   - 生 <select>
 *   - 生 <input type="text"|"search"|type省略>  ← 複数行対応
 *   - 自作タブ（classNameにtabを含むがtableを含まないトークン）
 *
 * 判定方式:
 *   各変更ファイルについて BASE/HEAD 両 SHA の全文を取得し、
 *   種別ごとに件数を比較。HEAD件数 > BASE件数 なら exit 1（赤）。
 *   （既存の生実装はBASE/HEAD両方に存在→件数同→緑＝既存を赤化しない）
 *
 * 例外口:
 *   違反要素の直前行または同一行に下記コメントがある場合は除外:
 *   JSX コメント書式: ui-allow: <理由> (#<課題番号>)
 *   ※ 理由と課題番号の両方が必須。欠ければ無効（赤のまま）。
 *
 * 踏襲: scripts/check-dangling-routes.js（git show <sha>:path 方式）
 * 設計: docs/adr/ADR-144-ui-component-governance.md
 *
 * CI実行方法:
 *   BASE_SHA=<sha> HEAD_SHA=<sha> node scripts/check-ui-governance.js
 */

'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
const PAGES_DIR = 'frontend/src/pages/';

// ---------------------------------------------------------------------------
// ユーティリティ
// ---------------------------------------------------------------------------

/**
 * git show で指定 SHA 時点のファイル内容を取得する。
 * 存在しない場合は空文字列を返す（新規ファイルの BASE 側など）。
 */
function showFile(sha, filePath) {
  const result = spawnSync('git', ['show', `${sha}:${filePath}`], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
  return result.status === 0 ? result.stdout : '';
}

/**
 * PR の変更ファイル一覧を取得する（rename 対応）。
 * 戻り値: [{ headPath, basePath }]
 *   - headPath: HEAD 側のファイルパス（常に存在）
 *   - basePath: BASE 側のパス。新規追加(A)なら null、rename(R)なら旧パス
 */
function getChangedFiles(baseSha, headSha) {
  const result = spawnSync(
    'git',
    ['diff', '--name-status', '-M', baseSha, headSha, '--', PAGES_DIR],
    { cwd: REPO_ROOT, encoding: 'utf8' }
  );
  if (result.status !== 0) return [];

  const files = [];
  for (const line of result.stdout.split('\n')) {
    if (!line.trim()) continue;
    const parts = line.split('\t');
    const status = parts[0];

    // 削除(D)はスキップ
    if (status.startsWith('D')) continue;

    let headPath, basePath;
    if (status.startsWith('R')) {
      // rename: parts[1]=旧パス, parts[2]=新パス
      basePath = parts[1];
      headPath = parts[2];
    } else {
      headPath = parts[1];
      basePath = status === 'A' ? null : parts[1];
    }

    if (!headPath || !headPath.endsWith('.tsx')) continue;
    if (headPath.endsWith('.stories.tsx')) continue;
    if (headPath.includes('/design-system/')) continue;
    if (headPath.includes('/design-preview/')) continue;

    files.push({ headPath, basePath });
  }
  return files;
}

// ---------------------------------------------------------------------------
// ui-allow ヘルパー
// ---------------------------------------------------------------------------

/**
 * 行に有効な ui-allow コメントが含まれるか判定する。
 * 書式: JSX コメント  ui-allow: <理由（非空）> (#<数字>)
 * 理由と課題番号の両方が必須。
 */
function isValidUiAllow(line) {
  return /ui-allow:\s+\S+.*\(#\d+\)/.test(line);
}

/**
 * 文字列中の指定オフセットが何行目（0始まり）にあるかを返す。
 */
function getLineIndex(content, charPos) {
  return content.slice(0, charPos).split('\n').length - 1;
}

/**
 * lineIdx 行（0始まり）またはその直前行に有効な ui-allow があるか確認する。
 */
function hasUiAllowBefore(lines, lineIdx) {
  const candidates = [lines[lineIdx]];
  if (lineIdx > 0) candidates.push(lines[lineIdx - 1]);
  return candidates.some(isValidUiAllow);
}

/**
 * コンテンツ中の ui-allow コメントを全て収集する。
 * { lineNum（1始まり）, content, valid } の配列を返す。
 */
function findAllUiAllows(content, filePath) {
  return content.split('\n').reduce((acc, line, idx) => {
    if (/ui-allow:/.test(line)) {
      acc.push({
        file: filePath,
        lineNum: idx + 1,
        content: line.trim(),
        valid: isValidUiAllow(line),
      });
    }
    return acc;
  }, []);
}

// ---------------------------------------------------------------------------
// 検出ロジック: 生 <select>
// ---------------------------------------------------------------------------

/**
 * コンテンツ内の生 <select> 件数を返す。
 * ui-allow が直前/同行にある要素は除外する。
 * recon F-E2 により、コメント/文字列内誤検知はゼロ → 単純照合で安全。
 */
function countSelect(content) {
  const lines = content.split('\n');
  const re = /<select[\s>/]/g;
  let count = 0;
  let m;
  while ((m = re.exec(content)) !== null) {
    const lineIdx = getLineIndex(content, m.index);
    if (!hasUiAllowBefore(lines, lineIdx)) count++;
  }
  return count;
}

// ---------------------------------------------------------------------------
// 検出ロジック: 生 <input type="text"|"search"|省略>
// ---------------------------------------------------------------------------

/**
 * コンテンツから <input ...> の開始タグ文字列を全て抽出する。
 * 波括弧ネスト depth=0 の最初の > を閉じとみなす（value={a > b} 対策）。
 * recon F-E1: 複数行対応必須（type が別行になるケースが224件ある）。
 */
function extractInputTags(content) {
  const tags = [];
  let i = 0;
  while (i < content.length) {
    const idx = content.indexOf('<input', i);
    if (idx === -1) break;

    // <input の直後は空白 / > / / でなければコンポーネント名とみなしスキップ
    const nextChar = content[idx + 6];
    if (nextChar === undefined || !/[\s>/]/.test(nextChar)) {
      i = idx + 6;
      continue;
    }

    // 開始タグ末尾の > を見つける（depth=0 の > のみ）
    let depth = 0;
    let j = idx + 6;
    let tagStr = content.slice(idx, idx + 6);
    while (j < content.length) {
      const ch = content[j];
      if (ch === '{') depth++;
      else if (ch === '}') depth--;
      else if (ch === '>' && depth === 0) {
        tagStr += ch;
        j++;
        break;
      }
      tagStr += ch;
      j++;
    }
    tags.push({ tagStr, pos: idx });
    i = j;
  }
  return tags;
}

/**
 * 抽出した <input> タグが検出対象（type=text/search/省略）かどうか判定する。
 */
function isDetectableInput(tagStr) {
  const typeMatch = tagStr.match(/\btype\s*=\s*["']([^"']*)["']/);
  if (!typeMatch) return true; // type省略 = HTML既定text = 検出対象
  const val = typeMatch[1].toLowerCase();
  return val === 'text' || val === 'search';
}

/**
 * コンテンツ内の検出対象 <input> 件数を返す（ui-allow 除外済み）。
 */
function countInput(content) {
  const lines = content.split('\n');
  let count = 0;
  for (const { tagStr, pos } of extractInputTags(content)) {
    if (!isDetectableInput(tagStr)) continue;
    const lineIdx = getLineIndex(content, pos);
    if (!hasUiAllowBefore(lines, lineIdx)) count++;
  }
  return count;
}

// ---------------------------------------------------------------------------
// 検出ロジック: 自作タブ
// ---------------------------------------------------------------------------

/**
 * className トークンがタブとみなされるか判定する。
 * /tab/ に一致し /table/ に一致しない場合のみタブとみなす。
 * recon F-E3: data-table 等の誤検知を /table/ 除外で防ぐ。
 */
function isTabToken(token) {
  return /tab/.test(token) && !/table/.test(token);
}

/**
 * コンテンツ内の自作タブ件数を返す（ui-allow 除外済み）。
 * 静的 className="..." とテンプレートリテラル className={`...`} の両方を対象とする。
 */
function countTab(content) {
  const lines = content.split('\n');
  let count = 0;
  let m;

  // 静的文字列: className="..."
  const staticRe = /className\s*=\s*"([^"]*)"/g;
  while ((m = staticRe.exec(content)) !== null) {
    const tokens = m[1].split(/\s+/).filter(Boolean);
    if (tokens.some(isTabToken)) {
      const lineIdx = getLineIndex(content, m.index);
      if (!hasUiAllowBefore(lines, lineIdx)) count++;
    }
  }

  // テンプレートリテラル: className={`...`}
  // ${...} 部分を空白に置換して静的トークンのみ評価する
  const templateRe = /className\s*=\s*\{`([^`]*)`\}/g;
  while ((m = templateRe.exec(content)) !== null) {
    const staticPart = m[1].replace(/\$\{[^}]*\}/g, ' ');
    const tokens = staticPart.split(/\s+/).filter(Boolean);
    if (tokens.some(isTabToken)) {
      const lineIdx = getLineIndex(content, m.index);
      if (!hasUiAllowBefore(lines, lineIdx)) count++;
    }
  }

  return count;
}

// ---------------------------------------------------------------------------
// 集計
// ---------------------------------------------------------------------------

function countAll(content) {
  return {
    select: countSelect(content),
    input: countInput(content),
    tab: countTab(content),
  };
}

// ---------------------------------------------------------------------------
// メイン処理
// ---------------------------------------------------------------------------

function main() {
  const BASE_SHA = process.env.BASE_SHA;
  const HEAD_SHA = process.env.HEAD_SHA;

  if (!BASE_SHA || !HEAD_SHA) {
    console.error('[ERROR] BASE_SHA と HEAD_SHA 環境変数が必要です');
    process.exit(1);
  }

  console.log(`[INFO] BASE_SHA=${BASE_SHA} HEAD_SHA=${HEAD_SHA}`);

  const changedFiles = getChangedFiles(BASE_SHA, HEAD_SHA);
  console.log(`[INFO] 対象ファイル数: ${changedFiles.length}`);

  if (changedFiles.length === 0) {
    console.log('✅ UI governance: pages/ への変更なし。チェックをスキップします。');
    process.exit(0);
  }

  const violations = [];
  const newUiAllows = [];

  for (const { headPath, basePath } of changedFiles) {
    const baseContent = basePath ? showFile(BASE_SHA, basePath) : '';
    const headContent = showFile(HEAD_SHA, headPath);

    const baseCounts = countAll(baseContent);
    const headCounts = countAll(headContent);

    const typeLabels = {
      select: '生<select>',
      input:  '生<input text/search/省略>',
      tab:    '自作タブ',
    };

    for (const type of ['select', 'input', 'tab']) {
      if (headCounts[type] > baseCounts[type]) {
        violations.push({
          file: headPath,
          type,
          label: typeLabels[type],
          base: baseCounts[type],
          head: headCounts[type],
        });
      }
    }

    // HEAD で新規に追加された ui-allow を収集（レビュー注意喚起のため）
    const baseAllowContents = new Set(
      findAllUiAllows(baseContent, basePath || headPath).map((a) => a.content)
    );
    for (const allow of findAllUiAllows(headContent, headPath)) {
      if (!baseAllowContents.has(allow.content)) {
        newUiAllows.push(allow);
      }
    }
  }

  // 新規 ui-allow の別枠表示（人間レビューに必ず乗せるため）
  if (newUiAllows.length > 0) {
    console.warn(`\n⚠️  新規 ui-allow ${newUiAllows.length} 件（人間レビュー必須）:`);
    for (const a of newUiAllows) {
      const validity = a.valid
        ? '✅ 書式OK'
        : '❌ 書式不正（ui-allow: <理由> (#<番号>) の両方が必須）';
      console.warn(`   ${a.file}:${a.lineNum}  ${validity}`);
      console.warn(`   → ${a.content}`);
    }
  }

  if (violations.length > 0) {
    console.error(
      '\n❌ UI governance: 新規の生UI部品を検出しました\n' +
      '   金型（components/）を使うか、やむを得ない場合は {/* ui-allow: <理由> (#<番号>) */} を付けてください\n'
    );
    for (const v of violations) {
      console.error(
        `   ${v.file}  [${v.label}]  BASE=${v.base} → HEAD=${v.head} (+${v.head - v.base})`
      );
    }
    console.error('\n   詳細: docs/CC_UI_GOVERNANCE.md / docs/adr/ADR-144-ui-component-governance.md');
    process.exit(1);
  }

  console.log('\n✅ UI governance: 新規ハードコードなし');
  process.exit(0);
}

// require された場合は検出関数をエクスポート（テスト用）
if (require.main === module) {
  main();
} else {
  module.exports = {
    countSelect,
    countInput,
    countTab,
    isValidUiAllow,
    isDetectableInput,
    extractInputTags,
    isTabToken,
  };
}
