-- Migration: unify_tcg_products_to_public
--
-- 目的（ADR-1001 Phase 2a）:
--   tcg_products テーブルのデータを public.products に統合する。
--   Step1: public.products にカラム追加（7列）
--   Step2: 全テナントスキーマの tcg_products → public.products へコピー（冪等 UPSERT）
--   Step3: 依存テーブルの FK を tcg_products → public.products.tcg_uuid に張替え
--   Step4: 件数照合（不一致なら EXCEPTION で停止）
--
-- 冪等性:
--   - ALTER TABLE ... ADD COLUMN IF NOT EXISTS → 再実行 no-op
--   - CREATE UNIQUE INDEX IF NOT EXISTS → 再実行 no-op
--   - ON CONFLICT (product_code) WHERE product_code IS NOT NULL DO UPDATE → 再実行 no-op
--   - DROP CONSTRAINT + ADD CONSTRAINT は存在チェックを挟む → 再実行 no-op
--
-- 注意:
--   - tcg_products の DROP は行わない（Phase 2c で別途実施）
--   - Python コードの変更は行わない（Phase 2b で別途実施）
--   - 既存データの DELETE は行わない
--
-- 型安全ガード（2026-09-22 追加、2026-09-22 v2: product_category_id 追加）:
--   後続 migration（20260916_120000, 20260919_010000, 20260920_010000）が先行適用済みの場合、
--   public.products の列型が変わっているため UPSERT が型ミスマッチで失敗する。
--   Step2/Step3 の冒頭で pg_attribute を参照し、型が一致しない場合は SKIP する。
--     - tcg_uuid が UUID で存在しない → Step2/Step3 をスキップ（移行完了扱い）
--     - work_id が UUID でない（INTEGER 等）→ work_id を NULL キャストして UPSERT
--     - product_category_id が UUID でない（INTEGER 等）→ product_category_id を NULL キャストして UPSERT

BEGIN;

-- ============================================================
-- Step 1: public.products に7カラム追加
-- ============================================================

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid          UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS division_id       UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS work_id           UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS manufacturer_id   UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS product_category_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS category_class    TEXT;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_active         BOOLEAN DEFAULT true;

-- tcg_uuid に部分ユニークインデックス（NULL は除外）
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_tcg_uuid
    ON public.products (tcg_uuid) WHERE tcg_uuid IS NOT NULL;

-- tcg_uuid に正式な UNIQUE 制約を追加（FK 参照に必要。部分インデックスだけでは不十分）
DO $uq$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.products'::regclass
          AND conname = 'uq_products_tcg_uuid'
          AND contype = 'u'
    ) THEN
        ALTER TABLE public.products ADD CONSTRAINT uq_products_tcg_uuid UNIQUE (tcg_uuid);
    END IF;
END;
$uq$;

-- ============================================================
-- Step 2: tcg_products → public.products データコピー
-- ============================================================

DO $step2$
DECLARE
    schema_record    RECORD;
    upserted_count   INTEGER;
    total_upserted   INTEGER := 0;
    _tcg_uuid_is_uuid            BOOLEAN;
    _work_id_is_uuid             BOOLEAN;
    _product_category_id_is_uuid BOOLEAN;
BEGIN
    -- ---------------------------------------------------------------
    -- 型安全ガード: pg_attribute で public.products の列型を確認する。
    -- 後続 migration（20260916_120000: tcg_uuid DROP,
    --                  20260919_010000: work_id UUID→INTEGER スワップ,
    --                  20260920_010000: product_category_id UUID→INTEGER スワップ）が
    -- 先行適用済みの場合、列型が変わっており UPSERT が型ミスマッチで失敗する。
    -- ---------------------------------------------------------------

    -- tcg_uuid が UUID 型で存在するか確認
    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'products'
          AND a.attname = 'tcg_uuid'
          AND a.atttypid = 'uuid'::regtype::oid
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _tcg_uuid_is_uuid;

    IF NOT _tcg_uuid_is_uuid THEN
        RAISE NOTICE 'Step2: public.products.tcg_uuid が UUID 型で存在しません（Phase 2c 適用済み or DROP 済み）。Step2 をスキップします。';
        RETURN;
    END IF;

    -- work_id が UUID 型で存在するか確認
    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'products'
          AND a.attname = 'work_id'
          AND a.atttypid = 'uuid'::regtype::oid
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _work_id_is_uuid;

    IF NOT _work_id_is_uuid THEN
        RAISE NOTICE 'Step2: public.products.work_id が UUID 型ではありません（20260919_010000 適用済み）。work_id は NULL でコピーします。';
    END IF;

    -- product_category_id が UUID 型で存在するか確認
    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'products'
          AND a.attname = 'product_category_id'
          AND a.atttypid = 'uuid'::regtype::oid
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _product_category_id_is_uuid;

    IF NOT _product_category_id_is_uuid THEN
        RAISE NOTICE 'Step2: public.products.product_category_id が UUID 型ではありません（20260920_010000 適用済み）。product_category_id は NULL でコピーします。';
    END IF;

    -- RLS 対応: jarvis は非 superuser のため operator フラグを立てる
    -- public.products は FORCE ROW LEVEL SECURITY がかかっており、
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
        RAISE NOTICE 'Step2: processing schema %', schema_record.schema_name;

        IF _work_id_is_uuid AND _product_category_id_is_uuid THEN
            -- 通常ケース: 両列が UUID 型のまま → そのままコピー
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
        ELSIF NOT _work_id_is_uuid AND _product_category_id_is_uuid THEN
            -- work_id が INTEGER に変わっているが product_category_id はまだ UUID
            -- (20260919 適用済み・20260920 未適用)
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
                    NULL::INTEGER,
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
                    manufacturer_id      = EXCLUDED.manufacturer_id,
                    product_category_id  = EXCLUDED.product_category_id,
                    category_class       = EXCLUDED.category_class,
                    is_active            = EXCLUDED.is_active
            $dml$, schema_record.schema_name);
        ELSE
            -- 型ミスマッチケース: work_id と product_category_id の両方が INTEGER に変わっている
            -- (20260919 + 20260920 適用済み) → 両列とも NULL でコピー
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
                    NULL::INTEGER,
                    t.manufacturer_id,
                    NULL::INTEGER,
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
                    manufacturer_id      = EXCLUDED.manufacturer_id,
                    category_class       = EXCLUDED.category_class,
                    is_active            = EXCLUDED.is_active
            $dml$, schema_record.schema_name);
        END IF;

        GET DIAGNOSTICS upserted_count = ROW_COUNT;
        total_upserted := total_upserted + upserted_count;
        RAISE NOTICE 'Step2: schema % → % rows upserted', schema_record.schema_name, upserted_count;
    END LOOP;

    RAISE NOTICE 'Step2 complete: total % rows upserted into public.products', total_upserted;
END;
$step2$;

-- ============================================================
-- Step 3: FK 依存テーブルの制約張替え
-- ============================================================

DO $step3$
DECLARE
    schema_record     RECORD;
    old_conname       TEXT;
    new_fk_name       TEXT;
    _tcg_uuid_is_uuid BOOLEAN;
    _pid_type         OID;
BEGIN
    -- 型安全ガード: tcg_uuid が UUID 型で存在する場合のみ FK 張替えを実施する。
    -- 20260916_120000（tcg_uuid DROP）が先行済みなら張替えは不要（既に完了 or 不要）。
    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'products'
          AND a.attname = 'tcg_uuid'
          AND a.atttypid = 'uuid'::regtype::oid
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _tcg_uuid_is_uuid;

    IF NOT _tcg_uuid_is_uuid THEN
        RAISE NOTICE 'Step3: public.products.tcg_uuid が UUID 型で存在しません。FK 張替えをスキップします。';
        RETURN;
    END IF;

    FOR schema_record IN
        SELECT n.nspname AS schema_name
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_products'
          AND c.relkind = 'r'
        ORDER BY n.nspname
    LOOP
        RAISE NOTICE 'Step3: processing schema %', schema_record.schema_name;

        -- --------------------------------------------------------
        -- 3-1. product_search_keywords
        -- --------------------------------------------------------
        -- 既存の tcg_products 向け FK を取得して DROP
        SELECT c.conname INTO old_conname
        FROM pg_constraint c
        JOIN pg_class rel ON c.conrelid = rel.oid
        JOIN pg_namespace ns ON rel.relnamespace = ns.oid
        JOIN pg_class ref ON c.confrelid = ref.oid
        WHERE ns.nspname = schema_record.schema_name
          AND rel.relname = 'product_search_keywords'
          AND ref.relname = 'tcg_products'
          AND c.contype = 'f'
        LIMIT 1;

        IF old_conname IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.product_search_keywords DROP CONSTRAINT %I',
                           schema_record.schema_name, old_conname);
            RAISE NOTICE 'Step3: dropped FK % on %.product_search_keywords', old_conname, schema_record.schema_name;
        END IF;

        -- 新 FK（public.products.tcg_uuid 向け）が未存在なら CREATE
        -- 型チェック: product_id が UUID 型でなければ FK 作成をスキップ
        SELECT a.atttypid INTO _pid_type
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = schema_record.schema_name
          AND c.relname = 'product_search_keywords'
          AND a.attname = 'product_id'
          AND NOT a.attisdropped;

        IF _pid_type IS DISTINCT FROM (SELECT oid FROM pg_type WHERE typname = 'uuid') THEN
            RAISE NOTICE 'Step3: %.product_search_keywords.product_id is not UUID (atttypid=%). Skipping FK rewire.', schema_record.schema_name, _pid_type;
        ELSE
        new_fk_name := 'fk_product_search_keywords_product_public';
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c
            JOIN pg_class rel ON c.conrelid = rel.oid
            JOIN pg_namespace ns ON rel.relnamespace = ns.oid
            WHERE ns.nspname = schema_record.schema_name
              AND rel.relname = 'product_search_keywords'
              AND c.conname = new_fk_name
              AND c.contype = 'f'
        ) THEN
            EXECUTE format($ddl$
                ALTER TABLE %I.product_search_keywords
                    ADD CONSTRAINT fk_product_search_keywords_product_public
                    FOREIGN KEY (product_id)
                    REFERENCES public.products (tcg_uuid)
                    ON DELETE CASCADE
            $ddl$, schema_record.schema_name);
            RAISE NOTICE 'Step3: created FK % on %.product_search_keywords', new_fk_name, schema_record.schema_name;
        ELSE
            RAISE NOTICE 'Step3: FK % already exists on %.product_search_keywords, skipping', new_fk_name, schema_record.schema_name;
        END IF;
        END IF; -- end UUID type guard for product_search_keywords

        -- --------------------------------------------------------
        -- 3-2. product_exclude_keywords
        -- --------------------------------------------------------
        old_conname := NULL;
        SELECT c.conname INTO old_conname
        FROM pg_constraint c
        JOIN pg_class rel ON c.conrelid = rel.oid
        JOIN pg_namespace ns ON rel.relnamespace = ns.oid
        JOIN pg_class ref ON c.confrelid = ref.oid
        WHERE ns.nspname = schema_record.schema_name
          AND rel.relname = 'product_exclude_keywords'
          AND ref.relname = 'tcg_products'
          AND c.contype = 'f'
        LIMIT 1;

        IF old_conname IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.product_exclude_keywords DROP CONSTRAINT %I',
                           schema_record.schema_name, old_conname);
            RAISE NOTICE 'Step3: dropped FK % on %.product_exclude_keywords', old_conname, schema_record.schema_name;
        END IF;

        -- 型チェック: product_id が UUID 型でなければ FK 作成をスキップ
        SELECT a.atttypid INTO _pid_type
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = schema_record.schema_name
          AND c.relname = 'product_exclude_keywords'
          AND a.attname = 'product_id'
          AND NOT a.attisdropped;

        IF _pid_type IS DISTINCT FROM (SELECT oid FROM pg_type WHERE typname = 'uuid') THEN
            RAISE NOTICE 'Step3: %.product_exclude_keywords.product_id is not UUID (atttypid=%). Skipping FK rewire.', schema_record.schema_name, _pid_type;
        ELSE
        new_fk_name := 'fk_product_exclude_keywords_product_public';
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c
            JOIN pg_class rel ON c.conrelid = rel.oid
            JOIN pg_namespace ns ON rel.relnamespace = ns.oid
            WHERE ns.nspname = schema_record.schema_name
              AND rel.relname = 'product_exclude_keywords'
              AND c.conname = new_fk_name
              AND c.contype = 'f'
        ) THEN
            EXECUTE format($ddl$
                ALTER TABLE %I.product_exclude_keywords
                    ADD CONSTRAINT fk_product_exclude_keywords_product_public
                    FOREIGN KEY (product_id)
                    REFERENCES public.products (tcg_uuid)
                    ON DELETE CASCADE
            $ddl$, schema_record.schema_name);
            RAISE NOTICE 'Step3: created FK % on %.product_exclude_keywords', new_fk_name, schema_record.schema_name;
        ELSE
            RAISE NOTICE 'Step3: FK % already exists on %.product_exclude_keywords, skipping', new_fk_name, schema_record.schema_name;
        END IF;
        END IF; -- end UUID type guard for product_exclude_keywords

        -- --------------------------------------------------------
        -- 3-3. products_logistics
        -- --------------------------------------------------------
        old_conname := NULL;
        SELECT c.conname INTO old_conname
        FROM pg_constraint c
        JOIN pg_class rel ON c.conrelid = rel.oid
        JOIN pg_namespace ns ON rel.relnamespace = ns.oid
        JOIN pg_class ref ON c.confrelid = ref.oid
        WHERE ns.nspname = schema_record.schema_name
          AND rel.relname = 'products_logistics'
          AND ref.relname = 'tcg_products'
          AND c.contype = 'f'
        LIMIT 1;

        IF old_conname IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.products_logistics DROP CONSTRAINT %I',
                           schema_record.schema_name, old_conname);
            RAISE NOTICE 'Step3: dropped FK % on %.products_logistics', old_conname, schema_record.schema_name;
        END IF;

        -- 型チェック: product_id が UUID 型でなければ FK 作成をスキップ
        SELECT a.atttypid INTO _pid_type
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = schema_record.schema_name
          AND c.relname = 'products_logistics'
          AND a.attname = 'product_id'
          AND NOT a.attisdropped;

        IF _pid_type IS DISTINCT FROM (SELECT oid FROM pg_type WHERE typname = 'uuid') THEN
            RAISE NOTICE 'Step3: %.products_logistics.product_id is not UUID (atttypid=%). Skipping FK rewire.', schema_record.schema_name, _pid_type;
        ELSE
        new_fk_name := 'fk_products_logistics_product_public';
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c
            JOIN pg_class rel ON c.conrelid = rel.oid
            JOIN pg_namespace ns ON rel.relnamespace = ns.oid
            WHERE ns.nspname = schema_record.schema_name
              AND rel.relname = 'products_logistics'
              AND c.conname = new_fk_name
              AND c.contype = 'f'
        ) THEN
            EXECUTE format($ddl$
                ALTER TABLE %I.products_logistics
                    ADD CONSTRAINT fk_products_logistics_product_public
                    FOREIGN KEY (product_id)
                    REFERENCES public.products (tcg_uuid)
                    ON DELETE CASCADE
            $ddl$, schema_record.schema_name);
            RAISE NOTICE 'Step3: created FK % on %.products_logistics', new_fk_name, schema_record.schema_name;
        ELSE
            RAISE NOTICE 'Step3: FK % already exists on %.products_logistics, skipping', new_fk_name, schema_record.schema_name;
        END IF;
        END IF; -- end UUID type guard for products_logistics

        -- --------------------------------------------------------
        -- 3-4. analysis_results（ON DELETE なし）
        -- --------------------------------------------------------
        old_conname := NULL;
        SELECT c.conname INTO old_conname
        FROM pg_constraint c
        JOIN pg_class rel ON c.conrelid = rel.oid
        JOIN pg_namespace ns ON rel.relnamespace = ns.oid
        JOIN pg_class ref ON c.confrelid = ref.oid
        WHERE ns.nspname = schema_record.schema_name
          AND rel.relname = 'analysis_results'
          AND ref.relname = 'tcg_products'
          AND c.contype = 'f'
        LIMIT 1;

        IF old_conname IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.analysis_results DROP CONSTRAINT %I',
                           schema_record.schema_name, old_conname);
            RAISE NOTICE 'Step3: dropped FK % on %.analysis_results', old_conname, schema_record.schema_name;
        END IF;

        -- 型チェック: product_id が UUID 型でなければ FK 作成をスキップ
        SELECT a.atttypid INTO _pid_type
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = schema_record.schema_name
          AND c.relname = 'analysis_results'
          AND a.attname = 'product_id'
          AND NOT a.attisdropped;

        IF _pid_type IS DISTINCT FROM (SELECT oid FROM pg_type WHERE typname = 'uuid') THEN
            RAISE NOTICE 'Step3: %.analysis_results.product_id is not UUID (atttypid=%). Skipping FK rewire.', schema_record.schema_name, _pid_type;
        ELSE
        new_fk_name := 'fk_analysis_results_product_public';
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c
            JOIN pg_class rel ON c.conrelid = rel.oid
            JOIN pg_namespace ns ON rel.relnamespace = ns.oid
            WHERE ns.nspname = schema_record.schema_name
              AND rel.relname = 'analysis_results'
              AND c.conname = new_fk_name
              AND c.contype = 'f'
        ) THEN
            EXECUTE format($ddl$
                ALTER TABLE %I.analysis_results
                    ADD CONSTRAINT fk_analysis_results_product_public
                    FOREIGN KEY (product_id)
                    REFERENCES public.products (tcg_uuid)
            $ddl$, schema_record.schema_name);
            RAISE NOTICE 'Step3: created FK % on %.analysis_results', new_fk_name, schema_record.schema_name;
        ELSE
            RAISE NOTICE 'Step3: FK % already exists on %.analysis_results, skipping', new_fk_name, schema_record.schema_name;
        END IF;
        END IF; -- end UUID type guard for analysis_results

    END LOOP;

    RAISE NOTICE 'Step3 complete: FK張替え完了';
END;
$step3$;

-- ============================================================
-- Step 4: 件数照合（不一致なら EXCEPTION で停止）
-- ============================================================

DO $step4$
DECLARE
    schema_record     RECORD;
    tcg_count         BIGINT;
    public_count      BIGINT;
    total_tcg         BIGINT := 0;
    _tcg_uuid_is_uuid BOOLEAN;
BEGIN
    -- ADR-1002: Phase 2c で tcg_products が全テナントから DROP 済みの場合、
    -- データは過去のデプロイで移行完了しているため件数照合をスキップする。
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_products'
          AND c.relkind = 'r'
    ) THEN
        RAISE NOTICE 'Step4: tcg_products が全テナントで不在（Phase 2c 完了済み）— 件数照合をスキップ';
        RETURN;
    END IF;

    -- 型安全ガード: tcg_uuid が UUID 型で存在しない場合は照合もスキップ
    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'products'
          AND a.attname = 'tcg_uuid'
          AND a.atttypid = 'uuid'::regtype::oid
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _tcg_uuid_is_uuid;

    IF NOT _tcg_uuid_is_uuid THEN
        RAISE NOTICE 'Step4: public.products.tcg_uuid が UUID 型で存在しません（Phase 2c 適用済み）— 件数照合をスキップ';
        RETURN;
    END IF;

    FOR schema_record IN
        SELECT n.nspname AS schema_name
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_products'
          AND c.relkind = 'r'
        ORDER BY n.nspname
    LOOP
        EXECUTE format('SELECT count(*) FROM %I.tcg_products', schema_record.schema_name)
            INTO tcg_count;
        total_tcg := total_tcg + tcg_count;
        RAISE NOTICE 'Step4: %.tcg_products count = %', schema_record.schema_name, tcg_count;
    END LOOP;

    SELECT count(*) INTO public_count
    FROM public.products
    WHERE tcg_uuid IS NOT NULL;

    RAISE NOTICE 'Step4: total tcg_products across all schemas = %', total_tcg;
    RAISE NOTICE 'Step4: public.products WHERE tcg_uuid IS NOT NULL = %', public_count;

    IF total_tcg <> public_count THEN
        RAISE EXCEPTION
            'Step4 FAILED: 件数不一致。tcg合計=% vs public.products(tcg_uuid IS NOT NULL)=%. 移行に問題があります。',
            total_tcg, public_count;
    END IF;

    RAISE NOTICE 'Step4 OK: 件数一致 (%件)', public_count;
END;
$step4$;

COMMIT;
