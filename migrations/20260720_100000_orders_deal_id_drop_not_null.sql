-- deals廃止 段階②(D3): orders.deal_id の NOT NULL を解除（company_id 直参照へ移行）
-- 設計: docs/specs/db-ssot/deal-removal/design.md §4.6
-- 冪等: 既に nullable ならそのまま成功する
-- 動的列挙: tenant_% スキーマのうち orders テーブルと deal_id 列が実在するもののみ適用
DO $$
DECLARE
    schema_record RECORD;
    applied_count INTEGER := 0;
    skipped_no_orders INTEGER := 0;
    skipped_no_deal_id INTEGER := 0;
BEGIN
    FOR schema_record IN
        SELECT schema_name
          FROM information_schema.schemata
         WHERE schema_name LIKE 'tenant_%'
         ORDER BY schema_name
    LOOP
        IF NOT EXISTS (
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = schema_record.schema_name
               AND table_name = 'orders'
        ) THEN
            skipped_no_orders := skipped_no_orders + 1;
            CONTINUE;
        END IF;

        IF NOT EXISTS (
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = schema_record.schema_name
               AND table_name = 'orders'
               AND column_name = 'deal_id'
        ) THEN
            skipped_no_deal_id := skipped_no_deal_id + 1;
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.orders ALTER COLUMN deal_id DROP NOT NULL',
            schema_record.schema_name
        );
        applied_count := applied_count + 1;
        RAISE NOTICE 'orders.deal_id nullable on %', schema_record.schema_name;
    END LOOP;

    RAISE NOTICE
        'orders.deal_id not-null drop done. applied=% skipped_no_orders=% skipped_no_deal_id=%',
        applied_count, skipped_no_orders, skipped_no_deal_id;
END $$;
