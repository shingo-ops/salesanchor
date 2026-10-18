-- Migration 20260602_020000: ADR-090 PR5a — public.products に tcg_type 列追加（ADR-1030 で削除済み）
--
-- （削除済み）products.tcg_type は ADR-1030 で取り除いた。作品の正本は products.work_id。
-- products は列番号が上限 1600 に達しているため、ここで列を足し直すと毎デプロイ失敗する。ADD を戻さないこと。
-- 列と FK・索引は 20261018_110000_drop_products_tcg_type.sql が取り除く。

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- category から tcg_type を埋める UPDATE 7 本を外した（本番は 0 行）。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: tcg_type backfill removed'; END $$;
