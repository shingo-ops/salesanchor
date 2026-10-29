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
  countLoadingTernary,
  countEnglishUiLiteral,
  LOADING_VERBS,
  splitTargets,
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

// T45-: ボタン等の言葉を読み込み中に入れ替える三項（loadingTernary）
const lt = countLoadingTernary;
assert('T45: (A) saving ? t(common.saving) : t(common.save) は1件', lt('<Button>{saving ? t("common.saving") : t("common.save")}</Button>'), 1);
assert('T46: (A) 逆順 t(common.save) : t(common.saving) は1件', lt('<Button>{saving ? t("common.save") : t("common.saving")}</Button>'), 1);
assert('T47: (B) t(saving ? "productDetail.saving" : "productDetail.save") は1件', lt('{t(saving ? "productDetail.saving" : "productDetail.save")}'), 1);
assert('T48: (B) 逆順 t(saving ? "x.save" : "x.saving") は1件', lt('{t(saving ? "x.save" : "x.saving")}'), 1);
assert('T49: (B) テンプレート文字列 `${s}.saving` は1件', lt('{t(saving ? `${s}.saving` : "common.save")}'), 1);
assert('T50: (C) fetching ? "..." : t(x.fetchNow) は1件', lt('{fetching ? "..." : t("x.fetchNow")}'), 1);
assert('T51: (C) 三点リーダー "…" も1件', lt('{fetching ? t("x.fetchNow") : "…"}'), 1);
assert('T52: camel の t("discord.discordRoleSyncing") は1件', lt('{busy ? t("discord.discordRoleSyncing") : t("discord.discordRoleSync")}'), 1);
assert('T53: lvStep7Loading（数字のあとの大文字）は1件', lt('{busy ? t("carrierIntegration.lvStep7Loading") : t("carrierIntegration.lvStep7Button")}'), 1);
assert('T54: 改行をまたぐ三項も1件', lt('{saving\n  ? t("common.saving")\n  : t("common.save")}'), 1);
assert('T55: 規則3 の結果 existing ? update : register は0件', lt('{existing ? t("common.update") : t("common.register")}'), 0);
assert('T56: prop confirmLabel={x ? t(a.disconnecting) : t(a.disconnect)} は0件', lt('<Dialog confirmLabel={x ? t("a.disconnecting") : t("a.disconnect")} />'), 0);
assert('T57: prop label={loading ? t(common.loading) : undefined} は0件', lt('<Block label={loading ? t("common.loading") : undefined} />'), 0);
assert('T58: shipping / billing は0件', lt('{shipping ? t("a.shipping") : t("a.billing")}'), 0);
assert('T59: pending ? t(a.pending) : null は0件', lt('{pending ? t("a.pending") : null}'), 0);
assert('T60: 直前行に有効な ui-allow があれば0件', lt('{/* ui-allow: 理由 (#4762) */}\n{saving ? t("common.saving") : t("common.save")}'), 0);
assert('T61: オブジェクトのキー { a: x, b: t(common.saving) } は0件', lt('const o = { a: x, b: t("common.saving") };'), 0);
assert('T62: 三項でない t(common.saving) 単独は0件', lt('<p>{t("common.saving")}</p>'), 0);
assert('T63: 2つの三項は2件', lt('{a ? t("x.saving") : t("x.save")}{b ? "..." : t("y.go")}'), 2);
assert('T64: countAll の戻りに loadingTernary がある', countAll('{saving ? t("common.saving") : t("common.save")}').loadingTernary, 1);
assert('T65: LOADING_VERBS は saving を含み shipping を含まない', LOADING_VERBS.includes('saving') && !LOADING_VERBS.includes('shipping'), true);

// T66-: 範囲の振り分け（features/ だけが変わったら loadingTernary のみ）
const fileOf = (p) => ({ headPath: p, basePath: p });
const sp1 = splitTargets([fileOf('frontend/src/features/a/B.tsx')]);
assert('T66: features/ のみの変更は既存6種別の対象0件', sp1.legacyFiles.length, 0);
assert('T67: features/ のみの変更は loadingTernary の対象1件', sp1.loadingFiles.length, 1);
const sp2 = splitTargets([fileOf('frontend/src/pages/P.tsx'), fileOf('frontend/src/components/C.tsx')]);
assert('T68: pages/ は既存6種別の対象に入る', sp2.legacyFiles.length, 1);
assert('T69: pages/ と components/ は loadingTernary の対象2件', sp2.loadingFiles.length, 2);
assert('T70: .test.tsx は loadingTernary の対象外', splitTargets([fileOf('frontend/src/components/C.test.tsx')]).loadingFiles.length, 0);
assert('T71: pages/ 外のほかの場所は対象外', splitTargets([fileOf('frontend/src/hooks/H.tsx')]).loadingFiles.length, 0);

// T72-: 取りこぼす4つの書き方（便8c）
assert('T72: (1) JSX の地の文の \' のあとの三項は1件', lt('<p>Don\'t {saving ? t("common.saving") : t("common.save")} it\'s</p>'), 1);
assert('T73: (1) \' が2つ以上ある段落の中の三項は1件', lt('<p>It\'s Bob\'s and we don\'t {saving ? t("common.saving") : t("common.save")} you\'re</p>'), 1);
assert('T74: (2) テンプレートの入れ子は1件', lt('{t(saving ? `${a ? `x` : `y`}.saving` : "common.save")}'), 1);
assert('T75: (3) t の第2引数 {saving ? t(..., { n }) : t(..)} は1件', lt('{saving ? t("common.saving", { n }) : t("common.save")}'), 1);
assert('T76: (3) 逆順 {saving ? t(save) : t(saving, { n })} は1件', lt('{saving ? t("common.save") : t("common.saving", { n })}'), 1);
assert('T77: (4) i18n.t の (A) 形は1件', lt('{saving ? i18n.t("common.saving") : i18n.t("common.save")}'), 1);
assert('T78: (4) i18n.t の (B) 形は1件', lt('{i18n.t(saving ? "common.saving" : "common.save")}'), 1);
assert('T79: 三項のない地の文 Don\'t stop. It\'s fine. は0件', lt('<p>Don\'t stop. It\'s fine.</p>'), 0);
assert('T80: 属性値 placeholder="Don\'t" は0件', lt('<input placeholder="Don\'t" />'), 0);
assert('T81: t の第2引数があっても読込キーでなければ0件', lt('{x ? t("common.save", { n }) : t("common.cancel")}'), 0);
assert('T82: prop の値の i18n.t（confirmLabel=）は0件', lt('<Dialog confirmLabel={x ? i18n.t("a.disconnecting") : i18n.t("a.disconnect")} />'), 0);
assert('T83: obj.t("common.saving") を使った三項は0件', lt('{x ? obj.t("common.saving") : obj.t("common.save")}'), 0);
assert('T84: ui-allow 付きの (3) は0件', lt('{/* ui-allow: 理由 (#4762) */}\n{saving ? t("common.saving", { n }) : t("common.save")}'), 0);

// E1-: 英語の直書き（englishUiLiteral）
const en = countEnglishUiLiteral;
assert('E1: <span>No data</span> は1件', en('<span>No data</span>'), 1);
assert('E2: aria-label="Close" は1件', en('<input aria-label="Close" />'), 1);
assert('E3: placeholder={"Search..."} は1件', en('<input placeholder={"Search..."} />'), 1);
assert('E4: {emptyState ?? \'No data\'} は1件', en("{emptyState ?? 'No data'}"), 1);
assert('E5: 番号なし ui-allow は無効で除外されず1件', en('{/* ui-allow: x */}\n<p>Send failed</p>'), 1);
assert('E6: <span>{t("common.noData")}</span> は0件', en('<span>{t("common.noData")}</span>'), 0);
assert('E7: aria-label={t(...)} は0件', en('<input aria-label={t("common.close")} />'), 0);
assert('E8: アロー関数と比較演算子は0件', en('const f = (a) => a > 0 && b < c;'), 0);
assert('E9: useState<string>("") は0件', en('useState<string>("")'), 0);
assert('E10: {variant ?? \'primary\'}（空白のない既定値）は0件', en("{variant ?? 'primary'}"), 0);
assert('E11: className="foo bar" と日本語の中身は0件', en('<div className="foo bar">中身</div>'), 0);
assert('E12: 日本語の文は0件', en('<p>送信に失敗しました</p>'), 0);
assert('E13: 有効な ui-allow の次の行は0件', en('{/* ui-allow: 固有名詞の見本 (#1) */}\n<span>No data</span>'), 0);
assert('E14: コメントの中は0件', en('// <span>No data</span>'), 0);
assert('E15: .test.tsx は englishFiles に入らない', splitTargets([fileOf('frontend/src/components/C.test.tsx')]).englishFiles.length, 0);
assert('E16: components/ の .tsx は englishFiles に入る', splitTargets([fileOf('frontend/src/components/C.tsx')]).englishFiles.length, 1);
assert('E17: countAll の戻りに englishUiLiteral がある', countAll('<span>No data</span>').englishUiLiteral, 1);
assert('E18: (A) と (C) の両方に当たる文字列は1件', en("<input placeholder={x || 'Search items'} />"), 1);

// ---------------------------------------------------------------------------
// 結果サマリ
// ---------------------------------------------------------------------------

console.log(`\n=== 結果: ${passed} passed / ${failed} failed ===\n`);

if (failed > 0) {
  process.exit(1);
}
process.exit(0);
