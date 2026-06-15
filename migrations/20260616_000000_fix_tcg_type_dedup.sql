-- ============================================================================
-- Migration 20260616_000000: tcg_type_master 重複 code 統合
--
-- 問題:
--   migration 085 で pokemon_booster_box（ポケモンカード）を登録済み。
--   migration 086 で weiss_schwarz（ヴァイスシュヴァルツ）を登録済み。
--   20260604_040000_seed_tcg_products_8series.sql が上記と重複する
--   pokemon（ポケモンカードゲーム）/ weiss（ヴァイスシュヴァルツ）を追加したため
--   UI の絞り込みドロップダウンに同名種別が2件ずつ表示されていた。
--
-- 修正:
--   1. products.tcg_type を正規 code へ統一
--      'pokemon' → 'pokemon_booster_box'
--      'weiss'   → 'weiss_schwarz'
--   2. 重複 tcg_type_master 行（pokemon / weiss）を削除
--
-- 冪等: WHERE 句が一致しない場合は何も変わらない。
-- ============================================================================

DO $$
BEGIN
    -- ガード: tcg_type_master が存在しない CI ベースラインはスキップ
    IF to_regclass('public.tcg_type_master') IS NULL THEN
        RAISE NOTICE 'tcg_type_master not present -- skipping';
        RETURN;
    END IF;

    -- =========================================================================
    -- Step 1: products.tcg_type を正規 code へ統一
    -- =========================================================================
    IF to_regclass('public.products') IS NOT NULL
       AND EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = 'products'
             AND column_name = 'tcg_type'
       )
    THEN
        UPDATE public.products
           SET tcg_type = 'pokemon_booster_box', updated_at = NOW()
         WHERE tcg_type = 'pokemon';

        UPDATE public.products
           SET tcg_type = 'weiss_schwarz', updated_at = NOW()
         WHERE tcg_type = 'weiss';
    END IF;

    -- =========================================================================
    -- Step 2: 重複 tcg_type_master 行を削除
    -- =========================================================================
    DELETE FROM public.tcg_type_master WHERE code IN ('pokemon', 'weiss');

END $$;
