-- Phase 2b prerequisites: ensure public.products has the columns AND data
-- that Phase 2b-modified migrations (20260910_*, 20260913_*) reference.
-- Columns and data are also added by 20260914_140000 (Phase 2a unification),
-- but that migration runs later in sort order. Using IF NOT EXISTS and
-- ON CONFLICT ensures no conflict when 20260914 runs again.

-- ============================================================
-- Step 1: カラム追加
-- ============================================================

-- incident 2026-10-04 (deploy run 37133284790): tcg_uuid は 20260916_120000 で永久 DROP
-- される列。Phase 2c（tcg_products テーブル DROP、migrations/20260915_010000）が完了した後は
-- tcg_uuid は二度と必要にならないため、その状態を過ぎたら再 ADD しない（毎デプロイ ADD→DROP
-- を繰り返すと attribute number を消費し続け、public.products が 1600 列上限に達する）。
--
-- マーカー訂正（2026-10-04、設計担当 Opus の指摘）: 当初は「tenant_*.tcg_products が
-- どこにも残っていない」をマーカーにしていたが、これは誤り。設計担当 Opus が本番を
-- read-only で確認した事実（未確認ではなく確認済み）として、tenant_004.tcg_products は
-- 現在も存在する（Phase 2c の DROP が、tcg_uuid 側の churn バグにより毎回それより手前の
-- ステップで失敗し続けていたため、一度も実行完了に到達していない。作成元:
-- migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:91-92、
-- scripts/run_all_migrations.sh の line 530 と 536 に重複登録されている。この生成元
-- migration はこの PR では変更しない）。この状態で旧マーカーを使うと本番で再び
-- tcg_uuid を ADD しようとして同じ 1600 列上限エラーで失敗する。
--
-- 正しいマーカー: public.products.work_id は migrations/20260919_010000_master_ssot_work_id_recast.sql
-- （scripts/run_all_migrations.sh の tcg_uuid DROP より後、work_id を UUID→INTEGER に
-- 永久変換する）が成功した後は INTEGER のまま変わらない（他のどの migration も
-- public.products.work_id を再び UUID にはしない）。よって
-- 「tcg_uuid が既に存在する」または「work_id が INTEGER でない（未存在 or UUID）」場合のみ
-- ADD + index を実行し、「tcg_uuid が無い かつ work_id が INTEGER」なら恒久的にスキップする。
-- 詳細: docs/handoff/products-column-churn-2/design.md
DO $guard_tcg_uuid$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products'
          AND column_name = 'work_id' AND data_type = 'integer'
    ) THEN
        ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid UUID;

        -- tcg_uuid に部分ユニークインデックス（ON CONFLICT で必要）
        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_tcg_uuid
            ON public.products (tcg_uuid) WHERE tcg_uuid IS NOT NULL;
    ELSE
        RAISE NOTICE 'tcg_uuid: work_id が INTEGER に再キャスト済み（Phase 3 完了）— tcg_uuid 再 ADD をスキップ';
    END IF;
END $guard_tcg_uuid$;

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS division_id       UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS work_id           UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS manufacturer_id   UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS product_category_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS category_class    TEXT;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_active         BOOLEAN DEFAULT true;

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
