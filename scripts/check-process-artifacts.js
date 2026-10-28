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
 *   MOCK_ADDED_FILES 新規追加ファイルの改行区切りリスト（added= A の代替）
 *   MOCK_ORIGIN_MAIN_FILES latest origin/main の改行区切りファイルリスト
 *   MOCK_PR_BODY  PR 本文テキスト（GitHub API の代替）
 *   MOCK_PR_AUTHOR PR 作者ログイン（GitHub API の代替）
 *   LOCAL_PRECHECK PR作成前の事前検査モード（'1'で有効。GO記録検査を省略し、PR番号猶予は
 *                   「猶予なし」として扱う。CI（GITHUB_ACTIONS=true）では使用不可）
 */
'use strict';

const { readFileSync, existsSync } = require('fs');
const { execSync } = require('child_process');
const { analyzeRepositoryDiff } = require('./detect-external-api-change');
const { join } = require('path');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
let cachedOriginMainPaths = null;

// ─── PR作成前の事前検査モード（scripts/dev/validate-pr-body.sh から呼ばれる） ──
const LOCAL_PRECHECK = process.env.LOCAL_PRECHECK === '1';

// ─── 認可された PR 作者（コード変更PR作成可） ────────────────────────────────
const AUTHORIZED_AUTHORS = ['shingo-cc', 'Hikky-dev'];
const TARGET_REPO = 'shingo-ops/salesanchor';
const TARGET_GH_REPO = 'github.com/shingo-ops/salesanchor';

// ─── GO権限（PO単独。ADR-1003 により例外を除き Claude Opus 設計担当へ常時委譲）──
const PO_GO_ISSUERS = ['shingo-ops', 'Shingo'];
const DELEGATED_GO_ISSUER = 'POの委任に基づくClaude Opus発行';
const AUTHORIZED_GO_ISSUERS = [...PO_GO_ISSUERS, DELEGATED_GO_ISSUER];
// 委任名義の語が入っていれば、PO の名前が混ざっていても本人扱いにしない
const DELEGATION_WORDS = /委任|opus|代理/i;

// ─── 委譲の例外パス（ADR-1003・PO本人のGOが必須） ────────────────────────────
// DANGEROUS_PATTERNS と同じ regex 方式で判定する。
const PO_ONLY_EXCEPTION_PATTERNS = [
  /^\.github\/workflows\/workflow-lint\.ya?ml$/,
];

// パスの表記ゆれ（大文字小文字・先頭の ./）をならしてから当てる
function normalizeExceptionPath(f) {
  return String(f).trim().replace(/^(\.\/)+/, '').toLowerCase();
}

function hasPoOnlyExceptionPath(files) {
  return files.some(f => {
    const p = normalizeExceptionPath(f);
    return PO_ONLY_EXCEPTION_PATTERNS.some(r => r.test(p));
  });
}

// ─── migration の表・列の削除／大量削除の検出（ADR-1003 例外判定） ───────────
// 対象の場所は deploy.yml の db_migrations と同じ範囲
const MIGRATION_PATH_PATTERNS = [
  /^migrations\//,
  /^scripts\/migrate_[^/]*\.py$/,
  /^scripts\/run_all_migrations\.sh$/,
];

function isMigrationPath(f) {
  return MIGRATION_PATH_PATTERNS.some(r => r.test(f));
}

// ── SQL の字句（PostgreSQL の決まり）──────────────────────────────────────────
const SQL_IDENT_CHAR = /[A-Za-z0-9_$\u0080-￿]/;
const SQL_DOLLAR_DELIM_SRC = String.raw`\$(?:[A-Za-z_\u0080-￿][A-Za-z0-9_\u0080-￿]*)?\$`;
const SQL_DOLLAR_DELIM_RE = new RegExp(SQL_DOLLAR_DELIM_SRC, 'y');

// 長い入力で時間がかかり過ぎないための上限（文を読み進めた字数の合計）。使い切ったら止める側（検出）に倒す
const work = { left: 0, exceeded: false };
function resetWork(len) {
  work.left = 60 * len + 2000000;
  work.exceeded = false;
}

// sql[i] が E 付き文字列の始まりの単引用符か（直前が E/e で、その前が識別子の一部でない）。
// bs（standard_conforming_strings = off）のときは、普通の文字列もバックスラッシュを逃がし記号として読む。
// lo は今読んでいる範囲の始まり（その手前の字は見ない）
function isEscapeStringQuote(sql, i, lo, bs) {
  if (sql[i] !== "'") return false;
  if (bs) return true;
  if (i - 1 < lo) return false;
  const p = sql[i - 1];
  if (p !== 'E' && p !== 'e') return false;
  return i - 2 < lo || !SQL_IDENT_CHAR.test(sql[i - 2]);
}

// sql[i] の引用符（' か "）の閉じの直後の位置。hi（範囲の終わり）までに閉じが無ければ -1
// 同じ引用符を 2 つ重ねた形は中身。E 付き文字列ではバックスラッシュが次の 1 文字を中身にする
function findQuoteEnd(sql, i, bs, lo, hi) {
  const q = sql[i];
  const esc = isEscapeStringQuote(sql, i, lo, bs);
  let j = i + 1;
  while (j < hi) {
    const c = sql[j];
    if (esc && c === '\\') { j += 2; continue; }
    if (c === q) {
      if (j + 1 < hi && sql[j + 1] === q) { j += 2; continue; }
      return j + 1;
    }
    j++;
  }
  return -1;
}

// sql[i] がドル引用の開き（$tag$）ならその文字列を返す。直前が識別子の一部なら開きではない
function dollarDelimiterAt(sql, i, lo) {
  if (sql[i] !== '$') return null;
  if (i > lo && SQL_IDENT_CHAR.test(sql[i - 1])) return null;
  SQL_DOLLAR_DELIM_RE.lastIndex = i;
  const m = SQL_DOLLAR_DELIM_RE.exec(sql);
  return m ? m[0] : null;
}

// 区切り（$tag$）が文のどこにあるかを 1 回の読みで集める（タグごとの位置の昇順）。
// タグの大文字小文字は区別する（PostgreSQL の決まり）。閉じを探すたびに先頭から読み直さないための表
function dollarIndex(text) {
  const map = new Map();
  let p = text.indexOf('$');
  while (p !== -1) {
    SQL_DOLLAR_DELIM_RE.lastIndex = p;
    const m = SQL_DOLLAR_DELIM_RE.exec(text);
    if (m) {
      const list = map.get(m[0]);
      if (list) list.push(p); else map.set(m[0], [p]);
    }
    p = text.indexOf('$', p + 1);
  }
  return map;
}

// from 以降で最初の delim の位置。区切り全体が limit までに収まらなければ -1
function nextDollar(index, delim, from, limit) {
  const list = index.get(delim);
  if (!list) return -1;
  let lo = 0;
  let hi = list.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (list[mid] < from) lo = mid + 1; else hi = mid;
  }
  return lo < list.length && list[lo] + delim.length <= limit ? list[lo] : -1;
}

// ブロックコメントの始まりの位置 → 入れ子を数えて閉じる位置の直後。1 回の読みで全部求める（閉じの無い始まりは載らない）
function blockCommentMap(text) {
  const map = new Map();
  const stack = [];
  let p = 0;
  let o = text.indexOf('/*');
  let c = text.indexOf('*/');
  for (;;) {
    if (o !== -1 && o < p) o = text.indexOf('/*', p);
    if (c !== -1 && c < p) c = text.indexOf('*/', p);
    if (o === -1 && c === -1) break;
    if (c === -1 || (o !== -1 && o < c)) {
      stack.push(o);
      p = o + 2;
    } else {
      if (stack.length > 0) {
        map.set(stack.pop(), c + 2);
        p = c + 2;
      } else {
        // 開きが積まれていないときの */ は閉じとして扱わず 1 字だけ進める（直後の /* もコメントの開き）
        p = c + 1;
      }
    }
  }
  return map;
}

// SQL のコメントを除く。引用符・E 付き文字列・ドル引用の中の -- や /* はコメントの始まりと見なさない。
// ドル引用の中身は実行される文として、その範囲だけで同じ読み方で読み直す（入れ子は繰り返しで読む）。
// ブロックコメントは入れ子を数える。閉じの無い引用・コメントは、その範囲の残りを素の文のまま残す（止める側）
function stripSqlComments(text, bs) {
  const index = dollarIndex(text);
  let comments = null;
  const out = [];
  const frames = [];
  let lo = 0;
  let hi = text.length;
  let i = 0;
  let run = 0; // まだ書き出していない素の部分の始まり
  for (;;) {
    if (i >= hi) {
      if (frames.length === 0) break;
      // ドル引用の中身を読み終えた。閉じの区切りは素の部分として続きに含める
      if (hi > run) out.push(text.slice(run, hi));
      const f = frames.pop();
      run = hi;
      i = hi + f.delim.length;
      lo = f.lo;
      hi = f.hi;
      continue;
    }
    const c = text[i];
    if (c === "'" || c === '"') {
      const end = findQuoteEnd(text, i, bs, lo, hi);
      i = end === -1 ? hi : end;
    } else if (c === '$') {
      let delim = dollarDelimiterAt(text, i, lo);
      if (delim && i + delim.length > hi) delim = null;
      if (!delim) {
        i++;
        continue;
      }
      const close = nextDollar(index, delim, i + delim.length, hi);
      if (close === -1) {
        i += delim.length;
      } else {
        const bodyStart = i + delim.length;
        if (bodyStart > run) out.push(text.slice(run, bodyStart));
        frames.push({ delim, lo, hi });
        lo = bodyStart;
        hi = close;
        i = bodyStart;
        run = bodyStart;
      }
    } else if (c === '-' && text[i + 1] === '-') {
      let j = text.indexOf('\n', i);
      if (j === -1 || j > hi) j = hi;
      if (i > run) out.push(text.slice(run, i));
      out.push(' ');
      i = j;
      run = j;
    } else if (c === '/' && text[i + 1] === '*') {
      if (!comments) comments = blockCommentMap(text);
      const k = comments.get(i);
      if (k === undefined || k > hi) {
        i++; // 閉じが無い: 素の文のまま 1 字進めて読み続ける（後ろの行コメントの除去と引用の読みも続ける）
      } else {
        if (i > run) out.push(text.slice(run, i));
        out.push(' ');
        i = k;
        run = k;
      }
    } else {
      i++;
    }
  }
  if (hi > run) out.push(text.slice(run, hi));
  return out.join('');
}

// SQL のコメントを除き、空白と改行を 1 つにまとめる
function normalizeSqlText(text, bs) {
  return stripSqlComments(text, bs).replace(/\s+/g, ' ').trim();
}

// 文の始まり: 先頭・; ・かっこ・引用符・手続きのかたまりの始まりや分岐の句・ドル引用の区切り・
// ルール定義の DO [ALSO|INSTEAD]・実行計画の前置き・準備文の AS の直後
const SQL_STATEMENT_START = String.raw`(^|[;()]|['"]|\b(?:BEGIN|THEN|ELSE|LOOP)\b|\bDO\s+(?:(?:ALSO|INSTEAD)\s+)?|${SQL_DOLLAR_DELIM_SRC}|\bEXPLAIN\s+(?:(?:ANALYZE|ANALYSE|VERBOSE)\s+)*|\bPREPARE\s+[^\s;()]+\s*(?:\([^()]*\)\s*)?AS\b)\s*`;

// 準備文の型の指定にかっこが入れ子になる形（PREPARE p (numeric(10,2)) AS ...）
const SQL_PREPARE_NESTED_RE = /\bPREPARE\s+(?:"(?:[^"]|"")*"|[^\s;()"]+)\s*\(/gi;
const SQL_AFTER_PREPARE_RE = /\s*AS\b\s*(DELETE\s+FROM\b|TRUNCATE\b)/iy;
const PREPARE_TYPE_LIST_MAX = 4000;

// open のかっこに対応する閉じかっこの位置。; が先に来る・長すぎる・閉じが無いときは -1
function findClosingParen(sql, open) {
  let depth = 0;
  const stop = Math.min(sql.length, open + PREPARE_TYPE_LIST_MAX);
  for (let j = open; j < stop; j++) {
    const c = sql[j];
    if (c === ';') return -1;
    if (c === '(') depth++;
    else if (c === ')') {
      depth--;
      if (depth === 0) return j;
    }
  }
  return -1;
}

// ── WHERE の条件が「中身が無い」か ───────────────────────────────────────────
// 条件から、文字列・数・:: の型変換・真偽値と NULL・演算子と語・かっことカンマを取り除いて、何も残らなければ中身が無い。
// 列名・引用符つきの名前・関数・$1 などの引数・%s などの差し込み記号が 1 つでも残れば中身がある
const SQL_TYPE_SRC = String.raw`(?:double\s+precision|character\s+varying|bit\s+varying|(?:time|timestamp)(?:\s*\(\s*\d+\s*\))?\s+with(?:out)?\s+time\s+zone|[A-Za-z_][A-Za-z0-9_$.]*)(?:\s*\[\s*\d*\s*\])*`;
const COND_CAST_RE = new RegExp(String.raw`::\s*` + SQL_TYPE_SRC, 'gi');
const COND_AS_TYPE_RE = new RegExp(String.raw`\bAS\s+` + SQL_TYPE_SRC, 'gi');
const COND_WORDS_RE = /\b(?:true|false|null|unknown|and|or|not|is|in|between|symmetric|asymmetric|like|ilike|similar|to|distinct|from|any|all|some|cast|as)\b/gi;
const COND_RADIX_RE = /0[xX][0-9a-fA-F_]+|0[oO][0-7_]+|0[bB][01_]+/g;
const COND_NUMBER_RE = /\d[\d_]*(?:\.[\d_]*)?(?:[eE][+-]?\d+)?|\.\d[\d_]*(?:[eE][+-]?\d+)?/g;
const COND_PUNCT_RE = /[=<>!+\-*/%^|&~(),.\s]/g;

function conditionResidue(s) {
  return s
    .replace(COND_CAST_RE, ' ')
    .replace(COND_AS_TYPE_RE, ' ')
    .replace(COND_WORDS_RE, ' ')
    .replace(COND_RADIX_RE, ' ')
    .replace(COND_NUMBER_RE, ' ')
    .replace(COND_PUNCT_RE, '');
}

const isWs = (c) => c === 32 || (c >= 9 && c <= 13);
const isAsciiLetter = (c) => (c >= 65 && c <= 90) || (c >= 97 && c <= 122);
const isWordChar = (c) => isAsciiLetter(c) || (c >= 48 && c <= 57) || c === 95;

// 条件（文字列は目印に置き換え済み）が中身の無い条件か。
// 条件の全体を包むかっこは何重でも外す。かっこの外の OR でつながった枝のうち 1 つでも中身が無ければ、条件全体を中身が無いと扱う。
// かっこの入れ子が深くても呼び出しを重ねないよう、枝は順に取り出して読む
function isHollowCondition(cond) {
  const n = cond.length;
  const match = new Int32Array(n).fill(-1);
  const stack = [];
  for (let i = 0; i < n; i++) {
    const c = cond.charCodeAt(i);
    if (c === 40) stack.push(i);
    else if (c === 41 && stack.length > 0) match[stack.pop()] = i;
  }
  for (const o of stack) match[o] = n; // 閉じの無いかっこは最後まで
  const pending = [[0, n]];
  while (pending.length > 0) {
    let [a, b] = pending.pop();
    for (;;) {
      while (a < b && isWs(cond.charCodeAt(a))) a++;
      while (b > a && isWs(cond.charCodeAt(b - 1))) b--;
      if (a < b && cond.charCodeAt(a) === 40) {
        if (match[a] === b - 1) { a++; b--; continue; }
        if (match[a] === n && b === n) { a++; continue; }
      }
      break;
    }
    if (a >= b) return true;
    const branches = [];
    let start = a;
    let k = a;
    while (k < b) {
      const c = cond.charCodeAt(k);
      if (c === 40) {
        k = match[k] === n ? b : match[k] + 1;
        continue;
      }
      if (isAsciiLetter(c) && (k === a || !isWordChar(cond.charCodeAt(k - 1)))) {
        let e = k + 1;
        while (e < b && isWordChar(cond.charCodeAt(e))) e++;
        if (e - k === 2 && (c === 79 || c === 111) && (cond.charCodeAt(k + 1) | 32) === 114) {
          branches.push([start, k]);
          start = e;
        }
        k = e;
        continue;
      }
      k++;
    }
    if (branches.length === 0) {
      if (conditionResidue(cond.slice(a, b)) === '') return true;
      continue;
    }
    branches.push([start, b]);
    for (const br of branches) pending.push(br);
  }
  return false;
}

// ── DELETE 文の本体 ───────────────────────────────────────────────────────
const SQL_SCAN_SPECIAL = /[;()'"$]/g;

// 文字列・ドル引用の前に付く記号（E / B / X / N / U&）の長さ。文字列の一部として扱う
function stringPrefixLength(sql, i, from) {
  if (i - 1 < from) return 0;
  const p = sql[i - 1];
  if (/[EeBbXxNn]/.test(p) && (i - 2 < from || !SQL_IDENT_CHAR.test(sql[i - 2]))) return 1;
  if (p === '&' && i - 2 >= from && /[Uu]/.test(sql[i - 2]) && (i - 3 < from || !SQL_IDENT_CHAR.test(sql[i - 3]))) return 2;
  return 0;
}

// from から 1 回だけ読み進め、文の終わりまでの本体を返す。文字列は目印（' 0 '）に、引用符つきの名前は
// ' ident ' に置き換える。終わりは ; ・対応のない閉じかっこ・（引用符やドル引用の区切りの直後で始まったときは）同じ区切り
function maskStatement(sql, from, endToken, bs, index) {
  const n = sql.length;
  const parts = [];
  let depth = 0;
  let run = from;
  let i = from;
  for (;;) {
    SQL_SCAN_SPECIAL.lastIndex = i;
    const m = SQL_SCAN_SPECIAL.exec(sql);
    if (!m) { i = n; break; }
    work.left -= m.index - i + 1;
    if (work.left < 0) { work.exceeded = true; i = m.index; break; }
    i = m.index;
    const c = sql[i];
    if (endToken && sql.startsWith(endToken, i)) break;
    if (c === ';') break;
    if (c === '(') { depth++; i++; continue; }
    if (c === ')') {
      if (depth === 0) break;
      depth--;
      i++;
      continue;
    }
    if (c === "'" || c === '"') {
      const plen = c === "'" ? Math.min(stringPrefixLength(sql, i, from), i - run) : 0;
      if (i - plen > run) parts.push(sql.slice(run, i - plen));
      parts.push(c === '"' ? ' ident ' : ' 0 ');
      const end = findQuoteEnd(sql, i, bs, 0, n);
      i = end === -1 ? n : end;
      run = i;
      continue;
    }
    const delim = dollarDelimiterAt(sql, i, 0);
    if (!delim) { i++; continue; }
    if (i > run) parts.push(sql.slice(run, i));
    const close = nextDollar(index, delim, i + delim.length, n);
    if (close === -1) {
      i += delim.length;
    } else {
      parts.push(' 0 ');
      i = close + delim.length;
    }
    run = i;
  }
  if (i > run) parts.push(sql.slice(run, i));
  return parts.join('');
}

// DELETE 文を走査し、意味のある WHERE の有無を返す。条件が中身の無いものだけなら WHERE が無いのと同じ
function deleteStatementHasWhere(sql, from, endToken, bs, index) {
  const body = maskStatement(sql, from, endToken, bs, index);
  const n = body.length;
  let depth = 0;
  let whereEnd = -1;
  let returningAt = n;
  for (let i = 0; i < n; i++) {
    const c = body.charCodeAt(i);
    if (c === 40) { depth++; continue; }
    if (c === 41) { depth--; continue; }
    if (depth === 0 && isAsciiLetter(c) && (i === 0 || !isWordChar(body.charCodeAt(i - 1)))) {
      let e = i + 1;
      while (e < n && isWordChar(body.charCodeAt(e))) e++;
      const word = body.slice(i, e);
      if (whereEnd < 0 && /^where$/i.test(word)) whereEnd = e;
      else if (whereEnd >= 0 && /^returning$/i.test(word)) { returningAt = i; break; }
      i = e - 1;
    }
  }
  if (whereEnd < 0) return false;
  return !isHollowCondition(body.slice(whereEnd, returningAt));
}

// ALTER TABLE（外部表を含む）の中で、列を消す略記（COLUMN を省いた削除）があるか。制約など列以外の削除は当てない。
// 操作の区切り（, ）は引用符の外だけで見る
const ALTER_TABLE_RE = /\bALTER\s+(?:FOREIGN\s+)?TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?(?:"(?:[^"]|"")*"|[^\s;,()"])+\s*\*?/gi;

// ALTER TABLE の読みは、範囲（最初はファイル全体）を左から 1 回だけ字句の決まりで読んで行う。
// 引用符・ドル引用の外、かつ操作のかっこの深さ 0 の位置にある次の ALTER TABLE の始まりでだけ読みを止める。
// ドル引用の中身は別の範囲として、引用符の中に ALTER TABLE がある形（python の文字列など）は、外側で ALTER TABLE を読んでいる途中でも、その引用符の中身を別の範囲として読み直す（引用符の中身の入れ子は 3 段まで）。
// 閉じの無い引用・ドル引用の開きは、R6c と同じく 1 字として読み進める（失敗した探しの合計に上限を付け、超えたら検出）
function alterTableDropsColumnShorthand(sql, bs) {
  const found = [...sql.matchAll(ALTER_TABLE_RE)];
  if (found.length === 0) return false;
  const starts = found.map(m => m.index);
  const firstFrom = p => {
    let lo = 0;
    let hi = starts.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (starts[mid] < p) lo = mid + 1; else hi = mid;
    }
    return lo;
  };
  let index = null;
  const getIndex = () => index || (index = dollarIndex(sql));
  const hasDollar = sql.indexOf('$') !== -1;
  let failWork = 0;
  const failLimit = 40 * sql.length + 1000000;
  const ranges = [[0, sql.length, 0]]; // [始まり, 終わり, 引用符の中身の入れ子の段]
  while (ranges.length > 0) {
    const [lo, hi, level] = ranges.pop();
    let mi = firstFrom(lo);
    if (mi >= found.length || starts[mi] >= hi) continue;
    let cur = null; // { depth, from, actions: [開始位置, 終了位置][] }
    const finish = () => {
      cur.actions.push([cur.from, cur.to]);
      const hit = cur.actions.some(([a, b]) => /^\s*DROP\s+(?!CONSTRAINT\b)\S/i.test(sql.slice(a, b)));
      cur = null;
      return hit;
    };
    let i = lo;
    while (i < hi) {
      while (mi < found.length && starts[mi] < i) mi++;
      if (cur === null && (mi >= found.length || starts[mi] >= hi)) break;
      if (mi < found.length && starts[mi] === i && (cur === null || cur.depth === 0)) {
        if (cur !== null && finish()) return true;
        const end = Math.min(found[mi].index + found[mi][0].length, hi);
        cur = { depth: 0, from: end, to: end, actions: [] };
        mi++;
        i = end;
        continue;
      }
      const c = sql[i];
      if (bs && level > 0 && c === '\\') {
        // バックスラッシュを逃がし記号として読む読み方では、引用符の中身の \' は引用符の開きではない
        i += 2;
        if (cur) cur.to = Math.min(i, hi);
        continue;
      }
      if (c === "'" || c === '"') {
        const end = findQuoteEnd(sql, i, bs, lo, hi);
        if (end === -1) {
          // 閉じの無い引用符は、ただの 1 字として読み進める（R6c の読み方）。失敗した探しの合計に上限を付け、使い切ったら検出に倒す
          failWork += hi - i;
          if (failWork > failLimit) return true;
          if (cur) cur.to = i + 1;
          i++;
          continue;
        }
        if (level < 3 && mi < found.length && starts[mi] > i && starts[mi] < end) {
          ranges.push([i + 1, end - 1, level + 1]);
        }
        i = end;
        if (cur) cur.to = i;
        continue;
      }
      if (c === '$' && hasDollar) {
        const delim = dollarDelimiterAt(sql, i, lo);
        if (delim) {
          const close = nextDollar(getIndex(), delim, i + delim.length, hi);
          if (close !== -1) {
            if (mi < found.length && starts[mi] > i && starts[mi] < close) ranges.push([i + delim.length, close, level]);
            i = close + delim.length;
            if (cur) cur.to = i;
            continue;
          }
          // 閉じの無いドル引用の開きは、ただの 1 字として読み進める
        }
      }
      if (cur) {
        if (c === ';') { if (finish()) return true; i++; continue; }
        if (c === '(') cur.depth++;
        else if (c === ')') {
          if (cur.depth === 0) { if (finish()) return true; i++; continue; }
          cur.depth--;
        } else if (c === ',' && cur.depth === 0) {
          cur.actions.push([cur.from, i]);
          cur.from = i + 1;
        }
        cur.to = i + 1;
      }
      i++;
    }
    if (cur !== null && finish()) return true;
  }
  return false;
}

// 1 つの文章（コメントを除く前か後のどちらか）が、表・列の削除または大量削除を含むか。
// 長すぎて読み切れないときは止める側（含む）に倒す
function sqlHasDestructiveStatement(sql, bs) {
  resetWork(sql.length);
  if (/\bDROP\s+(?:TABLE|COLUMN|SCHEMA|DATABASE|OWNED|FOREIGN\s+TABLE)\b/i.test(sql)) return true;
  if (alterTableDropsColumnShorthand(sql, bs)) return true;
  let index = null;
  const getIndex = () => index || (index = dollarIndex(sql));
  const startRe = new RegExp(SQL_STATEMENT_START + '(DELETE\\s+FROM\\b|TRUNCATE\\b)', 'gi');
  for (const m of sql.matchAll(startRe)) {
    if (/^TRUNCATE/i.test(m[2])) return true;
    const prefix = m[1].trim();
    const endToken = prefix === "'" || prefix === '"' || prefix.startsWith('$') ? prefix : null;
    if (!deleteStatementHasWhere(sql, m.index + m[0].length, endToken, bs, getIndex())) return true;
    if (work.exceeded) return true;
  }
  for (const m of sql.matchAll(SQL_PREPARE_NESTED_RE)) {
    const close = findClosingParen(sql, m.index + m[0].length - 1);
    if (close === -1) continue;
    SQL_AFTER_PREPARE_RE.lastIndex = close + 1;
    const a = SQL_AFTER_PREPARE_RE.exec(sql);
    if (!a) continue;
    if (/^TRUNCATE/i.test(a[1])) return true;
    if (!deleteStatementHasWhere(sql, SQL_AFTER_PREPARE_RE.lastIndex, null, bs, getIndex())) return true;
    if (work.exceeded) return true;
  }
  return work.exceeded;
}

// シェルのヒアドキュメントの中身を取り出す（閉じの語が無ければ最後まで）。
// 終わりの語は引用符つき・バックスラッシュ始まりも認める。psql 命令の行（バックスラッシュで始まる行）は文の区切りとして ; に置き換える
function heredocBodies(text) {
  const bodies = [];
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const m = /<<-?\s*(?:(["'])([A-Za-z_][A-Za-z0-9_]*)\1|\\?([A-Za-z_][A-Za-z0-9_]*))/.exec(lines[i]);
    if (!m) continue;
    const word = m[2] || m[3];
    const body = [];
    let j = i + 1;
    while (j < lines.length && lines[j].trim() !== word) {
      body.push(/^\s*\\/.test(lines[j]) ? ';' : lines[j]);
      j++;
    }
    bodies.push(body.join('\n'));
    i = j;
  }
  return bodies;
}

// 引用符を見分けずにコメントを除く（R6a と同じ切り方）。閉じの無い /* は、そこから後ろを残す
function stripCommentsLegacy(body) {
  let out = '';
  let from = 0;
  for (;;) {
    const open = body.indexOf('/*', from);
    if (open === -1) break;
    const close = body.indexOf('*/', open + 2);
    if (close === -1) break;
    out += body.slice(from, open) + ' ';
    from = close + 2;
  }
  return (out + body.slice(from)).replace(/--[^\n]*/g, ' ').replace(/\s+/g, ' ').trim();
}

// standard_conforming_strings を off にしている書き方（そのファイルでは普通の文字列もバックスラッシュが逃がし記号になる）
const SCS_OFF_RE = /standard_conforming_strings['"\s,=]*(?:to\s+)?['"]?(?:off|false|no|f|n|0)\b/i;

// 追加された文章が、表・列の削除または大量削除を含むか。
// .sql は PostgreSQL の字句の決まりでコメントを除いてから当てる。
// .sql 以外は、素の文と、引用符を見分けずにコメントを除いた文（R6a と同じ切り方）の両方に当て、
// どちらかで当たれば検出する。python の文字列の改行の記号（\n など）を実際の改行・空白に直した文と、ヒアドキュメントの中身にも同じ当て方をする。
// standard_conforming_strings を off にしているときは、バックスラッシュを逃がし記号として読む読み方でも当て、どちらかで当たれば検出する
function sqlTextHasDestructiveStatementNew(text, file) {
  const modes = SCS_OFF_RE.test(text) ? [false, true] : [false];
  if (/\.sql$/i.test(file || '')) {
    return modes.some(bs => sqlHasDestructiveStatement(normalizeSqlText(text, bs), bs));
  }
  const candidates = [
    text,
    text.replace(/\\([nrt])/g, (_, c) => (c === 't' ? ' ' : '\n')),
    ...heredocBodies(text),
  ];
  return candidates.some(body => {
    const plain = body.replace(/\s+/g, ' ').trim();
    const legacyStripped = stripCommentsLegacy(body);
    return modes.some(bs => sqlHasDestructiveStatement(plain, bs) || sqlHasDestructiveStatement(legacyStripped, bs));
  });
}

// ── 下限の見分け（R6c の見分けを中身を変えずに残したもの）──────────────────────
// 新しい見分けが R6c より弱くなる形を、形ごとの直しではなく作りで防ぐ。最終の判定は
// 「新しい見分けで当たる、または下限の見分けで当たる」。
// 関数名と定数名は lb（lower bound）を付けて新しい見分けと分けてある。読みの中身は origin/main（R6c）と同じ。
// 足したのは、繰り返しの回数を数える仕掛け（lbTick）だけ。上限に届いたとき、深い入れ子などで例外が出たときは、検出に倒す（止める側）
const LB_IDENT_CHAR = /[A-Za-z0-9_$\u0080-￿]/;
const LB_DOLLAR_DELIM_SRC = String.raw`\$(?:[A-Za-z_\u0080-￿][A-Za-z0-9_\u0080-￿]*)?\$`;
const LB_DOLLAR_DELIM_RE = new RegExp(LB_DOLLAR_DELIM_SRC, 'y');
const LB_STATEMENT_START = String.raw`(^|[;()]|['"]|\b(?:BEGIN|THEN|ELSE|LOOP)\b|${LB_DOLLAR_DELIM_SRC}|\bEXPLAIN\s+(?:(?:ANALYZE|ANALYSE|VERBOSE)\s+)*|\bPREPARE\s+[^\s;()]+\s*(?:\([^()]*\)\s*)?AS\b)\s*`;
const LB_ALTER_TABLE_RE = /\bALTER\s+(?:FOREIGN\s+)?TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?(?:"(?:[^"]|"")*"|[^\s;,()"])+\s*\*?/gi;

// 繰り返しの回数の上限（入力の長さ×100＋6000 万。1 回の呼び出し全体で数える。6000 万は約 1 秒分）。届いたら lbTick が例外を投げ、呼び出し側が検出に倒す
const lbWork = { used: 0, limit: 0 };
const LB_STATS = { limitHits: 0, errors: 0 };
const LB_LIMIT_ERROR = { lbLimit: true };
function lbBegin(len) {
  lbWork.used = 0;
  lbWork.limit = 100 * len + 60000000;
}
function lbTick(n) {
  lbWork.used += n;
  if (lbWork.used > lbWork.limit) throw LB_LIMIT_ERROR;
}

function lbIsEscapeStringQuote(sql, i) {
  if (sql[i] !== "'") return false;
  const p = sql[i - 1];
  if (p !== 'E' && p !== 'e') return false;
  const pp = sql[i - 2];
  return pp === undefined || !LB_IDENT_CHAR.test(pp);
}

function lbFindQuoteEnd(sql, i) {
  const q = sql[i];
  const esc = lbIsEscapeStringQuote(sql, i);
  let j = i + 1;
  while (j < sql.length) {
    const c = sql[j];
    if (esc && c === '\\') { j += 2; continue; }
    if (c === q) {
      if (sql[j + 1] === q) { j += 2; continue; }
      lbTick(j - i);
      return j + 1;
    }
    j++;
  }
  lbTick(j - i);
  return -1;
}

function lbDollarDelimiterAt(sql, i) {
  if (sql[i] !== '$') return null;
  if (i > 0 && LB_IDENT_CHAR.test(sql[i - 1])) return null;
  LB_DOLLAR_DELIM_RE.lastIndex = i;
  const m = LB_DOLLAR_DELIM_RE.exec(sql);
  return m ? m[0] : null;
}

function lbStripSqlComments(text) {
  let out = '';
  let i = 0;
  while (i < text.length) {
    lbTick(1);
    const c = text[i];
    if (c === "'" || c === '"') {
      const end = lbFindQuoteEnd(text, i);
      const stop = end === -1 ? text.length : end;
      out += text.slice(i, stop);
      i = stop;
    } else if (c === '$') {
      const delim = lbDollarDelimiterAt(text, i);
      if (!delim) {
        out += c;
        i++;
        continue;
      }
      const close = text.indexOf(delim, i + delim.length);
      lbTick((close === -1 ? text.length : close) - i);
      if (close === -1) {
        out += delim;
        i += delim.length;
      } else {
        out += delim + lbStripSqlComments(text.slice(i + delim.length, close)) + delim;
        i = close + delim.length;
      }
    } else if (c === '-' && text[i + 1] === '-') {
      const j = text.indexOf('\n', i);
      lbTick((j === -1 ? text.length : j) - i);
      out += ' ';
      i = j === -1 ? text.length : j;
    } else if (c === '/' && text[i + 1] === '*') {
      let depth = 1;
      let k = i + 2;
      while (k < text.length && depth > 0) {
        if (text[k] === '/' && text[k + 1] === '*') { depth++; k += 2; }
        else if (text[k] === '*' && text[k + 1] === '/') { depth--; k += 2; }
        else k++;
      }
      lbTick(k - i);
      if (depth > 0) {
        out += c;
        i++;
      } else {
        out += ' ';
        i = k;
      }
    } else {
      out += c;
      i++;
    }
  }
  return out;
}

function lbNormalizeSqlText(text) {
  return lbStripSqlComments(text).replace(/\s+/g, ' ').trim();
}

function lbIsConstantCondition(cond) {
  return cond
    .replace(/\b(?:true|false|null|unknown|and|or|not|is)\b/gi, ' ')
    .replace(/\b\d+(?:\.\d+)?\b/g, ' ')
    .replace(/[=<>!+\-*/%^|&~\s]/g, '') === '';
}

function lbScanOutsideParens(sql, from, endToken, groups) {
  let depth = 0;
  let outside = '';
  let groupStart = -1;
  let i = from;
  while (i < sql.length) {
    lbTick(1);
    const c = sql[i];
    if (c === ';') break;
    if (endToken && sql.startsWith(endToken, i)) break;
    if (c === '(') {
      if (depth === 0) {
        outside += ' (grp' + groups.length + ') ';
        groupStart = i + 1;
      }
      depth++;
      i++;
      continue;
    }
    if (c === ')') {
      if (depth === 0) break;
      depth--;
      if (depth === 0) groups.push(sql.slice(groupStart, i));
      i++;
      continue;
    }
    if (c === "'" || c === '"') {
      const end = lbFindQuoteEnd(sql, i);
      if (depth === 0) outside += c === '"' ? ' ident ' : ' 0 ';
      i = end === -1 ? sql.length : end;
      continue;
    }
    if (c === '$') {
      const delim = lbDollarDelimiterAt(sql, i);
      if (delim) {
        const close = sql.indexOf(delim, i + delim.length);
        lbTick((close === -1 ? sql.length : close) - i);
        if (close === -1) {
          i += delim.length;
        } else {
          if (depth === 0) outside += ' 0 ';
          i = close + delim.length;
        }
        continue;
      }
    }
    if (depth === 0) outside += c;
    i++;
  }
  if (depth > 0) groups.push(sql.slice(groupStart));
  return outside;
}

function lbDeleteStatementHasWhere(sql, from, endToken) {
  let groups = [];
  const outside = lbScanOutsideParens(sql, from, endToken, groups);
  const m = /\bWHERE\b/i.exec(outside);
  if (!m) return false;
  let cond = outside.slice(m.index + m[0].length).split(/\bRETURNING\b/i)[0];
  for (;;) {
    lbTick(1);
    const w = /^\s*\(grp(\d+)\)\s*$/.exec(cond);
    if (!w) break;
    const inner = groups[Number(w[1])];
    groups = [];
    cond = lbScanOutsideParens(inner, 0, null, groups);
  }
  return !lbIsConstantCondition(cond);
}

function lbAlterTableDropsColumnShorthand(sql) {
  for (const m of sql.matchAll(LB_ALTER_TABLE_RE)) {
    let depth = 0;
    let action = '';
    const actions = [];
    let i = m.index + m[0].length;
    while (i < sql.length) {
      lbTick(1);
      const c = sql[i];
      if (c === ';') break;
      if (c === "'" || c === '"') {
        const end = lbFindQuoteEnd(sql, i);
        const stop = end === -1 ? sql.length : end;
        action += sql.slice(i, stop);
        i = stop;
        continue;
      }
      if (c === '(') depth++;
      if (c === ')') {
        if (depth === 0) break;
        depth--;
      }
      if (c === ',' && depth === 0) {
        actions.push(action);
        action = '';
        i++;
        continue;
      }
      action += c;
      i++;
    }
    actions.push(action);
    if (actions.some(a => /^\s*DROP\s+(?!CONSTRAINT\b)\S/i.test(a))) return true;
  }
  return false;
}

function lbSqlHasDestructiveStatement(sql) {
  if (/\bDROP\s+(?:TABLE|COLUMN|SCHEMA|DATABASE|OWNED|FOREIGN\s+TABLE)\b/i.test(sql)) return true;
  if (lbAlterTableDropsColumnShorthand(sql)) return true;
  const startRe = new RegExp(LB_STATEMENT_START + '(DELETE\\s+FROM\\b|TRUNCATE\\b)', 'gi');
  for (const m of sql.matchAll(startRe)) {
    lbTick(1);
    if (/^TRUNCATE/i.test(m[2])) return true;
    const prefix = m[1].trim();
    const endToken = prefix === "'" || prefix === '"' || prefix.startsWith('$') ? prefix : null;
    if (!lbDeleteStatementHasWhere(sql, m.index + m[0].length, endToken)) return true;
  }
  return false;
}

function lbHeredocBodies(text) {
  const bodies = [];
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const m = /<<-?\s*(["']?)([A-Za-z_][A-Za-z0-9_]*)\1/.exec(lines[i]);
    if (!m) continue;
    const body = [];
    let j = i + 1;
    while (j < lines.length && lines[j].trim() !== m[2]) {
      body.push(lines[j]);
      j++;
    }
    bodies.push(body.join('\n'));
    i = j;
  }
  return bodies;
}

// R6c の sqlTextHasDestructiveStatement の中身。繰り返しの回数は 1 回の呼び出し全体で数える
function lbSqlTextHasDestructiveStatementCore(text, file) {
  lbBegin(text.length);
  if (/\.sql$/i.test(file || '')) {
    return lbSqlHasDestructiveStatement(lbNormalizeSqlText(text));
  }
  const candidates = [text, text.replace(/\\[nrt]/g, ' '), ...lbHeredocBodies(text)];
  return candidates.some(body => {
    const plain = body.replace(/\s+/g, ' ').trim();
    const legacyStripped = body
      .replace(/\/\*[\s\S]*?\*\//g, ' ')
      .replace(/--[^\n]*/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    return lbSqlHasDestructiveStatement(plain) || lbSqlHasDestructiveStatement(legacyStripped);
  });
}

// 下限の見分け。上限に届いたとき・例外（入れ子が深すぎる等）のときは検出に倒す
function lbSqlTextHasDestructiveStatement(text, file) {
  try {
    return lbSqlTextHasDestructiveStatementCore(text, file);
  } catch (e) {
    if (e === LB_LIMIT_ERROR) LB_STATS.limitHits++;
    else LB_STATS.errors++;
    return true;
  }
}

// 最終の判定: 新しい見分けで当たる、または下限の見分け（R6c と同じ読み）で当たる。
// 新しい見分けが R6c より弱くなる形があっても、下限の見分けが検出に戻す
function sqlTextHasDestructiveStatement(text, file) {
  return sqlTextHasDestructiveStatementNew(text, file) || lbSqlTextHasDestructiveStatement(text, file);
}

// diff をファイルごとに分け、ファイル名と、追加行だけを改行でつないだ文章にする
function addedTextByFile(diff) {
  const result = [];
  let current = null;
  for (const line of diff.split('\n')) {
    if (line.startsWith('diff --git ')) {
      const idx = line.lastIndexOf(' b/');
      current = { file: idx === -1 ? '' : line.slice(idx + 3), lines: [] };
      result.push(current);
    } else if (current && line.startsWith('+') && !line.startsWith('+++')) {
      current.lines.push(line.slice(1));
    }
  }
  return result.map(r => ({ file: r.file, text: r.lines.join('\n') }));
}

function migrationsContainDropStatement(files) {
  if (process.env.MOCK_MIGRATION_DROP_DETECTED !== undefined) {
    return process.env.MOCK_MIGRATION_DROP_DETECTED === 'true';
  }

  const migrationFiles = files.filter(isMigrationPath);
  if (migrationFiles.length === 0) return false;

  const base = process.env.BASE_SHA;
  const head = process.env.HEAD_SHA;
  // migration ファイルがあるのに diff を取れない場合は fail-closed（PO本人のGO必須側）に倒す
  if (!base || !head) return true;

  try {
    const diff = execSync(
      `git diff --unified=0 "${base}...${head}" -- ${migrationFiles.map(f => `"${f}"`).join(' ')}`,
      { encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 }
    );
    return addedTextByFile(diff).some(r => sqlTextHasDestructiveStatement(r.text, r.file));
  } catch {
    // git diff 自体が失敗した場合も fail-closed
    return true;
  }
}

function requiresPoOnlyGo(files) {
  return hasPoOnlyExceptionPath(files) || migrationsContainDropStatement(files);
}

// ─── 維持の仕組み欄の猶予閾値（GRACE_THRESHOLD_PR と同値） ───────────────────
const MAINTENANCE_GRACE_PR = 2600;

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

// ─── 正本ファイル（書類のみでも照合を飛ばさない・柱2 design-pillar2.md）──────
const CANONICAL_DOCS_PATTERNS = [
  /^docs\/specs\/.*\/ideal-state\.md$/,
  /^docs\/specs\/.*\/kgi\.md$/,
  /^docs\/ai-agents\/(?!lessons\.d\/).*\.md$/,
  /^(CLAUDE|AGENTS)\.md$/,
];

function hasCanonicalDoc(files) {
  return files.some(f => CANONICAL_DOCS_PATTERNS.some(r => r.test(f)));
}

const DANGEROUS_PATTERNS = [
  /^migrations\//,                       // DBマイグレーション（ADR-135）
  /^scripts\//,                          // 本番スクリプト全般（ADR-135 B-2）
  /^ops\/launchd\//,                     // 毎朝この Mac でファイルを消す LaunchAgent（disk-janitor）の入口
  /^\.github\/workflows\/deploy\.yml$/,  // デプロイワークフロー
  /^frontend\/src\/pages-layout\.css$/,  // 全ページ共通レイアウト（共有＝変更にGO必須）
  /^docs\/STANDARD-WORKFLOW\.md$/,                      // 正本（自己保護）
  /^\.github\/workflows\/process-artifacts-gate\.yml$/, // 関所ワークフロー（自己保護）
  /^\.github\/PULL_REQUEST_TEMPLATE\.md$/,              // 宣言テンプレ（自己保護）
  // ADR-1024 読み取り道の台本・compose（変更に GO 記録を要求）
  /^backend\/app\/ops\//,
  /^docker-compose\.ai-reader\.yml$/,
  /^docker-compose\.ai-reader-http\.yml$/,  // ADR-1042 クラウド読み取り窓口
  // ADR-1047 決まり台帳と、その検査の入力（変更に GO 記録を要求）
  /^docs\/specs\/rule-enforcement\/rules\.yml$/,
  /^docs\/specs\/rule-enforcement\/rule-docs\.txt$/,
  /^docs\/specs\/rule-enforcement\/required-checks\.txt$/,
  /^docs\/specs\/rule-enforcement\/prod-secrets\.txt$/,
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

const USER_IMPACT_PATTERNS = [
  /^frontend\/src\//,
  /^backend\/app\/routers\//,
  /^backend\/app\/services\//,
  /^backend\/app\/auth\//,
  /^backend\/app\/tasks\//,
  /^backend\/app\/discord_gateway\//,
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

function isUserImpactingFile(filePath) {
  return USER_IMPACT_PATTERNS.some(r => r.test(filePath));
}

function hasUserImpactingChange(files) {
  return files.some(f => isUserImpactingFile(f));
}

function getExternalApiChangeReport() {
  if (process.env.MOCK_EXTERNAL_API_CHANGE !== undefined) {
    const hasExternalChange = process.env.MOCK_EXTERNAL_API_CHANGE === 'true';
    return {
      hasExternalChange,
      detectedApis: hasExternalChange ? ['mock_external_api'] : [],
      unpreparedApis: [],
    };
  }

  const baseRef = process.env.MOCK_BASE_REF !== undefined
    ? process.env.MOCK_BASE_REF
    : process.env.BASE_SHA;
  const headRef = process.env.MOCK_HEAD_REF !== undefined
    ? process.env.MOCK_HEAD_REF
    : process.env.HEAD_SHA;

  if (!baseRef || !headRef) {
    return {
      hasExternalChange: false,
      detectedApis: [],
      unpreparedApis: [],
    };
  }

  return analyzeRepositoryDiff({ baseRef, headRef });
}

function parseLineList(envValue) {
  return envValue
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean);
}

function getAddedFiles() {
  if (process.env.MOCK_ADDED_FILES !== undefined) {
    return parseLineList(process.env.MOCK_ADDED_FILES);
  }

  const base = process.env.BASE_SHA;
  const head = process.env.HEAD_SHA;
  if (!base || !head) {
    return [];
  }

  const output = execSync(
    `git diff --name-status --diff-filter=A "${base}...${head}"`,
    { encoding: 'utf8' }
  ).trim();

  if (!output) {
    return [];
  }

  return output
    .split('\n')
    .map(line => line.split('\t').slice(1).join('\t').trim())
    .filter(Boolean);
}

function getLatestOriginMainPaths() {
  if (process.env.MOCK_ORIGIN_MAIN_FILES !== undefined) {
    return new Set(parseLineList(process.env.MOCK_ORIGIN_MAIN_FILES));
  }

  if (cachedOriginMainPaths) {
    return cachedOriginMainPaths;
  }

  execSync('git fetch origin main --quiet', { stdio: 'pipe' });
  const output = execSync('git ls-tree -r --name-only origin/main', { encoding: 'utf8' }).trim();
  const paths = output ? parseLineList(output) : [];
  cachedOriginMainPaths = new Set(paths);
  return cachedOriginMainPaths;
}

function findAddedPathsAlreadyInMain(addedFiles, originMainPaths) {
  return addedFiles.filter(filePath => originMainPaths.has(filePath));
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
  const adrs = extractTargetADRs(section);
  const reconMatch = section.match(/recon:\s*(docs\/handoff\/[^\s\n]+\.md)/);
  const designMatch = section.match(/設計:\s*([^\n（]+)/);
  const modeMatch = section.match(/モード:\s*(些細|緊急)/);
  const touchFilesMatch = section.match(/触るファイル:\s*((?:[\s\S]*?)(?=\n[^\s-*]|\n*$))/);
  const touchFiles = touchFilesMatch
    ? touchFilesMatch[1]
        .replace(/<!--[\s\S]*?-->/g, '')
        .split(/[\n,]/)
        .map(f => f.replace(/^\s*[-*]\s*/, '').replace(/[（(][^）)]*[）)]/g, '').trim())
        .filter(f => f.length > 0)
    : [];
  const deleteFilesMatch = section.match(/削除するファイル:\s*((?:[\s\S]*?)(?=\n[^\s-*]|\n*$))/);
  const deleteFiles = deleteFilesMatch
    ? deleteFilesMatch[1]
        .replace(/<!--[\s\S]*?-->/g, '')
        .split(/[\n,]/)
        .map(f => f.replace(/^\s*[-*]\s*/, '').replace(/[（(][^）)]*[）)]/g, '').trim())
        .filter(f => f.length > 0 && f !== 'なし')
    : [];
  const hasDeleteFilesDeclared = !!deleteFilesMatch;

  return {
    isExempt,
    adr: adrs.length > 0 ? adrs[0] : null,
    adrs,
    reconPath: reconMatch ? reconMatch[1].trim() : null,
    designPath: designMatch ? designMatch[1].trim() : null,
    mode: modeMatch ? modeMatch[1] : null,
    touchFiles,
    deleteFiles,
    hasDeleteFilesDeclared,
  };
}

function extractTargetADRs(section) {
  const adrs = [];
  const targetAdrRe = /対象ADR:\s*([^\n]+)/g;
  let match;

  while ((match = targetAdrRe.exec(section)) !== null) {
    const lineAdrs = match[1].match(/ADR-\d[\w-]*/g);
    if (lineAdrs) {
      adrs.push(...lineAdrs);
    }
  }

  return [...new Set(adrs)];
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

  const issuerMatch = section.match(/(?:\*\*)?GO発行者(?:\*\*)?\s*:\s*(.+)/);
  const dateMatch = section.match(/(?:\*\*)?日時(?:\*\*)?\s*:\s*(.+)/);
  const goTextMatch = section.match(/(?:\*\*)?GO原文(?:\*\*)?\s*:\s*(.+)/);
  const backupMatch = section.match(/(?:\*\*)?バックアップ確認(?:\*\*)?\s*:\s*(.+)/);

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
function validateGORecord(goRecord, prNumber, { requiresPoOnly = false } = {}) {
  if (!goRecord) {
    return [
      '❌ PR本文に「### GO記録」セクションがありません',
      '   → 危険変更はマージ前にチャットで「3行サマリ＋バックアップ確認」をPOに提示し、',
      '     「GO #<PR番号>」を受領してからPR本文の「### GO記録」セクションに転記してください',
      '   → 詳細: docs/specs/branch-operations/README.md §8',
    ];
  }

  const errors = [];

  if (!goRecord.issuer || !AUTHORIZED_GO_ISSUERS.some(a => goRecord.issuer.includes(a))) {
    errors.push(`❌ GO発行者が未記入または権限外です（「${goRecord.issuer || '未記入'}」）`);
    errors.push('   → GO権限はPO（Shingo / shingo-ops）またはADR-1003の委譲名義のみです');
  } else if (requiresPoOnly && (!PO_GO_ISSUERS.some(a => goRecord.issuer.includes(a)) || DELEGATION_WORDS.test(goRecord.issuer))) {
    errors.push(`❌ この変更はADR-1003の例外対象のためPO本人のGOが必要です（委譲名義「${goRecord.issuer}」は使用不可）`);
    errors.push('   → 表・列を消す、または大量に消す migration、または .github/workflows/workflow-lint.yml の変更は常にPO本人（Shingo / shingo-ops）のGOが必要です');
    if (PO_GO_ISSUERS.some(a => goRecord.issuer.includes(a))) {
      errors.push('   → 本人の発言を書き写した注記（転記した人・実行した人など）は「GO発行者」欄ではなく別の欄（変更3行など）に書き、GO発行者欄にはPO本人の名前だけを書いてください');
    }
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

/**
 * GO記録検査の呼び出しラッパー。LOCAL_PRECHECK では GO記録検査を省略する
 * （PR番号確定前の事前検査では GO記録がまだ書けないため。カード §2）。
 * LOCAL_PRECHECK でないときは validateGORecord をそのまま呼ぶ（挙動は変えない）。
 */
function checkGoRecord(prBody, prNumber, requiresPoOnly) {
  if (LOCAL_PRECHECK) {
    console.log('⏭ GO記録は PR 番号確定後に CI で検査します（PR 作成前の事前検査では省略）');
    return [];
  }
  const goRecord = parseGORecord(prBody);
  return validateGORecord(goRecord, prNumber, { requiresPoOnly });
}

// ─── recon.md 検証 ────────────────────────────────────────────────────────────

/**
 * 生パス文字列をリポジトリルート相対パスに正規化する。
 * './path' → 'path'、それ以外はそのまま。
 */
function normalizeCitationPath(rawPath) {
  return rawPath.startsWith('./') ? rawPath.slice(2) : rawPath;
}

const CITATION_FILE_EXTENSIONS = /\.(?:md|js|ts|tsx|py|yml|yaml|json)$/i;

function isRecognizedCitationPath(rawPath) {
  return CITATION_FILE_EXTENSIONS.test(normalizeCitationPath(rawPath));
}

/**
 * recon コンテンツから file パス引用をすべて抽出する。
 * 以下の書式を認識する:
 *   - `path/to/file.ext`, `path/to/file.ext:N`, `path/to/file.ext:N-M`
 *   - path/to/file.ext:N, path/to/file.ext:N-M  (バッククォートなし・スラッシュ必須・行番号あり)
 *   - ./path/to/file.ext:N  (相対パス、行番号あり)
 * 認識対象は .md/.js/.ts/.tsx/.py/.yml/.yaml/.json のみ。
 * 行番号の妥当性チェックは行わない（ファイル実在確認のみ）。
 */
function extractFileCitations(content) {
  const paths = new Set();

  // バッククォート付き（行番号はオプション、単数・範囲どちらも可）
  // ただし実ファイル拡張子を持つパスだけを存在チェック対象にする。
  const backtickRe = /`([^`\s]+?)(?::[\d]+(?:-[\d]+)?)?`/g;
  let m;
  while ((m = backtickRe.exec(content)) !== null) {
    const raw = m[1];
    if (/^https?:\/\//.test(raw)) continue; // URL スキップ
    if (!isRecognizedCitationPath(raw)) continue;
    paths.add(normalizeCitationPath(raw));
  }

  // バッククォートなし + スラッシュ入りパス + 行番号（スラッシュ必須で誤検知を抑制）
  // 先行する文字でパス開始を判定（空白・記号・行頭）
  // 例: `frontend/src/foo.tsx:42-50`, `./scripts/foo.js:10`
  const plainRe = /(?:^|[\s(,|[\n])((\.\/)?[a-zA-Z0-9_][\w.\-]*(?:\/[\w.\-]+)+)(?::[\d]+(?:-[\d]+)?)/gm;
  while ((m = plainRe.exec(content)) !== null) {
    const raw = m[1];
    if (/^https?:\/\//.test(raw)) continue;
    if (!isRecognizedCitationPath(raw)) continue;
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
  const adrs = normalizeAdrList(adr);

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
  for (const targetAdr of adrs) {
    if (!textHasAdrReference(designContent, targetAdr)) {
      errors.push(`  ❌ 設計docに ADR 参照（${targetAdr}）がありません（相互参照必須）`);
    }
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

// ─── 維持の仕組み欄 検証（正本§1.7・design-partner-loop maintenance-gate） ──
// 検査A: 「## 維持の仕組み」欄の存在と「守り手:」行の非空
// 検査B: 守り手パスの実在（「人手で守る」宣言時はスキップ）
function validateMaintenanceSection(designContent) {
  const errors = [];
  const headingMatch = /^##[^\n]*維持の仕組み[^\n]*$/m.exec(designContent);
  if (!headingMatch) {
    errors.push('  ❌ 設計docに「## 維持の仕組み」欄がありません（正本§1.7・空欄不可）');
    return errors;
  }
  const afterHeading = designContent.slice(headingMatch.index + headingMatch[0].length);
  const nextSectionMatch = afterHeading.match(/\n##/);
  const sectionContent = nextSectionMatch
    ? afterHeading.slice(0, nextSectionMatch.index)
    : afterHeading;
  const guardianMatch = sectionContent.match(/守り手:\s*([^\n]*)/);
  const guardianValue = guardianMatch ? guardianMatch[1].trim() : '';
  if (!guardianValue) {
    errors.push('  ❌ 「維持の仕組み」欄の「守り手:」が空欄です（関所パス、または「人手で守る」＋理由）');
    return errors;
  }
  if (/人手で守る/.test(guardianValue)) {
    return errors; // 関所なし宣言 — 理由の適切性は人のレビュー
  }
  const pathMatch = guardianValue.match(/[\w.\-]+(?:\/[\w.\-]+)+/);
  if (!pathMatch) {
    errors.push(`  ❌ 「守り手:」にファイルパスが見つかりません（「${guardianValue}」）`);
    return errors;
  }
  const guardianPath = normalizeCitationPath(pathMatch[0]);
  if (!existsSync(join(repoRoot, guardianPath))) {
    errors.push(`  ❌ 守り手ファイルが存在しません: ${guardianPath}`);
  }
  return errors;
}

function normalizeAdrList(adrOrAdrs) {
  if (!adrOrAdrs) return [];
  const list = Array.isArray(adrOrAdrs) ? adrOrAdrs : [adrOrAdrs];
  return [...new Set(list.map(a => String(a).trim()).filter(Boolean))];
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function adrFileMatchesReference(fileName, adr) {
  const stem = fileName.replace(/\.md$/i, '');
  const pattern = new RegExp(`^${escapeRegExp(adr)}(?:$|[-_.][\\w.-]*)$`, 'i');
  return pattern.test(stem);
}

function textHasAdrReference(text, adr) {
  const pattern = new RegExp(`(^|[^A-Za-z0-9])${escapeRegExp(adr)}($|[^A-Za-z0-9])`, 'i');
  return pattern.test(text);
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
        `gh issue list --label "sop-followup" --state open --json number,title --repo "${TARGET_GH_REPO}"`,
        { encoding: 'utf8' }
      ).trim()
    );
    if (existingIssues.some(i => i.title.includes(`PR #${prNumber}`))) {
      console.log(`  ℹ️  PR #${prNumber} の sop-followup issue が既にあるためスキップ`);
      return;
    }

    execSync(
      `gh issue create --title "${title}" --body '${body.replace(/'/g, "'\\''")}' --label "sop-followup" --repo "${TARGET_GH_REPO}"`,
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
function runFullCheck(declaration, { allowExempt = true } = {}) {
  const errors = [];

  if (!declaration) {
    errors.push('❌ PR本文に「### 標準ワークフロー確認」セクションがありません');
    errors.push('   → PRテンプレートの「標準ワークフロー確認」セクションに記入してください');
    printFailure(errors);
  }

  const { adr, adrs: declaredAdrs, reconPath, designPath } = declaration;
  const adrs = normalizeAdrList(declaredAdrs || adr);

  // a. ADR 参照
  if (adrs.length === 0 || adrs.every(a => a === 'ADR-____')) {
    errors.push('❌ 対象ADRが記入されていません（ADR-NNN の形式で記入）');
  } else {
    const adrGlob = join(repoRoot, 'docs/adr');
    try {
      const adrFiles = execSync(`ls "${adrGlob}" 2>/dev/null`, { encoding: 'utf8' })
        .split('\n').filter(Boolean);
      for (const targetAdr of adrs) {
        const matchedFiles = adrFiles.filter(f => adrFileMatchesReference(f, targetAdr));
        if (matchedFiles.length === 0) {
          errors.push(`❌ ADR ${targetAdr} のファイルが docs/adr/ に存在しません`);
        }
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
      const designErrors = validateDesignDoc(designContent, reconPath, adrs);
      errors.push(...designErrors);

      // 維持の仕組み欄 検査（PR番号2600以上のみ・初期は警告モード。LOCAL_PRECHECKは猶予なし扱い）
      const maintenancePrNumber = parseInt(process.env.PR_NUMBER, 10);
      if (LOCAL_PRECHECK || maintenancePrNumber >= MAINTENANCE_GRACE_PR) {
        const maintenanceErrors = validateMaintenanceSection(designContent);
        if (maintenanceErrors.length > 0) {
          if (process.env.MAINTENANCE_ENFORCE === 'fail') {
            errors.push(...maintenanceErrors);
          } else {
            console.warn('⚠️  維持の仕組み欄チェック（警告モード・将来failへ引き上げ予定）:');
            for (const e of maintenanceErrors) console.warn(e);
          }
        }
      }
    }
  }

  if (errors.length > 0) {
    printFailure(errors);
  }

  console.log('✅ process-artifacts gate PASSED');
}

// ─── メイン ──────────────────────────────────────────────────────────────────
function main() {
  if (LOCAL_PRECHECK && process.env.GITHUB_ACTIONS === 'true') {
    console.error('❌ LOCAL_PRECHECK は CI では使えません');
    process.exit(1);
  }

  const cliArgs = process.argv.slice(2);
  const validationOnly = cliArgs.includes('--validation-only');
  const unknownArgs = cliArgs.filter(arg => arg !== '--validation-only');
  if (unknownArgs.length > 0 || cliArgs.filter(arg => arg === '--validation-only').length > 1) {
    console.error(`❌ 不正な引数です: ${cliArgs.join(' ')}`);
    process.exit(1);
  }
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
    changedFiles = execSync(`git diff --name-only "${base}...${head}"`, { encoding: 'utf8' })
      .trim().split('\n').filter(Boolean);
  }

  if (changedFiles.length === 0) {
    console.log('✅ 変更ファイルなし — スキップ（pass）');
    process.exit(0);
  }

  const { hasDangerous, hasRealCode, hasDocsOnly } = classifyChanges(changedFiles);

  if (hasDocsOnly && !hasCanonicalDoc(changedFiles)) {
    console.log('✅ 書類のみの変更 — 自動スキップ（pass）');
    process.exit(0);
  }
  if (hasDocsOnly && hasCanonicalDoc(changedFiles)) {
    console.log('ℹ️ 書類のみだが正本を含む — 宣言照合へ進む（柱2）');
  }

  const addedFiles = getAddedFiles();
  if (addedFiles.length > 0) {
    const duplicateAddedFiles = findAddedPathsAlreadyInMain(addedFiles, getLatestOriginMainPaths());
    if (duplicateAddedFiles.length > 0) {
      printFailure([
        '❌ 新規作成したファイルが最新 origin/main に既に存在します',
        ...duplicateAddedFiles.map(filePath => `   - ${filePath}`),
        '   → このパスは既に main に在ります。古い土台で作業している可能性が高いので、最新 origin/main に rebase してやり直してください',
      ]);
    }
  }

  // PR 作者チェック（コード変更を含む PR のみ）
  const prNumber = process.env.PR_NUMBER;
  const repo = process.env.REPO;
  if (repo && repo !== TARGET_REPO) {
    printFailure([`❌ 対象外repoは検査できません: ${repo}`]);
  }
  let prAuthor = '';
  if (process.env.MOCK_PR_AUTHOR !== undefined) {
    prAuthor = process.env.MOCK_PR_AUTHOR;
  } else if (prNumber && repo) {
    try {
      prAuthor = execSync(
        `gh api --hostname github.com "repos/${TARGET_REPO}/pulls/${prNumber}" --jq '.user.login'`,
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
        `gh api --hostname github.com "repos/${TARGET_REPO}/pulls/${prNumber}" --jq '.body // ""'`,
        { encoding: 'utf8' }
      ).trim();
    } catch {
      console.warn('⚠️  PR本文の取得に失敗 — 空として扱います');
    }
  }

  const declaration = parseSOPDeclaration(prBody);
  const hasUserImpacting = hasUserImpactingChange(changedFiles);
  let externalApiReport = null;
  try {
    externalApiReport = getExternalApiChangeReport();
  } catch (error) {
    console.warn(`⚠️ 外部API変更検出に失敗 — 安全側で fail 扱い: ${error.message || error}`);
    externalApiReport = { hasExternalChange: true, detectedApis: ['external_api_detection_error'], unpreparedApis: [] };
  }
  const hasExternalApiImpact = externalApiReport.hasExternalChange;

  // ─── 触るファイル宣言 vs 実diff 照合（PR番号2600以上で義務化） ─────────────
  const GRACE_THRESHOLD_PR = 2600;
  const TOUCH_FILE_EXCLUDE_PATTERNS = [
    /package-lock\.json$/,
    /-snapshots\/.*\.png$/,
    /^\.claude-pipeline\/active-work\.md$/,
  ];

  if (LOCAL_PRECHECK || parseInt(prNumber, 10) >= GRACE_THRESHOLD_PR) {
    const targets = changedFiles.filter(
      f => !TOUCH_FILE_EXCLUDE_PATTERNS.some(p => p.test(f))
    );
    if (targets.length > 0) {
      const touchErrors = [];
      if (!declaration || !declaration.touchFiles || declaration.touchFiles.length === 0) {
        touchErrors.push('❌ PR本文に「触るファイル:」の宣言がありません（PR番号2600以上で必須）');
        touchErrors.push('   → 「### 標準ワークフロー確認」の「触るファイル:」にリポジトリ相対パスを記入してください');
      } else {
        const undeclared = targets.filter(f => !declaration.touchFiles.includes(f));
        if (undeclared.length > 0) {
          touchErrors.push('❌ 宣言外のファイルを変更しています:');
          undeclared.forEach(f => touchErrors.push(`   - ${f}`));
          touchErrors.push('   → 「触るファイル:」に追記するか、意図しない変更を除去してください');
        }
      }
      if (touchErrors.length > 0) {
        printFailure(touchErrors);
      }
    }
  }
  // PR番号 < 2600 はこのブロックを通らない＝スキップ（猶予）

  // ─── 削除ファイル宣言 vs 実diff 照合（PR番号2600以上で義務化） ─────────────
  if (LOCAL_PRECHECK || parseInt(prNumber, 10) >= GRACE_THRESHOLD_PR) {
    const base = process.env.BASE_SHA;
    const head = process.env.HEAD_SHA;
    if (base && head) {
      let numstatLines = [];
      try {
        numstatLines = execSync(`git diff --numstat "${base}...${head}"`, { encoding: 'utf8' })
          .trim().split('\n').filter(Boolean);
      } catch {
        console.warn('⚠️ git diff --numstat の実行に失敗 — 削除照合をスキップ');
      }
      const deletedFiles = numstatLines
        .map(line => {
          const parts = line.split('\t');
          return parts.length === 3 ? { deletions: parseInt(parts[1], 10), path: parts[2] } : null;
        })
        .filter(e => e && e.deletions > 0 && !TOUCH_FILE_EXCLUDE_PATTERNS.some(p => p.test(e.path)))
        .map(e => e.path);

      if (deletedFiles.length > 0) {
        const deleteErrors = [];
        if (!declaration || !declaration.hasDeleteFilesDeclared) {
          deleteErrors.push('❌ PR本文に「削除するファイル:」の宣言がありません（PR番号2600以上で必須）');
          deleteErrors.push('   → 「### 標準ワークフロー確認」の「削除するファイル:」にリポジトリ相対パスを記入してください');
          deleteErrors.push('   ※「削除するファイル」とは、丸ごと消したファイルだけでなく、1行でも削除・変更した行があるファイルを指します');
          deleteErrors.push('   → 行の削除・変更が無い場合は「削除するファイル: なし」と記入してください');
        } else {
          const undeclaredDeletes = deletedFiles.filter(f => !declaration.deleteFiles.includes(f));
          if (undeclaredDeletes.length > 0) {
            deleteErrors.push('❌ 宣言外のファイルから行を削除しています:');
            undeclaredDeletes.forEach(f => deleteErrors.push(`   - ${f}`));
            deleteErrors.push('   → 「削除するファイル:」に追記するか、意図しない変更を除去してください');
          }
        }
        if (deleteErrors.length > 0) {
          printFailure(deleteErrors);
        }
      }
    }
  }
  // PR番号 < 2600 はこのブロックを通らない＝スキップ（猶予）

  const requiresPoOnly = requiresPoOnlyGo(changedFiles);

  // 危ない変更の処理（GO記録チェック）
  if (hasDangerous) {
    const goErrors = checkGoRecord(prBody, prNumber, requiresPoOnly);

    if (goErrors.length > 0) {
      printFailure(goErrors);
    }

    const mode = declaration ? declaration.mode : null;
    if (mode === '緊急') {
      if (validationOnly) {
        console.log(`✅ 危ない変更：GO記録確認済み（緊急）— validation-onlyのため宿題待ち起票なし`);
      } else {
        console.log(`✅ 危ない変更：GO記録確認済み（緊急）— pass＋宿題待ち起票`);
        createFollowupIssue(prNumber, repo);
      }
    } else {
      console.log(`✅ 危ない変更：GO記録確認済み — pass`);
    }
    process.exit(0);
  }

  // ユーザー影響のある変更・外部API変更は、develop へ入る前に Shingo GO が必須
  if (hasUserImpacting || hasExternalApiImpact) {
    const goErrors = checkGoRecord(prBody, prNumber, requiresPoOnly);

    if (goErrors.length > 0) {
      printFailure([
        ...goErrors,
        '   → frontend/src / backend/app/routers / backend/app/services / backend/app/auth / backend/app/tasks / backend/app/discord_gateway / 外部API変更は Shingo の GO 記録が必要です',
        '   → 先にチャットで GO を受領し、PR 本文の「### GO記録」へ転記してください',
      ]);
    }

    const label = hasExternalApiImpact && !hasUserImpacting
      ? '✅ 外部API変更：GO記録確認済み — pass'
      : '✅ ユーザー影響変更：GO記録確認済み — pass';
    console.log(label);
  } else if (requiresPoOnly) {
    // hasDangerous / hasUserImpacting のどちらにも該当しないが、
    // ADR-1003 の例外対象パス（workflow-lint.yml 等）に該当する場合はここで GO を要求する
    const goErrors = checkGoRecord(prBody, prNumber, requiresPoOnly);

    if (goErrors.length > 0) {
      printFailure(goErrors);
    }

    console.log('✅ ADR-1003例外対象（PO本人のGO必須）：GO記録確認済み — pass');
    process.exit(0);
  }

  // 実コード変更の処理
  if (!hasUserImpacting && declaration && declaration.isExempt) {
    console.log('✅ 自律クラフト免除宣言あり — pass（記録）');
    process.exit(0);
  }

  runFullCheck(declaration, { allowExempt: !hasUserImpacting });
}

// テスト用にエクスポート
module.exports = {
  classifyFile,
  classifyChanges,
  hasCanonicalDoc,
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
  validateMaintenanceSection,
  hasPoOnlyExceptionPath,
  migrationsContainDropStatement,
  sqlTextHasDestructiveStatement,
  requiresPoOnlyGo,
};

// CLI として直接実行された場合のみ main() を呼ぶ
if (require.main === module) {
  main();
}
