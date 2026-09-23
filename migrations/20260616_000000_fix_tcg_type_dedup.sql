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
DECLARE
    _relkind CHAR(1);
    _target  TEXT;
BEGIN
    -- ガード: tcg_type_master も type_master も存在しない CI ベースラインはスキップ
    IF to_regclass('public.tcg_type_master') IS NULL
       AND to_regclass('public.type_master') IS NULL THEN
        RAISE NOTICE 'neither tcg_type_master nor type_master present -- skipping';
        RETURN;
    END IF;

    -- ADR-156 Phase 2 互換ガード: tcg_type_master が VIEW の場合は type_master を操作
    SELECT relkind INTO _relkind
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relname = 'tcg_type_master';

    IF _relkind = 'v' THEN
        _target := 'type_master';
    ELSE
        _target := 'tcg_type_master';
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
    -- Step 2: 重複行を削除（ビュー時は type_master から）
    -- =========================================================================
    EXECUTE format('DELETE FROM public.%I WHERE code IN (''pokemon'', ''weiss'')', _target);

END $$;
