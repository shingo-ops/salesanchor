-- 目的: 試運転（shadow）の表2件（extraction_shadow_runs / extraction_shadow_results）を削除する。
--   画面・API・書き込み経路は PR #4218 で削除済み（本番反映 2026-10-13）。
--
-- 設計: docs/handoff/shadow-remove/design.md §4 段1b
-- PO 決定: 2026-10-13（しんごさん）
--
-- 不可逆。適用には PO 本人の GO #番号 が必要（ADR-136、ADR-1003 の例外）。
--
-- 事前確認済み事実（/Users/tanizawashingo/CC報告ファイル-keep/review-page-20261013/drop-recon-facts.md 由来）:
--   - FK: この2表を外から参照する外部キーは0件（extraction_shadow_results -> extraction_shadow_runs の
--     1本のみで、2表の内側）。
--   - llm_usage_events から extraction_shadow_runs への FK は無い（ADR-1004 決定6）。
--   - view / trigger / RLS は0件。
--
-- 作成 migration（20260928_110000_create_extraction_shadow_tables.sql）の登録は残す:
--   その migration は表以外（suppliers への列追加と extraction_prompt_config の INSERT）も含むため。
--   毎デプロイで「作成 → 本 migration で削除」となり、最終状態は表なし。
--
-- バックアップ（PO 保管・ローカル、本リポジトリにはコミットしない）:
--   適用前に2表の CSV 退避と行数の記録を行う。
--
-- 冪等: IF EXISTS を使用。CASCADE は使わない（想定外の連鎖削除を防ぐ）。
-- 順序: results が runs を参照するため results -> runs。

DROP TABLE IF EXISTS public.extraction_shadow_results;
DROP TABLE IF EXISTS public.extraction_shadow_runs;
