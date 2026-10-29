#!/usr/bin/env node
/**
 * check-ui-governance.js
 *
 * PRで追加・変更された frontend/src/pages/ 配下の .tsx ファイルに
 * 新規の「生UI部品」が増えていないかを検査する。
 *
 * 検出対象（7種）:
 *   - 生 <select>
 *   - 生 <input type="text"|"search"|type省略>  ← 複数行対応
 *   - 生 <input type="checkbox">（AY-4d）
 *   - 生 <input type="radio">（AY-5b）
 *   - 自作タブ（classNameにtabを含むがtableを含まないトークン）
 *   - 読み込み中の文字だけの表示 t("...loading...")（<LoadingBlock> を使う）
 *   - ボタン等の言葉を読み込み中の言葉に入れ替える三項（loadingTernary。
 *     金型 Button の loading={条件} を使う）。この種別だけ pages/・features/・components/ を見る
 *   - 英語の直書き（englishUiLiteral。JSX の文字・aria-label 等の属性・?? 'English text' の既定値。
 *     t("key") を使う）。loadingTernary と同じ pages/・features/・components/ を見る
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
const FEATURES_DIR = 'frontend/src/features/';
const COMPONENTS_DIR = 'frontend/src/components/';
// loadingTernary だけが見るディレクトリ（既存6種別は PAGES_DIR のみ）
const LOADING_TERNARY_DIRS = [PAGES_DIR, FEATURES_DIR, COMPONENTS_DIR];
// englishUiLiteral が見るディレクトリ（中身は LOADING_TERNARY_DIRS と同じ。意味を分けるため別名）
const ENGLISH_LITERAL_DIRS = [PAGES_DIR, FEATURES_DIR, COMPONENTS_DIR];

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
function getChangedFiles(baseSha, headSha, dirs = [PAGES_DIR]) {
  const result = spawnSync(
    'git',
    ['diff', '--name-status', '-M', baseSha, headSha, '--', ...dirs],
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

/**
 * 変更ファイルを検査の範囲ごとに振り分ける（git を呼ばない純粋な関数）。
 *   legacyFiles : 既存6種別を数えるファイル（PAGES_DIR 配下のみ。今までと同じ）
 *   loadingFiles: loadingTernary を数えるファイル（pages/・features/・components/。.test.tsx は除く）
 *   englishFiles: englishUiLiteral を数えるファイル（pages/・features/・components/。.test.tsx は除く）
 */
function splitTargets(files) {
  const legacyFiles = files.filter((f) => f.headPath.startsWith(PAGES_DIR));
  const loadingFiles = files.filter(
    (f) =>
      LOADING_TERNARY_DIRS.some((d) => f.headPath.startsWith(d)) &&
      !f.headPath.endsWith('.test.tsx')
  );
  const englishFiles = files.filter(
    (f) =>
      ENGLISH_LITERAL_DIRS.some((d) => f.headPath.startsWith(d)) &&
      !f.headPath.endsWith('.test.tsx')
  );
  return { legacyFiles, loadingFiles, englishFiles };
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
// 検出ロジック: 生 <input type="checkbox">（AY-4d）
// ---------------------------------------------------------------------------

/**
 * 抽出した <input> タグが生チェック欄かどうか判定する。
 * type="checkbox" / type='checkbox' / type={"checkbox"} / type={'checkbox'} を対象にする。
 * type={kind} のような動的な値は判定できないので数えない。
 */
function isCheckboxInput(tagStr) {
  return /\btype\s*=\s*(?:\{\s*)?["']checkbox["']/i.test(tagStr);
}

/**
 * コンテンツ内の生チェック欄の件数を返す（ui-allow 除外済み）。
 */
function countCheckbox(content) {
  const lines = content.split('\n');
  let count = 0;
  for (const { tagStr, pos } of extractInputTags(content)) {
    if (!isCheckboxInput(tagStr)) continue;
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
// 検出ロジック: 生 <input type="radio">（AY-5b）
// ---------------------------------------------------------------------------

/**
 * 抽出した <input> タグが生ラジオかどうか判定する。
 * type="radio" / type='radio' / type={"radio"} / type={'radio'} を対象にする。
 * type={kind} のような動的な値は判定できないので数えない。
 */
function isRadioInput(tagStr) {
  return /\btype\s*=\s*(?:\{\s*)?["']radio["']/i.test(tagStr);
}

/**
 * コンテンツ内の生ラジオの件数を返す（ui-allow 除外済み）。
 */
function countRadio(content) {
  const lines = content.split('\n');
  let count = 0;
  for (const { tagStr, pos } of extractInputTags(content)) {
    if (!isRadioInput(tagStr)) continue;
    const lineIdx = getLineIndex(content, pos);
    if (!hasUiAllowBefore(lines, lineIdx)) count++;
  }
  return count;
}

// ---------------------------------------------------------------------------
// 検出ロジック: 読み込み中の文字だけの表示
// ---------------------------------------------------------------------------

/**
 * コンテンツ内の t("...loading...") の件数を返す（ui-allow 除外済み）。
 * prop の値（`name={t("...")}`）は数えない。
 */
function countLoadingText(content) {
  const lines = content.split('\n');
  const re = /\bt\(\s*["'`]([A-Za-z0-9_.]*[Ll]oading[A-Za-z0-9_.]*)["'`]\s*\)/g;
  let count = 0;
  let m;
  while ((m = re.exec(content)) !== null) {
    const brace = content.lastIndexOf('{', m.index);
    if (brace !== -1) {
      const before = content.slice(0, brace).replace(/\s+$/, '');
      if (before.endsWith('=')) continue;
    }
    const lineIdx = getLineIndex(content, m.index);
    if (!hasUiAllowBefore(lines, lineIdx)) count++;
  }
  return count;
}

// ---------------------------------------------------------------------------
// 検出ロジック: ボタン等の言葉を読み込み中の言葉に入れ替える三項（loadingTernary）
// ---------------------------------------------------------------------------

// 読込キーの最後の部分に含まれていれば「読み込み中の言葉」とみなす動詞の現在進行形
const LOADING_VERBS = [
  'saving', 'submitting', 'sending', 'loading', 'processing', 'testing',
  'merging', 'confirming', 'running', 'connecting', 'disconnecting',
  'reconnecting', 'changing', 'uploading', 'downloading', 'signingIn',
  'searching', 'calculating', 'recalculating', 'exporting', 'importing',
  'issuing', 'syncing', 'deploying', 'committing', 'checking', 'adding',
  'deleting', 'updating', 'creating', 'registering', 'fetching',
  'generating', 'applying', 'resetting', 'retrying', 'verifying', 'analyzing',
];

/**
 * 辞書キー（テンプレート文字列の `${s}.saving` も可）が読込キーか判定する。
 * キーを "." で区切った最後の部分に LOADING_VERBS の語が含まれること。
 * 比較は大文字小文字を区別しない。含むとは、最後の部分の先頭にあるか、
 * 語頭が大文字（直前は小文字・数字・"}"）で、語のあとが終わりか大文字であること。
 */
function isLoadingKey(key) {
  const parts = String(key).split('.');
  const last = parts[parts.length - 1];
  const lower = last.toLowerCase();
  for (const verb of LOADING_VERBS) {
    const v = verb.toLowerCase();
    let from = 0;
    let idx;
    while ((idx = lower.indexOf(v, from)) !== -1) {
      const end = idx + v.length;
      const startOk =
        idx === 0 || (/[A-Z]/.test(last[idx]) && /[a-z0-9}]/.test(last[idx - 1]));
      const endOk = end === last.length || /[A-Z]/.test(last[end]);
      if (startOk && endOk) return true;
      from = idx + 1;
    }
  }
  return false;
}

/** テンプレート文字列の ${ ... } の中身を読み飛ばし、閉じの } の次の位置を返す（閉じなければ -1） */
function skipTemplateExpr(content, from) {
  let depth = 1;
  let i = from;
  while (i < content.length) {
    const ch = content[i];
    if (ch === '"' || ch === "'") {
      let j = i + 1;
      while (j < content.length && content[j] !== ch && content[j] !== '\n') j += content[j] === '\\' ? 2 : 1;
      if (content[j] !== ch) return -1;
      i = j + 1;
    } else if (ch === '`') {
      const end = findTemplateEnd(content, i);
      if (end === -1) return -1;
      i = end;
    } else if (ch === '/' && content[i + 1] === '*') {
      const end = content.indexOf('*/', i + 2);
      if (end === -1) return -1;
      i = end + 2;
    } else if (ch === '/' && content[i + 1] === '/') {
      const end = content.indexOf('\n', i);
      if (end === -1) return -1;
      i = end;
    } else if (ch === '{') {
      depth++;
      i++;
    } else if (ch === '}') {
      depth--;
      i++;
      if (depth === 0) return i;
    } else {
      i++;
    }
  }
  return -1;
}

/** start のバッククォートで始まるテンプレート文字列の終わり（閉じの次の位置）を返す。閉じなければ -1 */
function findTemplateEnd(content, start) {
  let i = start + 1;
  while (i < content.length) {
    const ch = content[i];
    if (ch === '\\') {
      i += 2;
    } else if (ch === '`') {
      return i + 1;
    } else if (ch === '$' && content[i + 1] === '{') {
      const end = skipTemplateExpr(content, i + 2);
      if (end === -1) return -1;
      i = end;
    } else {
      i++;
    }
  }
  return -1;
}

/** 文字列が来うる直前の記号 */
const STRING_PRECEDING_CHARS = '(,=:?[{}+-*/%!&|^~;<>';
/** 文字列が来うる直前の語 */
const STRING_PRECEDING_WORDS = new Set([
  'return', 'typeof', 'case', 'in', 'of', 'void', 'yield', 'await', 'delete', 'else', 'throw',
]);

/**
 * pos の ' または " が文字列の始まりになりうるか（JSX の地の文の ' " は false）。
 * pos より前の、空白（改行を含む）でない直前の文字で判定する。
 */
function canStartString(masked, pos) {
  const p = prevNonWs(masked, pos);
  if (p < 0) return true;
  const ch = masked[p];
  if (STRING_PRECEDING_CHARS.includes(ch)) return true;
  if (/[A-Za-z0-9_$]/.test(ch)) {
    let w = p;
    while (w > 0 && /[A-Za-z0-9_$]/.test(masked[w - 1])) w--;
    return STRING_PRECEDING_WORDS.has(masked.slice(w, p + 1));
  }
  return false;
}

/**
 * コメントと文字列を取り除いた写しを作る（長さは同じ。文字列は区切りだけ残す）。
 * 戻り値: { masked, strings: [{ start, end, value, quote }] }
 */
function maskSource(content) {
  const re = /\/\*[\s\S]*?\*\/|\/\/[^\n]*|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`/g;
  const strings = [];
  let masked = '';
  let last = 0;
  let m;
  while ((m = re.exec(content)) !== null) {
    let text = m[0];
    masked += content.slice(last, m.index);
    last = m.index;
    if (text === '`') {
      const end = findTemplateEnd(content, m.index);
      if (end === -1) {
        // 閉じないテンプレートは文字列とみなさない
        masked += '`';
        last = m.index + 1;
        continue;
      }
      text = content.slice(m.index, end);
      re.lastIndex = end;
    } else if ((text[0] === '"' || text[0] === "'") && !canStartString(masked, m.index)) {
      masked += text[0];
      last = m.index + 1;
      re.lastIndex = m.index + 1;
      continue;
    }
    const isComment = text.startsWith('/*') || text.startsWith('//');
    if (isComment) {
      masked += text.replace(/[^\n]/g, ' ');
    } else {
      const q = text[0];
      masked += q + text.slice(1, -1).replace(/[^\n]/g, '_') + q;
      strings.push({ start: m.index, end: m.index + text.length, value: text.slice(1, -1), quote: q });
    }
    last = m.index + text.length;
  }
  masked += content.slice(last);
  return { masked, strings };
}

/** pos より前の、空白を除いた直前の文字の位置（なければ -1） */
function prevNonWs(masked, pos) {
  let i = pos - 1;
  while (i >= 0 && /\s/.test(masked[i])) i--;
  return i;
}

/** pos 以降の、空白を除いた次の文字の位置（なければ -1） */
function nextNonWs(masked, pos) {
  let i = pos;
  while (i < masked.length && /\s/.test(masked[i])) i++;
  return i < masked.length ? i : -1;
}

/** masked[i] が三項演算子の ? か（?? ?. ?: は除く） */
function isTernaryQuestion(masked, i) {
  if (masked[i] !== '?') return false;
  const next = masked[i + 1];
  const prev = masked[i - 1];
  if (next === '?' || next === '.' || next === ':' || prev === '?') return false;
  return true;
}

/**
 * ":" の位置から後ろ向きに、同じ階層の三項演算子の "?" を探す。
 * 区切りの "," ";" や、閉じていない括弧に当たったら null。
 */
function findTernaryQuestionBefore(masked, colonIdx) {
  let depth = 0;
  for (let i = colonIdx - 1; i >= 0; i--) {
    const ch = masked[i];
    if (ch === ')' || ch === ']' || ch === '}') depth++;
    else if (ch === '(' || ch === '[' || ch === '{') {
      if (depth === 0) return null;
      depth--;
    } else if (depth === 0) {
      if (ch === ',' || ch === ';') return null;
      if (isTernaryQuestion(masked, i)) return i;
    }
  }
  return null;
}

/** "?" の位置が t( ... ) の引数の中にあるか（t(cond ? "a" : "b") の形） */
function isInsideTCall(masked, qIdx) {
  let depth = 0;
  for (let i = qIdx - 1; i >= 0; i--) {
    const ch = masked[i];
    if (ch === ')' || ch === ']' || ch === '}') depth++;
    else if (ch === '(' || ch === '[' || ch === '{') {
      if (depth === 0) {
        if (ch !== '(') return false;
        return /(?:^|[^A-Za-z0-9_$.])(?:(?:i18n|i18next)\.)?t\s*$/.test(masked.slice(Math.max(0, i - 20), i));
      }
      depth--;
    } else if (depth === 0 && (ch === ',' || ch === ';')) {
      return false;
    }
  }
  return false;
}

/** pos の式が prop の値（"=" の直後の "{" の中）にあるか */
function isInsidePropValue(masked, pos) {
  let paren = 0, brack = 0, brace = 0;
  for (let i = pos - 1; i >= 0; i--) {
    const ch = masked[i];
    if (ch === ')') paren++;
    else if (ch === ']') brack++;
    else if (ch === '}') brace++;
    else if (ch === '(') { if (paren > 0) paren--; }
    else if (ch === '[') { if (brack > 0) brack--; }
    else if (ch === '{') {
      if (brace > 0) { brace--; continue; }
      const p = prevNonWs(masked, i);
      return p >= 0 && masked[p] === '=';
    }
  }
  return false;
}

/**
 * コンテンツ内の「読み込み中の言葉と元の言葉を入れ替える三項」の件数を返す（ui-allow 除外済み）。
 *   (A) cond ? t("<読込キー>") : x ／ cond ? x : t("<読込キー>")
 *   (B) t(cond ? "<読込キー>" : x) ／ t(cond ? x : "<読込キー>")
 *   (C) cond ? "..." : x ／ cond ? x : "..."（"..." か "…" だけの文字列）
 * 1つの三項は1件と数える。prop の値（name={...}）は数えない。
 */
function countLoadingTernary(content) {
  const lines = content.split('\n');
  const { masked, strings } = maskSource(content);
  const seen = new Set();
  let count = 0;

  for (const s of strings) {
    const isKey = isLoadingKey(s.value);
    const isDots = s.quote !== '`' && (s.value === '...' || s.value === '…');
    if (!isKey && !isDots) continue;

    // t( "key" ) で包まれていれば、包みごと1つの単位にする
    let unitStart = s.start;
    let unitEnd = s.end;
    let kind;
    const before = masked.slice(Math.max(0, s.start - 40), s.start);
    const wrap = /(?:^|[^A-Za-z0-9_$.])((?:(?:i18n|i18next)\.)?t\(\s*)$/.exec(before);
    const after = nextNonWs(masked, s.end);
    let wrapEnd = -1;
    if (isKey && wrap && after !== -1) {
      if (masked[after] === ')') {
        wrapEnd = after + 1;
      } else if (masked[after] === ',') {
        // t("key", { n }) のように第2引数があるとき、t( に対応する ) までを1つの単位にする
        let depth = 1;
        for (let i = after + 1; i < masked.length; i++) {
          if (masked[i] === '(') depth++;
          else if (masked[i] === ')' && --depth === 0) { wrapEnd = i + 1; break; }
        }
      }
    }
    if (wrapEnd !== -1) {
      unitStart = s.start - wrap[1].length;
      unitEnd = wrapEnd;
      kind = 'A';
    } else if (isKey) {
      kind = 'B';
    } else {
      kind = 'C';
    }

    // 三項の ? を探す
    let q = null;
    const pi = prevNonWs(masked, unitStart);
    const ni = nextNonWs(masked, unitEnd);
    if (pi >= 0 && isTernaryQuestion(masked, pi)) {
      if (ni !== -1 && masked[ni] === ':' && masked[ni + 1] !== ':') q = pi;
    } else if (pi >= 0 && masked[pi] === ':' && masked[pi - 1] !== ':') {
      q = findTernaryQuestionBefore(masked, pi);
    }
    if (q === null || q === undefined) continue;
    if (kind === 'B' && !isInsideTCall(masked, q)) continue;
    if (seen.has(q)) continue;
    if (isInsidePropValue(masked, q)) continue;

    const lineIdx = getLineIndex(content, unitStart);
    const qLineIdx = getLineIndex(content, q);
    if (hasUiAllowBefore(lines, lineIdx) || hasUiAllowBefore(lines, qLineIdx)) continue;

    seen.add(q);
    count++;
  }
  return count;
}

/**
 * コンテンツ内の英語の直書きの件数を返す（ui-allow 除外済み）。英語の語は英字2文字以上。
 *   (A) aria-label・placeholder・title・alt・label 属性の文字列
 *   (B) JSX の文字（> と < の間）
 *   (C) ?? 'English text' ／ || 'English text' の英文の既定値（空白と英語の語の両方がある文字列）
 * 1つの文字列が (A) と (C) の両方に当たっても1件と数える。
 */
function countEnglishUiLiteral(content) {
  const lines = content.split('\n');
  const { masked, strings } = maskSource(content);
  const hasWord = (v) => /[A-Za-z]{2,}/.test(v);
  let count = 0;

  // (A) 属性の文字列 と (C) 英文の既定値
  for (const s of strings) {
    if (s.quote === '`') continue;
    const before = masked.slice(0, s.start);
    const isAttr = /\b(aria-label|placeholder|title|alt|label)=\{?\s*$/.test(before) && hasWord(s.value);
    const isDefault = /(\?\?|\|\|)\s*$/.test(before) && /\s/.test(s.value) && hasWord(s.value);
    if (!isAttr && !isDefault) continue;
    if (hasUiAllowBefore(lines, getLineIndex(content, s.start))) continue;
    count++;
  }

  // (B) JSX の文字
  const re = />([^<>{}]*)</g;
  let m;
  while ((m = re.exec(masked)) !== null) {
    const prev = masked[m.index - 1];
    if (prev === '=' || prev === '-') continue;
    const inner = m[1];
    if (/[();=&|?]/.test(inner)) continue;
    const next = masked[m.index + m[0].length];
    if (next === undefined || !/[/A-Za-z]/.test(next)) continue;
    if (!hasWord(inner)) continue;
    if (hasUiAllowBefore(lines, getLineIndex(content, m.index))) continue;
    count++;
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
    checkbox: countCheckbox(content),
    radio: countRadio(content),
    loadingText: countLoadingText(content),
    loadingTernary: countLoadingTernary(content),
    englishUiLiteral: countEnglishUiLiteral(content),
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

  const allFiles = getChangedFiles(BASE_SHA, HEAD_SHA, LOADING_TERNARY_DIRS);
  const { legacyFiles, loadingFiles, englishFiles } = splitTargets(allFiles);
  const legacyPaths = new Set(legacyFiles.map((f) => f.headPath));
  const loadingPaths = new Set(loadingFiles.map((f) => f.headPath));
  const englishPaths = new Set(englishFiles.map((f) => f.headPath));
  const changedFiles = allFiles.filter(
    (f) => legacyPaths.has(f.headPath) || loadingPaths.has(f.headPath) || englishPaths.has(f.headPath)
  );
  console.log(
    `[INFO] 対象ファイル数: ${changedFiles.length}（pages/ ${legacyFiles.length} 件・読み込み中の三項 ${loadingFiles.length} 件・英語の直書き ${englishFiles.length} 件）`
  );

  if (changedFiles.length === 0) {
    console.log('✅ UI governance: pages/・features/・components/ への変更なし。チェックをスキップします。');
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
      checkbox: '生<input type="checkbox">',
      radio: '生<input type="radio">',
      loadingText: '読み込み中の文字だけの表示 → <LoadingBlock> を使うこと',
      loadingTernary: 'ボタン等の言葉を読み込み中に入れ替える三項 → 金型 Button の loading={条件} を使い、言葉は元のままにすること',
      englishUiLiteral: '英語の直書き → t("key") を使い、ja.json と en.json に同じキーを足すこと（固有名詞も t() を通す。ADR-027 追記）',
    };

    for (const type of ['select', 'input', 'tab', 'checkbox', 'radio', 'loadingText', 'loadingTernary', 'englishUiLiteral']) {
      // loadingTernary・englishUiLiteral だけが features/・components/ も見る。既存6種別は pages/ のみ（今までと同じ）
      const scope = type === 'loadingTernary' ? loadingPaths : type === 'englishUiLiteral' ? englishPaths : legacyPaths;
      if (!scope.has(headPath)) continue;
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
    countCheckbox,
    isCheckboxInput,
    countRadio,
    countLoadingText,
    countLoadingTernary,
    countEnglishUiLiteral,
    isLoadingKey,
    LOADING_VERBS,
    splitTargets,
    countAll,
    isRadioInput,
    extractInputTags,
    isTabToken,
  };
}
