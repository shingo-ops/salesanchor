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

/**
 * SQL コメント（-- 行末まで、/* ブロック *\/）を空白に置換（行番号を保持）。
 * 文字列リテラル（単一引用符、'' エスケープ対応）と dollar-quote
 * （$$ ... $$ / $tag$ ... $tag$、EXECUTE format('...') や DO $$...$$ 本体を含む）の
 * 内側はコメット解釈をスキップし、内容をそのまま残す（ALTER文の検出対象として
 * スキャナーに見える状態を保つ）。コメントはリテラルの外側でのみ除去する。
 */
function stripSqlComments(text) {
  const n = text.length;
  let out = '';
  let i = 0;
  while (i < n) {
    const ch = text[i];

    // 単一引用符の文字列リテラル（'' はエスケープされた引用符として内部に留める）
    if (ch === "'") {
      let j = i + 1;
      while (j < n) {
        if (text[j] === "'") {
          if (text[j + 1] === "'") {
            j += 2;
            continue;
          }
          j += 1;
          break;
        }
        j += 1;
      }
      out += text.slice(i, j);
      i = j;
      continue;
    }

    // dollar-quote（$$ ... $$ / $tag$ ... $tag$）。DO $$...$$ 本体や
    // EXECUTE format($q$...$q$, ...) の文字列部分もここに含まれる。
    if (ch === '$') {
      const tagMatch = /^\$([A-Za-z_][A-Za-z0-9_]*)?\$/.exec(text.slice(i));
      if (tagMatch) {
        const openTag = tagMatch[0];
        const closeIdx = text.indexOf(openTag, i + openTag.length);
        if (closeIdx !== -1) {
          out += text.slice(i, closeIdx + openTag.length);
          i = closeIdx + openTag.length;
          continue;
        }
        // 閉じタグが見つからない（未終端）。安全側に倒して残り全体をそのまま残す。
        out += text.slice(i);
        break;
      }
    }

    // 行コメント（リテラル外側のみ）
    if (ch === '-' && text[i + 1] === '-') {
      let j = i;
      while (j < n && text[j] !== '\n') j += 1;
      out += ' '.repeat(j - i);
      i = j;
      continue;
    }

    // ブロックコメント（リテラル外側のみ）
    if (ch === '/' && text[i + 1] === '*') {
      let j = i + 2;
      while (j < n && !(text[j] === '*' && text[j + 1] === '/')) j += 1;
      const end = Math.min(j + 2, n);
      out += text.slice(i, end).replace(/[^\n]/g, ' ');
      i = end;
      continue;
    }

    out += ch;
    i += 1;
  }
  return out;
}

/** Python コメント（# 行末まで）を空白に置換（行番号を保持） */
function stripPyComments(text) {
  return text.replace(/#[^\n]*/g, (line) => ' '.repeat(line.length));
}

// ---------------------------------------------------------------------------
// 3. ALTER TABLE 抽出
// ---------------------------------------------------------------------------

// スキーマ部分（%I / {schema} / tenant_NNN / public）は常に非引用のリテラルトークン。
// テーブル名部分は引用識別子（"Tbl"）または非引用識別子のどちらも許容する。
const SCHEMA_ALT = '%I|\\{schema\\}|tenant_\\d+|public';
const IDENT_ALT = '"[^"]*"|[A-Za-z_][A-Za-z0-9_]*';
const TARGET_RE = `(?:(?:${SCHEMA_ALT})\\.(?:${IDENT_ALT})|(?:${IDENT_ALT}))`;

const ALTER_RE = new RegExp(
  `ALTER\\s+TABLE\\s+(?:IF\\s+EXISTS\\s+)?(?:ONLY\\s+)?(${TARGET_RE})\\s+([^;]*?)(?=;|$)`,
  'gi',
);

/**
 * 引用識別子（"Name"）は PostgreSQL の規則通り大小文字をそのまま保持し、
 * 非引用識別子は小文字に正規化する。
 * @returns {{name: string, wasQuoted: boolean}}
 */
function parseIdentifier(raw) {
  if (raw.length >= 2 && raw[0] === '"' && raw[raw.length - 1] === '"') {
    return { name: raw.slice(1, -1), wasQuoted: true };
  }
  return { name: raw.toLowerCase(), wasQuoted: false };
}

/** raw の中から、引用符の外側にある最初の '.' でスキーマ部とテーブル部に分割する */
function splitSchemaTable(raw) {
  let inQuote = false;
  for (let i = 0; i < raw.length; i += 1) {
    if (raw[i] === '"') inQuote = !inQuote;
    else if (raw[i] === '.' && !inQuote) {
      return [raw.slice(0, i), raw.slice(i + 1)];
    }
  }
  return [null, raw];
}

function normalizeTable(raw) {
  const [schemaRaw, tableRaw] = splitSchemaTable(raw);
  const table = parseIdentifier(tableRaw);
  const tableName = table.name;
  if (schemaRaw === null) {
    return `public.${tableName}`;
  }
  const schema = parseIdentifier(schemaRaw);
  if (!schema.wasQuoted && schema.name === 'public') {
    return `public.${tableName}`;
  }
  return `tenant.${tableName}`;
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
  'COLUMN',
]);
const DROP_NON_COLUMN_KEYWORDS = new Set(['CONSTRAINT', 'DEFAULT', 'NOT', 'COLUMN']);

// 列名: 引用識別子（"Col"、大小文字保持）または非引用識別子（小文字化）
const COLUMN_IDENT_CAPTURE = '(?:"([^"]*)"|([A-Za-z_][A-Za-z0-9_]*))';

/**
 * 正規表現マッチ結果から引用/非引用の識別子名を読み取る。
 * quotedIdx は引用グループの番号（非引用グループは quotedIdx+1）。
 * @returns {{name: string, wasQuoted: boolean}|null}
 */
function readIdentFromMatch(m, quotedIdx) {
  const quoted = m[quotedIdx];
  const bare = m[quotedIdx + 1];
  if (quoted !== undefined) return { name: quoted, wasQuoted: true };
  if (bare !== undefined) return { name: bare, wasQuoted: false };
  return null;
}

function finalizeIdentName(ident) {
  if (!ident) return null;
  return ident.wasQuoted ? ident.name : ident.name.toLowerCase();
}

function matchAddColumn(clause) {
  let m = clause.match(
    new RegExp(`^ADD\\s+COLUMN\\s+(?:IF\\s+NOT\\s+EXISTS\\s+)?${COLUMN_IDENT_CAPTURE}`, 'i'),
  );
  if (m) return finalizeIdentName(readIdentFromMatch(m, 1));
  m = clause.match(new RegExp(`^ADD\\s+(?:IF\\s+NOT\\s+EXISTS\\s+)?${COLUMN_IDENT_CAPTURE}`, 'i'));
  if (m) {
    const ident = readIdentFromMatch(m, 1);
    if (ident.wasQuoted) return finalizeIdentName(ident);
    if (!ADD_NON_COLUMN_KEYWORDS.has(ident.name.toUpperCase())) return finalizeIdentName(ident);
  }
  return null;
}

function matchDropColumn(clause) {
  let m = clause.match(
    new RegExp(`^DROP\\s+COLUMN\\s+(?:IF\\s+EXISTS\\s+)?${COLUMN_IDENT_CAPTURE}`, 'i'),
  );
  if (m) return finalizeIdentName(readIdentFromMatch(m, 1));
  m = clause.match(new RegExp(`^DROP\\s+(?:IF\\s+EXISTS\\s+)?${COLUMN_IDENT_CAPTURE}`, 'i'));
  if (m) {
    const ident = readIdentFromMatch(m, 1);
    if (ident.wasQuoted) return finalizeIdentName(ident);
    if (!DROP_NON_COLUMN_KEYWORDS.has(ident.name.toUpperCase())) return finalizeIdentName(ident);
  }
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
      // matchAddColumn/matchDropColumn は引用識別子の大小文字保持・非引用識別子の
      // 小文字化を既に適用済みなので、ここで再度 toLowerCase() しない
      // （引用識別子の大小文字を壊さないため）。
      const addCol = matchAddColumn(clause);
      if (addCol) {
        events.push({ table, column: addCol, action: 'ADD', line });
        continue;
      }
      const dropCol = matchDropColumn(clause);
      if (dropCol) {
        events.push({ table, column: dropCol, action: 'DROP', line });
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
