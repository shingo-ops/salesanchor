#!/usr/bin/env node
/**
 * check-dangling-routes.js
 *
 * PRで削除されたバックエンドルート（BASE_SHA → HEAD_SHA）が
 * フロントエンドから参照されている場合に exit 1 で失敗する。
 *
 * アルゴリズム:
 *   removed = backendRoutes(BASE_SHA) − backendRoutes(HEAD_SHA)
 *   dangling = removed ∩ frontendRefs
 *   dangling が空でなければ exit 1（赤）、空なら exit 0（緑）
 *
 * 実行方法（CIから）:
 *   BASE_SHA=<sha> HEAD_SHA=<sha> node scripts/check-dangling-routes.js
 *
 * テスト用モック環境変数:
 *   MOCK_BACKEND_BASE=<JSON>  BASE時のルート配列を直接注入
 *   MOCK_BACKEND_HEAD=<JSON>  HEAD時のルート配列を直接注入
 *   MOCK_FRONTEND_REFS=<JSON> フロントエンド参照パス配列を直接注入
 */

'use strict';

const { execSync, spawnSync } = require('child_process');
const { existsSync, readdirSync, readFileSync } = require('fs');
const path = require('path');
const { globSync } = require('fs');

// ---------------------------------------------------------------------------
// 定数
// ---------------------------------------------------------------------------
const REPO_ROOT = path.resolve(__dirname, '..');
const MAIN_PY = 'backend/app/main.py';
const ROUTERS_DIR = 'backend/app/routers';
const FRONTEND_SRC = 'frontend/src';
const API_BASE = '/api/v1';

// translation.py だけ自前 prefix を持つ（二重にならないよう特別扱い）
const TRANSLATION_SELF_PREFIX = '/translation';

// フロントエンドで /api/v1 を直接渡している二重 prefix 異常ファイル（正規化時に前置しない）
const DOUBLE_PREFIX_ANOMALY_FILES = new Set([
  'frontend/src/pages/admin/ChannelMastersPage.tsx',
  'frontend/src/pages/inbox/ManualRecordSection.tsx',
]);

// ---------------------------------------------------------------------------
// ユーティリティ
// ---------------------------------------------------------------------------

/**
 * git show でファイル内容を取得する。
 * ファイルが SHA に存在しなければ空文字列を返す。
 */
function gitShowFile(sha, filePath) {
  const result = spawnSync('git', ['show', `${sha}:${filePath}`], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
  if (result.status !== 0) return '';
  return result.stdout;
}

/**
 * ディレクトリ内の全ファイル一覧を git ls-tree で取得する。
 * SHA 時点のファイルパスを返す。
 */
function gitListDir(sha, dirPath) {
  const result = spawnSync(
    'git',
    ['ls-tree', '-r', '--name-only', sha, dirPath],
    { cwd: REPO_ROOT, encoding: 'utf8' }
  );
  if (result.status !== 0) return [];
  return result.stdout
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.endsWith('.py'));
}

/**
 * パスパラメータ `{param_name}` を `{*}` に正規化する。
 * クエリ文字列は除去する。
 */
function normalizePath(p) {
  return p
    .replace(/\?.*$/, '')             // クエリ除去
    .replace(/\{[^}]+\}/g, '{*}');    // {param} → {*}
}

// ---------------------------------------------------------------------------
// バックエンド ルート抽出
// ---------------------------------------------------------------------------

/**
 * main.py を解析して `include_router(module.router, prefix=...)` マップを返す。
 * 戻り値: Map<moduleFileName, includedPrefix>
 * 例: "translation" → "/api/v1" （translation.py 自身の prefix は別途処理）
 *
 * 同一モジュールが複数 include される場合（public_router / router）は両方登録する。
 * ここでは .py ファイル名（拡張子なし）→ prefix[] の多対多マップを返す。
 */
function parseIncludeRouterMap(mainPyContent) {
  // import 文から モジュール変数名 → ファイル名 をマップ
  // 例: from app.routers import analytics  → analytics → analytics
  // 例: from app.routers import google_calendar → google_calendar → google_calendar
  const importMap = new Map(); // importedName → routerFileName (拡張子なし)

  const importRe = /from\s+app\.routers(?:\.\w+)?\s+import\s+([\w,\s]+)/g;
  let m;
  while ((m = importRe.exec(mainPyContent)) !== null) {
    const names = m[1].split(',').map((n) => n.trim()).filter(Boolean);
    for (const name of names) {
      importMap.set(name, name);
    }
  }

  // include_router(module.router, prefix="...", ...) を抽出
  // 複数行に渡る可能性があるため 500 文字程度のウィンドウで処理
  const includeRe = /app\.include_router\s*\(\s*([\w.]+?)\s*,\s*prefix\s*=\s*["']([^"']+)["']/g;
  const prefixMap = new Map(); // routerFileName → Set<prefix>

  while ((m = includeRe.exec(mainPyContent)) !== null) {
    const routerExpr = m[1]; // 例: "analytics.router", "translation.router"
    const prefix = m[2];

    // モジュール名抽出（例: "google_calendar.public_router" → "google_calendar"）
    const moduleName = routerExpr.split('.')[0];
    const fileName = importMap.get(moduleName) || moduleName;

    if (!prefixMap.has(fileName)) {
      prefixMap.set(fileName, new Set());
    }
    prefixMap.get(fileName).add(prefix);
  }

  return prefixMap;
}

/**
 * ルーターファイルから `@router.{method}("path")` を抽出して実効パスセットを返す。
 * - translation.py のみ自前 prefix を持つため includePrefix + selfPrefix + routePath で合成
 * - その他は includePrefix + routePath
 */
function extractRoutesFromFile(fileContent, fileName, includePrefixes) {
  const routes = new Set();

  // router 自身の prefix（translation.py のみ）
  let selfPrefix = '';
  const selfPrefixMatch = fileContent.match(/router\s*=\s*APIRouter\s*\(\s*prefix\s*=\s*["']([^"']+)["']/);
  if (selfPrefixMatch) {
    selfPrefix = selfPrefixMatch[1];
  }

  // @router.{method}("path") を抽出（多行対応: デコレータ行から最初の文字列引数を取得）
  // パターン: @router.get(\n    "/path",
  const decoratorRe = /@router\.(get|post|put|patch|delete)\s*\(\s*\n?\s*["']([^"']+)["']/g;
  let m;
  while ((m = decoratorRe.exec(fileContent)) !== null) {
    const routePath = m[2];

    for (const includePrefix of includePrefixes) {
      const fullPath = normalizePath(includePrefix + selfPrefix + routePath);
      routes.add(fullPath);
    }
  }

  return routes;
}

/**
 * 指定 SHA 時点のバックエンドルートセットを返す。
 */
function extractBackendRoutes(sha) {
  const mainPyContent = gitShowFile(sha, MAIN_PY);
  if (!mainPyContent) {
    console.warn(`[WARN] main.py が SHA=${sha} に存在しません`);
    return new Set();
  }

  const prefixMap = parseIncludeRouterMap(mainPyContent);
  const allRoutes = new Set();

  const routerFiles = gitListDir(sha, ROUTERS_DIR);

  for (const filePath of routerFiles) {
    const fileName = path.basename(filePath, '.py');
    const includePrefixes = prefixMap.get(fileName);
    if (!includePrefixes || includePrefixes.size === 0) {
      // include_router されていないファイル（__init__.py 等）はスキップ
      continue;
    }

    const content = gitShowFile(sha, filePath);
    if (!content) continue;

    const routes = extractRoutesFromFile(content, fileName, includePrefixes);
    for (const r of routes) {
      allRoutes.add(r);
    }
  }

  return allRoutes;
}

// ---------------------------------------------------------------------------
// フロントエンド API 参照抽出
// ---------------------------------------------------------------------------

/**
 * フロントエンドソースファイルから api.(get|post|put|patch|delete)(...) の
 * 第1引数パスを抽出して正規化する。
 * - テスト/ストーリー/モックファイルは除外
 * - 変数セグメントが解決不能なものはスキップ（誤検知防止）
 * - /api/v1 が既についていないものは前置（二重 prefix 異常2件は例外）
 */
function extractFrontendRefs() {
  const refs = new Set();

  // frontend/src 以下の .ts/.tsx ファイルを取得（テスト/ストーリー/モック除外）
  function walkDir(dirPath) {
    let files = [];
    try {
      const entries = readdirSync(dirPath, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        if (entry.isDirectory()) {
          // テスト・ストーリーディレクトリは除外
          if (['__tests__', 'tests', 'stories', '__mocks__', 'mocks'].includes(entry.name)) {
            continue;
          }
          files = files.concat(walkDir(fullPath));
        } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
          // テスト/ストーリー/モックファイルは除外
          if (/\.(test|spec|stories|mock)\.(ts|tsx)$/.test(entry.name)) {
            continue;
          }
          files.push(fullPath);
        }
      }
    } catch (_) {
      // ディレクトリが存在しない場合は無視
    }
    return files;
  }

  const srcDir = path.join(REPO_ROOT, FRONTEND_SRC);
  const files = walkDir(srcDir);

  // api.(method)(`...`) を抽出する正規表現
  // テンプレートリテラル・文字列の両方に対応
  const apiCallRe = /\bapi\s*\.\s*(?:get|post|put|patch|delete)\s*(?:<[^>]*>)?\s*\(\s*(`[^`]*`|"[^"]*"|'[^']*')/g;

  for (const filePath of files) {
    const relativePath = path.relative(REPO_ROOT, filePath);
    let content;
    try {
      content = readFileSync(filePath, 'utf8');
    } catch (_) {
      continue;
    }

    const isDoublePrefix = DOUBLE_PREFIX_ANOMALY_FILES.has(relativePath);

    let m;
    while ((m = apiCallRe.exec(content)) !== null) {
      const rawArg = m[1];

      // クォート除去
      const inner = rawArg.slice(1, -1);

      // 変数セグメントが解決不能なもの（${variable} 形式で変数名が残る）はスキップ
      // ただし ${someVar}/fixed は {*}/fixed として処理可能
      // 完全に変数だけのセグメントではなく、静的部分が混在するものは処理する
      // 例: /discord/${action}/${leadId} → スキップ（action/leadId が完全に変数）
      // 例: /leads/${leadId}/messages → /leads/{*}/messages として処理OK
      //
      // 解決不能判定: テンプレートリテラルで ${} のみで構成されるセグメントが存在する場合
      // → ここでは保守的に、すべての ${...} を {*} に変換して処理する
      // → ただし、パスの最初のセグメントが "/" で始まらない（完全変数パス）はスキップ
      const withWildcard = inner.replace(/\$\{[^}]+\}/g, '{*}');

      // パスが / で始まらない場合（変数 interpolation の結果）はスキップ
      if (!withWildcard.startsWith('/')) {
        console.log(`[SKIP] 解決不能パス: ${relativePath}: ${inner}`);
        continue;
      }

      // クエリ除去・{param} 正規化
      let normalized = normalizePath(withWildcard);

      // /api/v1 前置（二重 prefix 異常ファイルは既に /api/v1 で始まるのでスキップ）
      if (!normalized.startsWith('/api/')) {
        normalized = API_BASE + normalized;
      }
      // 二重 prefix 異常: /api/v1/api/v1/... にならないよう確認（冗長だが安全のため）
      if (normalized.startsWith('/api/v1/api/')) {
        normalized = normalized.replace('/api/v1/api/', '/api/');
      }

      refs.add(normalized);
    }
  }

  return refs;
}

// ---------------------------------------------------------------------------
// メイン処理
// ---------------------------------------------------------------------------

function main() {
  // モック注入（テスト用）
  if (process.env.MOCK_BACKEND_BASE && process.env.MOCK_BACKEND_HEAD && process.env.MOCK_FRONTEND_REFS) {
    const baseRoutes = new Set(JSON.parse(process.env.MOCK_BACKEND_BASE));
    const headRoutes = new Set(JSON.parse(process.env.MOCK_BACKEND_HEAD));
    const frontendRefs = new Set(JSON.parse(process.env.MOCK_FRONTEND_REFS));

    const removed = new Set([...baseRoutes].filter((r) => !headRoutes.has(r)));
    const dangling = [...removed].filter((r) => frontendRefs.has(r));

    if (dangling.length > 0) {
      console.error('❌ dangling route 検出（フロント参照あり・バックエンドから削除済み）:');
      for (const r of dangling) {
        console.error(`   ${r}`);
      }
      process.exit(1);
    }

    console.log(`✅ dangling route なし（removed=${removed.size}, frontend_refs=${frontendRefs.size}）`);
    process.exit(0);
  }

  const BASE_SHA = process.env.BASE_SHA;
  const HEAD_SHA = process.env.HEAD_SHA;

  if (!BASE_SHA || !HEAD_SHA) {
    console.error('[ERROR] BASE_SHA と HEAD_SHA 環境変数が必要です');
    process.exit(1);
  }

  console.log(`[INFO] BASE_SHA=${BASE_SHA} HEAD_SHA=${HEAD_SHA}`);

  // バックエンドルート抽出
  console.log('[INFO] BASE のバックエンドルートを抽出中...');
  const baseRoutes = extractBackendRoutes(BASE_SHA);
  console.log(`[INFO] BASE ルート数: ${baseRoutes.size}`);

  console.log('[INFO] HEAD のバックエンドルートを抽出中...');
  const headRoutes = extractBackendRoutes(HEAD_SHA);
  console.log(`[INFO] HEAD ルート数: ${headRoutes.size}`);

  // 削除されたルート
  const removed = new Set([...baseRoutes].filter((r) => !headRoutes.has(r)));
  console.log(`[INFO] 削除されたルート数: ${removed.size}`);

  if (removed.size === 0) {
    console.log('✅ ルート削除なし。チェックをスキップします。');
    process.exit(0);
  }

  for (const r of [...removed].sort()) {
    console.log(`[REMOVED] ${r}`);
  }

  // フロントエンド参照抽出
  console.log('[INFO] フロントエンド API 参照を抽出中...');
  const frontendRefs = extractFrontendRefs();
  console.log(`[INFO] フロントエンド参照数: ${frontendRefs.size}`);

  // 突合
  const dangling = [...removed].filter((r) => frontendRefs.has(r));

  if (dangling.length > 0) {
    console.error('');
    console.error('❌ dangling route 検出（フロント参照あり・バックエンドから削除済み）:');
    for (const r of dangling) {
      console.error(`   ${r}`);
    }
    console.error('');
    console.error('削除前に frontend 側の参照を更新してください。');
    process.exit(1);
  }

  console.log('✅ dangling route なし。全削除ルートはフロントエンドから未参照です。');
  process.exit(0);
}

main();
