# design: PARITY-02 C-1+C-7+Status 正規化・注記・ステータス解決

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

`analyze_extraction_job` に以下を組み込む。
1. **C-1**: 正規化ルール適用（A-1 依存）— 各 raw フィールドの装飾記号除去・表記統一をキーワード照合前に実施
2. **C-7**: 注記生成（A-3 依存）— raw_memo に対して注記マスタを照合し note_ja を生成
3. **Status**: ステータス解決（A-4 依存）— raw_state に対してステータスマスタを適用し status/exclusion を解決

GAS の `normalizeTextField_` → `buildNoteJA_` → `resolveStatusV2_` の実行順に対応。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| 装飾記号（●◆■★等）を含む商品名・状態テキストが正規化されてキーワード照合に供される | analysis_results の pid_resolved 件数が正規化前以上になる |
| raw_memo にキーワードを含む行で note_ja が NULL でなくなる | analysis_results WHERE note_ja IS NOT NULL 件数が > 0 |
| 在庫切れワード（在庫なし/売り切れ/完売等）を含む raw_state の行で exclusion='excluded' になる | analysis_results WHERE exclusion='excluded' 件数が > 0 |
| Pre-order パターン（M/D発）を含む行で status='Pre-order' になる | analysis_results WHERE status='Pre-order' 件数が > 0 |
| 既存テスト全 PASS | pytest -x -q |
| graceful fallback: tcg_normalization_rules/tcg_note_master/tcg_status_master が存在しない場合でも analyze_extraction_job が正常完了する | テーブル不在時に session.rollback() してデフォルト動作（ルールなし/'active' 固定）になる |

---

## 設計判断

### post-processing ではなく pre-processing（メインループ内）

正規化ルールはキーワード照合エンジン（matchKeyword_）への入力を整形するもの。
メインループの各アイテム処理内で raw フィールドに適用してから解決関数に渡す。

### CONDITION と STATUS で同じ raw_state を別々に正規化

GAS: `normalizeTextField_('CONDITION', raw)` と `normalizeTextField_('STATUS', raw)` は独立して呼ばれる。
同一のルールセットでも別 field の場合は独立適用が正。
`norm_condition` と `norm_status` を別変数に持つ。

### REMOVE は literal 置換（re.sub ではなく str.replace）

REMOVE ルールの from_val は単一文字・記号（●◆■等）。
GAS 側も `replace(char, '')` を呼んでいる。正規表現として解釈するとエスケープ問題が生じる。

### REGEX_REPLACE のバックリファレンス変換

GAS 式 `$N` → Python `re.sub` 形式 `\N` に変換してから適用。
NOTE フィールドの日付正規化 NR0121-NR0127 で使用。

### graceful fallback（テーブル未存在時）

A-1/A-3/A-4 が本 PR より後にマージされる場合でも正常動作する。
各 load 関数で `except Exception as exc: session.rollback(); return {}/[]` 。
- 正規化ルールなし → 生テキストのまま照合（従来動作）
- 注記マスタなし → note_ja = NULL（従来動作）
- ステータスマスタなし → ('active', None)（従来動作）

### ENGINE_VERSION 更新

`name-first-v2-cond-r4` → `name-first-v2-cond-r4-c1c7`
C-3/C-6 PR と別ブランチのため、マージ時に `name-first-v2-cond-r4-e3a-e5-c1c7` へ統合する。

---

## 外部事例

当プロジェクト既存踏襲: GAS `SystemResolverV2.gs:197` の `normalizeTextField_` 実装を Python 移植。

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 弊害・リスク

- 正規化によって既存の pid_basis / condition_basis が変わる可能性がある
  → ON CONFLICT DO UPDATE で上書きされるため冪等。既存データを参照する処理がある場合は注意
- REGEX_REPLACE パターンが無効な正規表現だった場合: `re.error` を捕捉して WARNING ログを出して続行（データは未変換のまま）

---

## 戻し方

ENGINE_VERSION を `name-first-v2-cond-r4` に戻し、C-1/C-7/Status の関数呼び出しを削除。
対象ジョブで `analyze_extraction_job` を再実行すれば ON CONFLICT DO UPDATE で元の値に戻る。
