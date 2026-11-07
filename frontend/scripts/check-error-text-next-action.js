#!/usr/bin/env node
/**
 * check-error-text-next-action.js（ADR-1071 W2・docs/handoff/error-message-plain-language/card-guard.md）
 *
 * 画面の文言（src/locales/ja.json）で、失敗の文なのに「次にすること」が無い文を増やさない見張り。
 *
 * 数え方:
 *   1. ja.json の葉の文字列を全部集める（キーは階層を . でつなぐ。配列は番号を道すじに入れる）。
 *   2. 失敗の文: 値が /失敗|エラー|できません/ に当たる。
 *   3. 次にすることがある: 値が /もう一度|お試し|連絡|確認して|ください/ に当たる。
 *   4. 違反: 失敗の文で、次にすることが無いもの。
 *   5. 例外: scripts/error-text-next-action-baseline.json の exempt にキーと空でない理由があるもの。
 * 基準: 同じファイルの keys（今の違反のキー）。
 * 赤になる時: 増えた（keys に無い違反）・減った（keys にあるのに違反でない）・例外の理由が空。
 *
 * 使い方: node scripts/check-error-text-next-action.js
 *         node scripts/check-error-text-next-action.js --write-baseline   （keys を書き出す。exempt は触らない）
 * CI: npm run check:error-text-next-action（check:all に入っている）
 */

import { readFileSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const JA_FILE = join(__dirname, '../src/locales/ja.json');
const BASELINE_FILE = join(__dirname, 'error-text-next-action-baseline.json');
const FAILURE = /失敗|エラー|できません/;
const NEXT_ACTION = /もう一度|お試し|連絡|確認して|ください/;

function flatten(node, prefix, out) {
  if (typeof node === 'string') {
    out[prefix] = node;
  } else if (Array.isArray(node)) {
    node.forEach((v, i) => flatten(v, prefix ? `${prefix}.${i}` : String(i), out));
  } else if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      flatten(v, prefix ? `${prefix}.${k}` : k, out);
    }
  }
  return out;
}

function violations(ja) {
  const flat = flatten(ja, '', {});
  const keys = Object.keys(flat).filter((k) => FAILURE.test(flat[k]) && !NEXT_ACTION.test(flat[k]));
  return { flat, keys };
}

function compare(ja, baseline) {
  const { flat, keys } = violations(ja);
  const exempt = baseline.exempt ?? {};
  const problems = [];
  for (const [k, reason] of Object.entries(exempt)) {
    if (typeof reason !== 'string' || reason.trim() === '') problems.push(`例外の理由が空: ${k}`);
  }
  const known = new Set(baseline.keys ?? []);
  const nowSet = new Set(keys);
  for (const k of keys) {
    if (typeof exempt[k] === 'string' && exempt[k].trim() !== '') continue;
    if (!known.has(k)) problems.push(`増えた: ${k}「${flat[k]}」`);
  }
  for (const k of known) {
    if (!nowSet.has(k)) {
      problems.push(`減った: ${k}（scripts/error-text-next-action-baseline.json の keys からこの行を消す）`);
    }
  }
  return { problems, count: keys.length, exemptCount: Object.keys(exempt).length };
}

function selfTest() {
  const ja = {
    a: { x: '保存に失敗しました', y: '保存に失敗しました。もう一度お試しください。', z: 'エラー' },
    b: ['読み込みに失敗しました', '読み込めませんでした。管理者に連絡してください。'],
  };
  const base = { exempt: { 'a.z': '表の見出し' }, keys: ['a.x', 'b.0'] };
  const ok = compare(ja, base).problems.length === 0;
  const added = compare({ ...ja, a: { ...ja.a, w: '送信できませんでした' } }, base).problems.length === 1;
  const fixed =
    compare({ ...ja, a: { ...ja.a, x: '保存に失敗しました。もう一度お試しください。' } }, base).problems.length === 1;
  const emptyReason = compare(ja, { exempt: { 'a.z': ' ' }, keys: ['a.x', 'b.0'] }).problems.length === 2;
  return ok && added && fixed && emptyReason;
}

function main() {
  if (!selfTest()) {
    console.error('自己点検に失敗（数え方が壊れている）');
    process.exit(1);
  }
  const ja = JSON.parse(readFileSync(JA_FILE, 'utf8'));
  if (process.argv.includes('--write-baseline')) {
    let exempt = {};
    try {
      exempt = JSON.parse(readFileSync(BASELINE_FILE, 'utf8')).exempt ?? {};
    } catch {
      exempt = {};
    }
    const keys = violations(ja).keys.filter((k) => !(k in exempt)).sort();
    writeFileSync(BASELINE_FILE, JSON.stringify({ exempt, keys }, null, 2) + '\n');
    console.log(`書き出し: keys ${keys.length} 件・exempt ${Object.keys(exempt).length} 件`);
    return;
  }
  const baseline = JSON.parse(readFileSync(BASELINE_FILE, 'utf8'));
  const { problems, count, exemptCount } = compare(ja, baseline);
  if (problems.length > 0) {
    for (const p of problems) console.error(p);
    console.error('');
    console.error('失敗の文には、何が起きたかと次にすることを書く（ADR-1071）。例: 時間切れにより連携できませんでした。もう一度お試しください。');
    console.error('次にすることの語: もう一度・お試し・連絡・確認して・ください のどれか');
    console.error('失敗の文でない見出しなどは、scripts/error-text-next-action-baseline.json の exempt にキーと理由を書く');
    process.exit(1);
  }
  console.log(`✅ error-text-next-action: 基準どおり（違反 ${count} 件・例外 ${exemptCount} 件）`);
}

main();
