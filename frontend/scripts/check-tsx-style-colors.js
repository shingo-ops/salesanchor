#!/usr/bin/env node
/**
 * .tsx/.jsx の JSX style 内 UIスタイル色直書き検査（warn版・落とさない）。
 * 目的: color/background/border 等への #hex / rgb() 直書き（var(--)でない）を警告。
 * データ色（下記 EXCLUDE のファイル）は誤爆防止のため検査対象外。
 * ブロック化は誤爆0を確認後に別便で exit(1) に切替。
 */
import { execSync } from 'child_process';
import fs from 'fs';

// ▼▼ 管理ポイント: 除外するデータ色ファイル（新しいデータ色ファイルはここに追記） ▼▼
const EXCLUDE = [
  'frontend/src/features/schedule/calendars.config.ts',
  'frontend/src/pages/schedule/schedule-owner.ts',
  'frontend/src/contexts/UiPrefsContext.tsx',
];
// ▲▲ 管理ポイントここまで ▲▲

// スタイルプロパティへの色直書き（var(--)でない #hex / rgb）
const STYLE_COLOR =
  /(color|backgroundColor|background|borderColor|border|boxShadow|fill|stroke)\s*:\s*['"`](#[0-9a-fA-F]{3,6}|rgba?\()/;

let files = [];
try {
  files = execSync("find frontend/src -type f \\( -name '*.tsx' -o -name '*.jsx' \\) -print", { encoding: 'utf8' })
    .split('\n')
    .filter(Boolean)
    .filter((f) => !EXCLUDE.includes(f));
} catch (e) {
  console.log('check-tsx-style-colors: ファイル列挙に失敗（警告のみ）');
  process.exit(0);
}

let hits = [];
for (const f of files) {
  let lines;
  try {
    lines = fs.readFileSync(f, 'utf8').split('\n');
  } catch {
    continue;
  }
  lines.forEach((ln, i) => {
    if (ln.includes('var(--')) return;
    if (STYLE_COLOR.test(ln)) hits.push(`${f}:${i + 1}: ${ln.trim()}`);
  });
}

if (hits.length) {
  console.log(`⚠️  [warn] .tsx UIスタイル色の直書きを ${hits.length} 件検出（トークン var(--*) 推奨）:`);
  hits.forEach((h) => console.log('  ' + h));
} else {
  console.log('✅ .tsx UIスタイル色の直書きなし（データ色除外後）');
}
process.exit(0); // warn版: 常に成功
