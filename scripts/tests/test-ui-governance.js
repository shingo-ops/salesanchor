#!/usr/bin/env node
/**
 * test-ui-governance.js
 *
 * check-ui-governance.js の検出関数を固定の見本入力で自動テストする。
 * 1 件でも失敗したら exit 1。全件合格で exit 0。
 *
 * 設計: docs/adr/ADR-144-ui-component-governance.md §9.5 D2
 * CI実行: node scripts/tests/test-ui-governance.js
 */

'use strict';

const {
  countSelect,
  countInput,
  countTab,
  countCheckbox,
  countRadio,
  countLoadingText,
  countAll,
  isValidUiAllow,
} = require('../check-ui-governance');

// ---------------------------------------------------------------------------
// テストランナー
// ---------------------------------------------------------------------------

let passed = 0;
let failed = 0;

function assert(description, actual, expected) {
  if (actual === expected) {
    console.log(`  ✅ ${description}`);
    passed++;
  } else {
    console.error(`  ❌ ${description}`);
    console.error(`     expected=${JSON.stringify(expected)}, actual=${JSON.stringify(actual)}`);
    failed++;
  }
}

// ---------------------------------------------------------------------------
// テスト本体
// ---------------------------------------------------------------------------

console.log('\n=== UI Governance Gate: 自動テスト ===\n');

// ── T1: 生 <select> 1個 → 検出 ────────────────────────────────────────────
console.log('T1: 生 <select> 検出');
assert(
  '生 <select> は検出される',
  countSelect('<select value={x} onChange={f}>'),
  1
);

// ── T2: 複数行 <input type="search">（type が別行）→ 検出 ─────────────────
// recon F-E1: type="search" の 4 件は全て複数行だった。
// この回帰テストが通れば「type が次行にあっても取りこぼさない」が保証される。
console.log('T2: 複数行 <input type="search"> 検出（F-E1 回帰テスト）');
assert(
  '複数行 type="search" は検出される',
  countInput('<input\n  type="search"\n  placeholder="..."\n/>'),
  1
);

// ── T3: <input type="checkbox"> → 非検出 ──────────────────────────────────
console.log('T3: <input type="checkbox"> 非検出');
assert(
  'type="checkbox" は検出されない',
  countInput('<input type="checkbox" checked={x} />'),
  0
);

// ── T4: className="data-table" → 非検出（/table/ 除外） ──────────────────
// recon F-E3: data-table が /tab/ に一致するが /table/ 除外ルールで誤検知防止。
console.log('T4: className="data-table" 非検出（table 除外）');
assert(
  '"data-table" は検出されない',
  countTab('<div className="data-table">'),
  0
);

// ── T5: className="my-tabs" → 検出 ────────────────────────────────────────
console.log('T5: className="my-tabs" 検出');
assert(
  '"my-tabs" は検出される',
  countTab('<div className="my-tabs">'),
  1
);

// ── T6: 有効な ui-allow（理由＋番号付き）→ 除外（非検出扱い） ────────────
// 書式: {/* ui-allow: <理由> (#<番号>) */}  ← 両方必須
console.log('T6: 有効な ui-allow 付き生select → 除外');
assert(
  '有効な ui-allow 付き生select は除外される',
  countSelect('{/* ui-allow: 移行期間のため (#123) */}\n<select value={x}>'),
  0
);

// ── T7: ui-allow（番号なし）→ 無効＝除外されない（赤のまま） ────────────
console.log('T7: 番号なし ui-allow → 無効＝除外されない');
assert(
  '番号なし ui-allow は無効で除外されない',
  countSelect('{/* ui-allow: 理由だけで番号なし */}\n<select value={x}>'),
  1
);

// ---------------------------------------------------------------------------
// 追加テスト（実装の重要ケースを補強）
// ---------------------------------------------------------------------------

console.log('\n追加テスト:');

// T8: type 省略の <input> → 検出（HTML 既定が text のため）
assert(
  'type 省略の <input> は検出される',
  countInput('<input value={x} onChange={f} />'),
  1
);

// T9: <input type="text"> 1行 → 検出
assert(
  'type="text" は検出される',
  countInput('<input type="text" value={x} />'),
  1
);

// T10: <input type="date"> → 非検出
assert(
  'type="date" は非検出',
  countInput('<input type="date" value={x} />'),
  0
);

// T11: <input type="number"> → 非検出
assert(
  'type="number" は非検出',
  countInput('<input type="number" value={x} />'),
  0
);

// T12: <input type="time"> → 非検出
assert(
  'type="time" は非検出',
  countInput('<input type="time" value={x} />'),
  0
);

// T13: 複数行 <input type="text">（type が別行）→ 検出
assert(
  '複数行 type="text" は検出される',
  countInput('<input\n  type="text"\n  value={x}\n/>'),
  1
);

// T14: className="tab-nav" → 検出
assert(
  '"tab-nav" は検出される',
  countTab('<nav className="tab-nav">'),
  1
);

// T15: className="table-container" → 非検出（table 除外）
assert(
  '"table-container" は非検出',
  countTab('<div className="table-container">'),
  0
);

// T16: テンプレートリテラル className={`db-tab...`} → 検出
assert(
  'template literal "db-tab..." は検出される',
  countTab('className={`db-tab${active ? " active" : ""}`}'),
  1
);

// T17: ui-allow が同行にある → 除外
assert(
  '同行 ui-allow は除外される（同行コメントも有効）',
  countSelect('<select value={x}> {/* ui-allow: 同行テスト (#456) */}'),
  0
);

// T18: isValidUiAllow — 書式検証
assert(
  'ui-allow: 理由 (#123) → 有効',
  isValidUiAllow('{/* ui-allow: 移行のため (#123) */}'),
  true
);
assert(
  'ui-allow: 番号なし → 無効',
  isValidUiAllow('{/* ui-allow: 理由のみ */}'),
  false
);
assert(
  'ui-allow: 理由なし → 無効',
  isValidUiAllow('{/* ui-allow:  (#123) */}'),
  false
);

// T19: <InputField> コンポーネントは誤検知しない
assert(
  '<InputField> コンポーネントは非検出',
  countInput('<InputField type="text" value={x} />'),
  0
);

// T20: <select> と <Selection> を区別する
assert(
  '<Selection> コンポーネントは非検出',
  countSelect('<Selection value={x}>'),
  0
);

// ── AY-4d: 生チェック欄 ────────────────────────────────────────────────
// T21: 基本形
assert(
  'T21: 生 type="checkbox" は1件',
  countCheckbox('<input type="checkbox" checked={x} onChange={f} />'),
  1
);

// T22: type が別行
assert(
  'T22: type が別行の生チェック欄は1件',
  countCheckbox('<input\n  type="checkbox"\n  checked={x}\n/>'),
  1
);

// T23: 波括弧付き文字列
assert(
  'T23: type={"checkbox"} と type={\'checkbox\'} は2件',
  countCheckbox('<input type={"checkbox"} />\n<input type={\'checkbox\'} />'),
  2
);

// T24: ui-allow で除外
assert(
  'T24: 有効な ui-allow 付きは除外',
  countCheckbox('{/* ui-allow: 移行のため (#123) */}\n<input type="checkbox" />'),
  0
);

// T25: 金型は数えない
assert(
  'T25: <Checkbox> と <CheckboxControl> は非検出',
  countCheckbox('<Checkbox checked={x} label="a" />\n<CheckboxControl checked={x} />'),
  0
);

// T26: radio と role=checkbox は数えない
assert(
  'T26: type="radio" と role="checkbox" は非検出',
  countCheckbox('<input type="radio" />\n<div role="checkbox" />'),
  0
);

// T27: checkbox は既存の input 種別と重ならない
assert(
  'T27: type="checkbox" は countInput に数えられない',
  countInput('<input type="checkbox" />'),
  0
);

// T28: 動的な type は数えない
assert(
  'T28: type={kind} は countCheckbox に数えられない',
  countCheckbox('<input type={kind} />'),
  0
);

// T29: 既存の動きの固定（波括弧付きは type 省略扱いで input 種別が数える）
assert(
  'T29: type={"checkbox"} は countInput で1件（既存の動きを固定）',
  countInput('<input type={"checkbox"} />'),
  1
);

// T30: 生ラジオ
assert(
  'T30: 生 type="radio" は1件',
  countRadio('<input type="radio" checked={x} onChange={f} />'),
  1
);

// T31: type が別行
assert(
  'T31: type が別行の生ラジオは1件',
  countRadio('<input\n  type="radio"\n  checked={x}\n/>'),
  1
);

// T32: 波括弧付き文字列
assert(
  'T32: type={"radio"} と type={\'radio\'} は2件',
  countRadio('<input type={"radio"} />\n<input type={\'radio\'} />'),
  2
);

// T33: ui-allow で除外
assert(
  'T33: 有効な ui-allow 付きは除外',
  countRadio('{/* ui-allow: 移行のため (#123) */}\n<input type="radio" />'),
  0
);

// T34: 金型は数えない
assert(
  'T34: <Radio> と <RadioControl> と <ChoiceCardGroup> は非検出',
  countRadio('<Radio checked={x} label="a" />\n<RadioControl checked={x} />\n<ChoiceCardGroup options={o} />'),
  0
);

// T35: checkbox と role=radio / radiogroup は数えない
assert(
  'T35: type="checkbox" と role="radio" と role="radiogroup" は非検出',
  countRadio('<input type="checkbox" />\n<div role="radio" />\n<div role="radiogroup" />'),
  0
);

// T36: radio は既存の input 種別と重ならない
assert(
  'T36: type="radio" は countInput に数えられない',
  countInput('<input type="radio" />'),
  0
);

// T37: 動的な type は数えない
assert(
  'T37: type={kind} は countRadio に数えられない',
  countRadio('<input type={kind} />'),
  0
);

// T38-T44: 読み込み中の文字だけの表示
assert('T38: <p>{t("common.loading")}</p> は1件', countLoadingText('<p>{t("common.loading")}</p>'), 1);
assert(
  'T39: 三項の中の t("schedule.loading") は1件',
  countLoadingText('{loading ? <div className="loading">{t("schedule.loading")}</div> : null}'),
  1
);
assert('T40: prop の値 label={t(...)} は0件', countLoadingText('<LoadingBlock label={t("schedule.loading")} />'), 0);
assert('T41: loadingText={t(...)} は0件', countLoadingText('<Button loadingText={t("common.loading")}>'), 0);
assert(
  'T42: 直前行に有効な ui-allow があれば0件',
  countLoadingText('// ui-allow: 理由 (#4624)\n<p>{t("common.loading")}</p>'),
  0
);
assert('T43: t("common.save") は0件', countLoadingText('{t("common.save")}'), 0);
assert('T44: countAll の戻りに loadingText がある', countAll('<p>{t("common.loading")}</p>').loadingText, 1);

// ---------------------------------------------------------------------------
// 結果サマリ
// ---------------------------------------------------------------------------

console.log(`\n=== 結果: ${passed} passed / ${failed} failed ===\n`);

if (failed > 0) {
  process.exit(1);
}
process.exit(0);
