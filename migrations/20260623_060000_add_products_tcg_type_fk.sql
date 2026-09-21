-- ============================================================================
-- Migration 20260623_030000: products.tcg_type を tcg_type_master.code に固定
--
-- 方針:
--   - pre-flight で public.products の不正 tcg_type を distinct 列挙
--   - 1 件でも見つかったら RAISE EXCEPTION で中止
--   - ゼロ件なら FK を追加
--   - データ変更なし（制約のみ）
-- ============================================================================

DO $$
DECLARE
    invalid_codes TEXT;
    _fk_target TEXT;
BEGIN
    -- ADR-156 Phase 1: tcg_type_master がテーブルならそのまま参照。
    -- ビュー（type_master へリネーム済み）なら type_master を参照する。
    -- type_master も tcg_type_master も存在しない場合はスキップ。
    IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'tcg_type_master' AND c.relkind = 'r'
    ) THEN
        _fk_target := 'tcg_type_master';
    ELSIF to_regclass('public.type_master') IS NOT NULL THEN
        _fk_target := 'type_master';
    ELSE
        _fk_target := NULL;
    END IF;

    IF to_regclass('public.products') IS NULL
       OR _fk_target IS NULL
       OR NOT EXISTS (
            SELECT 1
              FROM pg_attribute a
              JOIN pg_class rel ON rel.oid = a.attrelid
              JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
             WHERE nsp.nspname = 'public'
               AND rel.relname = 'products'
               AND a.attname = 'tcg_type'
               AND a.attnum > 0
               AND NOT a.attisdropped
       ) THEN
        RAISE NOTICE
            'fk_products_tcg_type preflight skipped: public.products / public.products.tcg_type / type master is missing';
    ELSE
        SELECT string_agg(quote_literal(tc), ', ' ORDER BY tc)
          INTO invalid_codes
          FROM (
            SELECT DISTINCT tcg_type AS tc
              FROM public.products
             WHERE tcg_type IS NOT NULL
               AND tcg_type NOT IN (SELECT code FROM public.tcg_type_master)
          ) invalids;

        IF invalid_codes IS NOT NULL THEN
            RAISE EXCEPTION
                'fk_products_tcg_type preflight failed: invalid tcg_type values found: %',
                invalid_codes;
        END IF;

        IF NOT EXISTS (
            SELECT 1
              FROM pg_constraint c
              JOIN pg_class rel ON rel.oid = c.conrelid
             WHERE c.conname = 'fk_products_tcg_type'
               AND rel.relname = 'products'
               AND rel.relnamespace = 'public'::regnamespace
        ) THEN
            IF _fk_target = 'type_master' THEN
                ALTER TABLE public.products
                    ADD CONSTRAINT fk_products_tcg_type
                    FOREIGN KEY (tcg_type) REFERENCES public.type_master(code);
            ELSE
                ALTER TABLE public.products
                    ADD CONSTRAINT fk_products_tcg_type
                    FOREIGN KEY (tcg_type) REFERENCES public.tcg_type_master(code);
            END IF;
        END IF;
    END IF;
END $$;
