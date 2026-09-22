-- Phase 2b prerequisites: ensure public.products has the columns AND data
-- that Phase 2b-modified migrations (20260910_*, 20260913_*) reference.
-- Columns and data are also added by 20260914_140000 (Phase 2a unification),
-- but that migration runs later in sort order. Using IF NOT EXISTS and
-- ON CONFLICT ensures no conflict when 20260914 runs again.

-- ============================================================
-- Step 1: カラム追加
-- ============================================================

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid          UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS division_id       UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS work_id           UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS manufacturer_id   UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS product_category_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS category_class    TEXT;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_active         BOOLEAN DEFAULT true;

-- tcg_uuid に部分ユニークインデックス（ON CONFLICT で必要）
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_tcg_uuid
    ON public.products (tcg_uuid) WHERE tcg_uuid IS NOT NULL;

-- ============================================================
-- Step 2: tcg_products → public.products データコピー（冪等）
-- 20260914_140000 Step 2 と同一ロジック。先行実行で
-- 20260910_*/20260913_* が public.products を参照できるようにする。
-- ============================================================

DO $bootstrap$
DECLARE
    schema_record RECORD;
    upserted_count INTEGER;
    total_upserted INTEGER := 0;
BEGIN
    -- RLS 対応: public.products は FORCE ROW LEVEL SECURITY
    -- tenant_id = NULL の INSERT には is_operator = 'true' が必要
    SET LOCAL app.is_operator = 'true';

    FOR schema_record IN
        SELECT n.nspname AS schema_name
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_products'
          AND c.relkind = 'r'
        ORDER BY n.nspname
    LOOP
        RAISE NOTICE 'Phase2b bootstrap: processing schema %', schema_record.schema_name;

        -- Phase 3 がすでに work_id を INTEGER に変換済みの場合はスキップ
        -- (UUID型のデータを INTEGER列に INSERT しようとすると型不一致エラーになるため)
        IF EXISTS (
            SELECT 1 FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = 'products'
              AND a.attname = 'work_id'
              AND a.atttypid = 'integer'::regtype::oid
              AND a.attnum > 0
              AND NOT a.attisdropped
        ) THEN
            RAISE NOTICE 'Phase2b bootstrap: public.products.work_id already INTEGER (Phase 3 complete), skipping schema %', schema_record.schema_name;
            CONTINUE;
        END IF;

        EXECUTE format($dml$
            INSERT INTO public.products (
                product_code, name, name_en, mark, release_date,
                tcg_uuid, division_id, work_id, manufacturer_id, product_category_id,
                category_class, is_active
            )
            SELECT
                t.code,
                t.japanese_title,
                t.english_title,
                t.mark,
                t.release_date,
                t.id,
                t.division_id,
                t.work_id,
                t.manufacturer_id,
                t.product_category_id,
                t.category_class,
                t.is_active
            FROM %I.tcg_products t
            ON CONFLICT (product_code) WHERE product_code IS NOT NULL DO UPDATE SET
                name                 = EXCLUDED.name,
                name_en              = EXCLUDED.name_en,
                mark                 = EXCLUDED.mark,
                release_date         = EXCLUDED.release_date,
                tcg_uuid             = EXCLUDED.tcg_uuid,
                division_id          = EXCLUDED.division_id,
                work_id              = EXCLUDED.work_id,
                manufacturer_id      = EXCLUDED.manufacturer_id,
                product_category_id  = EXCLUDED.product_category_id,
                category_class       = EXCLUDED.category_class,
                is_active            = EXCLUDED.is_active
        $dml$, schema_record.schema_name);

        GET DIAGNOSTICS upserted_count = ROW_COUNT;
        total_upserted := total_upserted + upserted_count;
        RAISE NOTICE 'Phase2b bootstrap: schema % → % rows upserted', schema_record.schema_name, upserted_count;
    END LOOP;

    RAISE NOTICE 'Phase2b bootstrap complete: total % rows upserted into public.products', total_upserted;
END;
$bootstrap$;
