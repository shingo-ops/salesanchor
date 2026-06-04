-- Migration: 全テナントの deals に lost_reason_code カラムを追加
--
-- 目的 (C-1):
--   失注理由を選択式で記録できるようにする。
--   既存の lost_reason（自由テキスト）は保持し将来廃止予定。
--
-- 影響テーブル: {tenant_NNN}.deals
-- 適用対象: 全テナント（pg_namespace 走査で冪等適用）
-- 冪等: ADD COLUMN IF NOT EXISTS + constraint の IF NOT EXISTS

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
        RAISE NOTICE 'Processing schema: %', schema_record.schema_name;

        -- lost_reason_code カラムを追加
        EXECUTE format(
            'ALTER TABLE %I.deals
             ADD COLUMN IF NOT EXISTS lost_reason_code VARCHAR(30)',
            schema_record.schema_name
        );

        -- CHECK 制約を追加（冪等: IF NOT EXISTS 相当の条件分岐）
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'chk_deals_lost_reason_code'
              AND connamespace = (
                  SELECT oid FROM pg_namespace
                  WHERE nspname = schema_record.schema_name
              )
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.deals
                 ADD CONSTRAINT chk_deals_lost_reason_code
                 CHECK (lost_reason_code IS NULL OR lost_reason_code IN (
                     ''price'',
                     ''lead_time'',
                     ''competitor'',
                     ''spec_condition'',
                     ''payment_terms'',
                     ''no_response'',
                     ''other''
                 ))',
                schema_record.schema_name
            );
        END IF;

        -- カラムコメント
        EXECUTE format(
            'COMMENT ON COLUMN %I.deals.lost_reason_code IS '
            '''C-1: 選択式失注理由。lost_reason（自由テキスト）と併用、将来的にlost_reasonは廃止予定''',
            schema_record.schema_name
        );
    END LOOP;
END
$$;
