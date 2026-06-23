-- Migration 20260623_040000: message_translations に tenant_id を追加し backfill する
--
-- 目的:
--   各 tenant schema の message_translations に tenant_id を追加し、
--   既存行を schema 名から導出した tenant 番号で埋める。
--   RLS はまだ有効化しない（phase 2 は別 migration）。
--
-- 冪等:
--   ALTER TABLE ... ADD COLUMN IF NOT EXISTS
--   UPDATE ... WHERE tenant_id IS NULL
--   既存行の translated_text / message_id 等は変更しない

DO $$
DECLARE
    schema_rec RECORD;
    tenant_num INTEGER;
BEGIN
    FOR schema_rec IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        tenant_num := substring(schema_rec.schema_name from '^tenant_([0-9]+)$')::INTEGER;

        EXECUTE format(
            'ALTER TABLE %I.message_translations ADD COLUMN IF NOT EXISTS tenant_id INTEGER',
            schema_rec.schema_name
        );

        EXECUTE format(
            'UPDATE %I.message_translations
             SET tenant_id = %s
             WHERE tenant_id IS NULL',
            schema_rec.schema_name,
            tenant_num
        );
    END LOOP;
END
$$;
