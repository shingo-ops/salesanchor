-- Migration 096: 全テナントの deals に lead_source カラムを追加
--
-- 目的:
--   商談情報の顧客情報セクションに「流入元」を記録できるようにする。
--   リードの source と同じ自由入力テキスト（最大50文字）。
--
-- 影響テーブル: {tenant_NNN}.deals
-- 適用対象: 全テナント（pg_namespace 走査で冪等適用）
-- 冪等: ADD COLUMN IF NOT EXISTS
-- ガード: deals テーブルが存在しないスキーマはスキップ（deals 廃止後の新テナント対応）

DO $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        -- deals テーブルが存在しない場合はスキップ
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_record.schema_name
              AND table_name = 'deals'
        ) THEN
            RAISE NOTICE 'Skipping schema %: deals table does not exist', schema_record.schema_name;
            CONTINUE;
        END IF;

        RAISE NOTICE 'Processing schema: %', schema_record.schema_name;

        EXECUTE format(
            'ALTER TABLE %I.deals
             ADD COLUMN IF NOT EXISTS lead_source VARCHAR(50)',
            schema_record.schema_name
        );
    END LOOP;
END
$$;
