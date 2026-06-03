-- ============================================================================
-- Migration 20260603_040000: public.products に set_type（セット種別）を追加。
--
-- 商品マスタ編集の「型番」右に置くセット種別の選択肢:
--   booster(ブースター) / deck(デッキ) / single(シングルカード) / bulk(バルク)
-- 値検証はアプリ側（Pydantic / UI プルダウン）で行い、DB は自由 VARCHAR。
--
-- 冪等: ADD COLUMN IF NOT EXISTS。NULL 許可。additive-only。
-- ============================================================================

DO $$
BEGIN
    IF to_regclass('public.products') IS NULL THEN
        RAISE NOTICE 'public.products not present (migration-test baseline) — skipping';
    ELSE
        ALTER TABLE public.products
            ADD COLUMN IF NOT EXISTS set_type VARCHAR(50);
    END IF;
END $$;
