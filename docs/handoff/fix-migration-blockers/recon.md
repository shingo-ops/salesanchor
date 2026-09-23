# recon: fix-migration-blockers

## 問題
SSOT移行（tenant_004→public）後、4本のマイグレーションが部分テーブル構造検出時に RAISE EXCEPTION を発生させデプロイをブロック。

## 対象ファイル（file:line）

- migrations/20260910_200000_tcg_condition_note_delivery_t004.sql:16-18 — `IF table_count <> 2 THEN RAISE EXCEPTION`
- migrations/20260913_150000_tcg_empty_box_condition.sql:28 — `IF table_count <> 6 THEN RAISE EXCEPTION`
- migrations/20260913_200000_tcg_cardset_exclusion.sql:35-37 — `ELSIF table_count <> 4 THEN RAISE EXCEPTION`
- migrations/20260913_210000_tcg_cardset_bundle_registration.sql:37-39 — `ELSIF table_count <> 6 THEN RAISE EXCEPTION`

## 原因
SSOT移行（PR #3585等）後、tenant_004.conditions / tenant_004.tcg_note_master 等が public スキーマへ移行済み。table_count が期待値未満になるのは正常状態。

## 既存の冪等ガードパターン（同一ファイル内）
- `IF table_count = 0 THEN RETURN;` — 全テーブル不在時はスキップ（正しいパターン）
- `IF to_regclass('tenant_004.analysis_results') IS NULL THEN RAISE NOTICE ... RETURN;` — 部分不在時のスキップ例（20260913_150000 line 24-27）
- 修正はこの既存パターンに揃える
