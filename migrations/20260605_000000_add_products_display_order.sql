-- ============================================================================
-- Migration 20260605_000000: public.products に display_order（手動並び替え順）を追加。
--
-- 商品マスタ一覧（ProductsPage）の行ドラッグ並び替え用。各種マスタと同様に
-- 「手動並び替え」ソートモードで display_order 昇順に並べ、ドラッグで値を入れ替える。
--
-- 冪等: ADD COLUMN IF NOT EXISTS。NULL 許可。additive-only。
-- backfill は display_order IS NULL の行のみ id を初期値に入れる（毎デプロイ再実行されるが、
--   ユーザーが設定済みの順序は NULL でないため上書きしない＝順序保全）。新規商品は次回 NULL→id。
-- ============================================================================

DO $$
BEGIN
    IF to_regclass('public.products') IS NULL THEN
        RAISE NOTICE 'public.products not present (migration-test baseline) — skipping';
    ELSE
        ALTER TABLE public.products
            ADD COLUMN IF NOT EXISTS display_order INTEGER;
        -- 未設定行のみ id を初期順として付与（設定済みの手動順は保持）
        UPDATE public.products SET display_order = id WHERE display_order IS NULL;
    END IF;
END $$;
