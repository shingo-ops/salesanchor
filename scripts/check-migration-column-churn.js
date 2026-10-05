#!/usr/bin/env node
/**
 * check-migration-column-churn.js
 *
 * scripts/run_all_migrations.sh の登録順に沿って migrations/*.sql
 * （run_py が読む .sql ファイルも含む）を走査し、同一 (table, column) に対して
 * ADD → 後で DROP（カラム番号を消費し続ける「チャーン」）が起きている箇所を検出する。
 * 逆方向（DROP → 後で ADD）は別クラス（警告のみ、exit は変えない）として報告する。
 *
 * 背景: ADR-1005（docs/adr/ADR-1005-migration-run-once-ledger.md）Stage 0 ①。
 *       2026-10-03 インシデント（condition/unit/category_classification の
 *       ADD が #3958 で削除された例、tcg_uuid の ADD→guard→DROP の例）を踏まえ、
 *       同種の column churn を機械的に検出できるようにする。
 *
 * 実行方法:
 *   node scripts/check-migration-column-churn.js
 *
 * 終了コード:
 *   0 = 未許可の churn なし（かつ allowlist が stale でない）
 *   1 = 未許可の churn あり、または allowlist が stale
 *
 * テスト用オーバーライド（回帰テスト専用）:
 *   MIGRATIONS_SCRIPT_OVERRIDE=<path>   run_all_migrations.sh の代わりに読むファイル
 *   ALLOWLIST_OVERRIDE=<path>           allowlist の代わりに読むファイル
 *   REPO_ROOT_OVERRIDE=<path>           repo root の代わりに使うディレクトリ
 */
'use strict';

const { execSync } = require('child_process');
const { existsSync, readFileSync } = require('fs');
const path = require('path');

const REPO_ROOT =
  process.env.REPO_ROOT_OVERRIDE ||
  execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();

const MIGRATIONS_SCRIPT_PATH =
  process.env.MIGRATIONS_SCRIPT_OVERRIDE ||
  path.join(REPO_ROOT, 'scripts/run_all_migrations.sh');

const ALLOWLIST_PATH =
  process.env.ALLOWLIST_OVERRIDE ||
  path.join(REPO_ROOT, 'scripts/migration-column-churn-allowlist.json');

// ---------------------------------------------------------------------------
// 1. run_all_migrations.sh から登録順リストを抽出
// ---------------------------------------------------------------------------

/**
 * @returns {{kind: 'sql'|'py', filePath: string, order: number}[]}
 */
function parseRegistrations(migrationsScriptPath) {
  const text = readFileSync(migrationsScriptPath, 'utf8');
  const lines = text.split('\n');
  const registrations = [];
  let order = 0;
  for (const line of lines) {
    const sqlMatch = line.match(/^run_sql[ \t]+(\S+)/);
    const pyMatch = line.match(/^run_py[ \t]+(\S+)/);
    if (sqlMatch) {
      order += 1;
      registrations.push({ kind: 'sql', filePath: sqlMatch[1], order });
    } else if (pyMatch) {
      order += 1;
      registrations.push({ kind: 'py', filePath: pyMatch[1], order });
    }
  }
  return registrations;
}

/**
 * run_py スクリプト本文から、それが読む .sql ファイル名を抽出する。
 * 既存コードのパターン: MIGRATIONS_DIR / "NNN_xxx.sql" や
 * リスト要素 "NNN_xxx.sql"。スラッシュを含む文字列はそのまま repo-root 相対とし、
 * スラッシュを含まない文字列は migrations/ を前置する。
 * @returns {string[]} repo-root 相対パスの配列（出現順）
 */
function extractReferencedSqlFiles(pyContent) {
  const results = [];
  const re = /(['"])([^'"]*\.sql)\1/g;
  let m;
  while ((m = re.exec(pyContent)) !== null) {
    const raw = m[2];
    const resolved = raw.includes('/') ? raw : `migrations/${raw}`;
    results.push(resolved);
  }
  return results;
}

/**
 * registrations を「実行順に走査するソースファイル一覧」に展開する。
 * run_py の場合は: ①そのスクリプト自体（インラインSQLの可能性）→ order.0
 *               ②参照している .sql を出現順 → order.001, order.002, ...
 * @returns {{filePath: string, kind: 'sql'|'py', order: number}[]}
 */
function expandSources(registrations, repoRoot) {
  const sources = [];
  for (const reg of registrations) {
    if (reg.kind === 'sql') {
      sources.push({ filePath: reg.filePath, kind: 'sql', order: reg.order });
      continue;
    }
    // run_py
    const abs = path.join(repoRoot, reg.filePath);
    sources.push({ filePath: reg.filePath, kind: 'py', order: reg.order });
    if (existsSync(abs)) {
      const content = readFileSync(abs, 'utf8');
      const referenced = extractReferencedSqlFiles(content);
      referenced.forEach((sqlPath, idx) => {
        sources.push({
          filePath: sqlPath,
          kind: 'sql',
          order: reg.order + (idx + 1) / 1000,
        });
      });
    }
  }
  return sources;
}

// ---------------------------------------------------------------------------
// 2. コメント除去
// ---------------------------------------------------------------------------

/** SQL コメント（-- 行末まで、/* ブロック *\/）を空白に置換（行番号を保持） */
function stripSqlComments(text) {
  let out = text.replace(/\/\*[\s\S]*?\*\//g, (block) =>
    block.replace(/[^\n]/g, ' '),
  );
  out = out.replace(/--[^\n]*/g, (line) => ' '.repeat(line.length));
  return out;
}

/** Python コメント（# 行末まで）を空白に置換（行番号を保持） */
function stripPyComments(text) {
  return text.replace(/#[^\n]*/g, (line) => ' '.repeat(line.length));
}

// ---------------------------------------------------------------------------
// 3. ALTER TABLE 抽出
// ---------------------------------------------------------------------------

const TARGET_RE =
  '(?:%I|\\{schema\\}|tenant_\\d+|public)\\.[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*';

const ALTER_RE = new RegExp(
  `ALTER\\s+TABLE\\s+(?:IF\\s+EXISTS\\s+)?(?:ONLY\\s+)?(${TARGET_RE})\\s+([^;'"]*?)(?=[;'"]|\\$q\\$|$)`,
  'gi',
);

function normalizeTable(raw) {
  const parts = raw.split('.');
  if (parts.length === 1) {
    return `public.${parts[0]}`;
  }
  const [schema, table] = parts;
  if (schema.toLowerCase() === 'public') {
    return `public.${table}`;
  }
  return `tenant.${table}`;
}

/** 括弧の深さを見て、トップレベルのカンマでのみ分割する */
function splitTopLevel(str) {
  const parts = [];
  let depth = 0;
  let buf = '';
  for (const ch of str) {
    if (ch === '(') depth += 1;
    if (ch === ')') depth -= 1;
    if (ch === ',' && depth === 0) {
      parts.push(buf);
      buf = '';
    } else {
      buf += ch;
    }
  }
  if (buf.trim().length > 0) parts.push(buf);
  return parts;
}

const ADD_NON_COLUMN_KEYWORDS = new Set([
  'CONSTRAINT',
  'PRIMARY',
  'UNIQUE',
  'CHECK',
  'FOREIGN',
  'EXCLUDE',
]);
const DROP_NON_COLUMN_KEYWORDS = new Set(['CONSTRAINT', 'DEFAULT', 'NOT']);

function matchAddColumn(clause) {
  let m = clause.match(/^ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)/i);
  if (m) return m[1];
  m = clause.match(/^ADD\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)/i);
  if (m && !ADD_NON_COLUMN_KEYWORDS.has(m[1].toUpperCase())) return m[1];
  return null;
}

function matchDropColumn(clause) {
  let m = clause.match(/^DROP\s+COLUMN\s+(?:IF\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)/i);
  if (m) return m[1];
  m = clause.match(/^DROP\s+(?:IF\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)/i);
  if (m && !DROP_NON_COLUMN_KEYWORDS.has(m[1].toUpperCase())) return m[1];
  return null;
}

function lineNumberAt(text, index) {
  let line = 1;
  for (let i = 0; i < index; i += 1) {
    if (text[i] === '\n') line += 1;
  }
  return line;
}

/**
 * ファイル内容（コメント除去済み・元の index 計算用に生テキストも必要）から
 * ADD/DROP COLUMN イベントを抽出する。
 * @returns {{table: string, column: string, action: 'ADD'|'DROP', line: number}[]}
 */
function extractColumnEvents(strippedText, originalText) {
  const events = [];
  let m;
  ALTER_RE.lastIndex = 0;
  while ((m = ALTER_RE.exec(strippedText)) !== null) {
    const rawTarget = m[1];
    const clauseBlob = m[2];
    const table = normalizeTable(rawTarget);
    const line = lineNumberAt(originalText, m.index);
    const clauses = splitTopLevel(clauseBlob);
    for (const rawClause of clauses) {
      const clause = rawClause.trim();
      if (!clause) continue;
      const addCol = matchAddColumn(clause);
      if (addCol) {
        events.push({ table, column: addCol.toLowerCase(), action: 'ADD', line });
        continue;
      }
      const dropCol = matchDropColumn(clause);
      if (dropCol) {
        events.push({ table, column: dropCol.toLowerCase(), action: 'DROP', line });
      }
    }
  }
  return events;
}

// ---------------------------------------------------------------------------
// 4. 走査本体
// ---------------------------------------------------------------------------

/**
 * @returns {{churn: Array, warnings: Array}}
 */
function scan(repoRoot, migrationsScriptPath) {
  const registrations = parseRegistrations(migrationsScriptPath);
  const sources = expandSources(registrations, repoRoot);

  /** key: "table::column" -> events [{action, file, line, order}] */
  const byColumn = new Map();

  for (const src of sources) {
    const abs = path.join(repoRoot, src.filePath);
    if (!existsSync(abs)) continue; // existence は別チェック（check-migration-registration-exists.sh）の責務
    const original = readFileSync(abs, 'utf8');
    const stripped = src.kind === 'sql' ? stripSqlComments(original) : stripPyComments(original);
    const events = extractColumnEvents(stripped, original);
    for (const ev of events) {
      const key = `${ev.table}::${ev.column}`;
      if (!byColumn.has(key)) byColumn.set(key, []);
      byColumn.get(key).push({
        action: ev.action,
        file: src.filePath,
        line: ev.line,
        order: src.order,
      });
    }
  }

  const churn = [];
  const warnings = [];

  for (const [key, rawEvents] of byColumn.entries()) {
    const events = [...rawEvents].sort((a, b) => a.order - b.order);
    const [table, column] = key.split('::');
    for (let i = 1; i < events.length; i += 1) {
      const prev = events[i - 1];
      const curr = events[i];
      if (prev.action === curr.action) continue;
      if (prev.action === 'ADD' && curr.action === 'DROP') {
        churn.push({ table, column, addEvent: prev, dropEvent: curr });
      } else if (prev.action === 'DROP' && curr.action === 'ADD') {
        warnings.push({ table, column, dropEvent: prev, addEvent: curr });
      }
    }
  }

  return { churn, warnings };
}

// ---------------------------------------------------------------------------
// 5. allowlist
// ---------------------------------------------------------------------------

function loadAllowlist(allowlistPath) {
  if (!existsSync(allowlistPath)) return [];
  const raw = readFileSync(allowlistPath, 'utf8');
  const data = JSON.parse(raw);
  if (!Array.isArray(data)) {
    throw new Error(`allowlist は配列である必要があります: ${allowlistPath}`);
  }
  for (const entry of data) {
    if (!entry.table || !entry.column || !entry.reason || !entry.reference) {
      throw new Error(
        `allowlist エントリに table/column/reason/reference が必要です: ${JSON.stringify(entry)}`,
      );
    }
  }
  return data;
}

function fmtEvent(ev) {
  return `${ev.file}:${ev.line}`;
}

function main() {
  const { churn, warnings } = scan(REPO_ROOT, MIGRATIONS_SCRIPT_PATH);
  const allowlist = loadAllowlist(ALLOWLIST_PATH);

  const allowlistMatched = new Set();
  const unallowedChurn = [];

  for (const c of churn) {
    const idx = allowlist.findIndex((e) => e.table === c.table && e.column === c.column);
    if (idx >= 0) {
      allowlistMatched.add(idx);
    } else {
      unallowedChurn.push(c);
    }
  }

  const staleEntries = allowlist.filter((_, idx) => !allowlistMatched.has(idx));

  console.log('\n=== migration-column-churn 検出 ===\n');

  if (churn.length === 0) {
    console.log('✅ ADD → DROP の churn は検出されませんでした');
  } else {
    console.log(`🔍 churn 候補 ${churn.length} 件:`);
    for (const c of churn) {
      const allowed = allowlist.some((e) => e.table === c.table && e.column === c.column);
      console.log(
        `  ${allowed ? '✅ allowlisted' : '❌ UNALLOWED'} ${c.table}.${c.column} : ADD ${fmtEvent(
          c.addEvent,
        )} -> DROP ${fmtEvent(c.dropEvent)}`,
      );
    }
  }

  if (warnings.length > 0) {
    console.log(`\n⚠️  drop-then-add 警告 ${warnings.length} 件（exit には影響しません）:`);
    for (const w of warnings) {
      console.log(
        `  ⚠️  ${w.table}.${w.column} : DROP ${fmtEvent(w.dropEvent)} -> ADD ${fmtEvent(w.addEvent)}`,
      );
    }
  }

  if (staleEntries.length > 0) {
    console.log(`\n❌ stale allowlist エントリ ${staleEntries.length} 件（現在の churn に該当なし）:`);
    for (const e of staleEntries) {
      console.log(`  ${e.table}.${e.column} (${e.reference})`);
    }
  }

  if (unallowedChurn.length > 0 || staleEntries.length > 0) {
    console.log('\n❌ MIGRATION COLUMN CHURN CHECK FAILED');
    if (unallowedChurn.length > 0) {
      console.log('未許可の churn があります。allowlist に追加するか、修正してください。');
    }
    if (staleEntries.length > 0) {
      console.log('allowlist に stale なエントリがあります。削除してください。');
    }
    process.exitCode = 1;
    return;
  }

  console.log('\n✅ MIGRATION COLUMN CHURN CHECK PASSED');
  process.exitCode = 0;
}

if (require.main === module) {
  main();
}

module.exports = {
  parseRegistrations,
  extractReferencedSqlFiles,
  expandSources,
  stripSqlComments,
  stripPyComments,
  extractColumnEvents,
  normalizeTable,
  splitTopLevel,
  matchAddColumn,
  matchDropColumn,
  scan,
  loadAllowlist,
};
