-- ============================================================================
-- Migration 20260604_010000: 商品マスタの型番(mark)を「商品マスタ」シート B列(Mark)で更新。
--
-- 公式シートの (日本語タイトル -> Mark) 125 件で public.products.mark を更新する。
-- 一致キー: public.products.name = 日本語タイトル（中央カタログ tenant_id IS NULL）。
-- 既存 Dragon Ball seed (name='ブースターパック …', mark=FBxx) とは name が異なるため非干渉。
--
-- 冪等: 何度実行しても同じ結果（UPDATE）。列追加・破壊なし。
-- ガード: migration-test baseline には public.products.mark 列が無い場合があるので skip。
-- ============================================================================
--
-- NEUTRALIZED (ADR-155, 2026-10-05):
-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- 元の内容は git history で参照可能。
-- 再実行（毎デプロイ）のたびに products.mark を上書きし、アプリで直した値
-- （例: MEGAドリームex M3 -> M2a）を元に戻していたため、本体を no-op に置換した。
--

DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: product mark seed removed — manage via app/CSV'; END $$;
