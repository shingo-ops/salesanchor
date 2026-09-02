-- MIG PARITY-02 A-7: products_logistics 廃止 (tenant_004)
-- 2列のみ（product_id, created_at）・実質空テーブル・GAS・Python 参照ゼロ確認済み
-- PO 廃止承認: CC_TASK_PARITY-02_full_migration.md §着手順序 A-7
-- 冪等: DROP TABLE IF EXISTS

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_140000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- products_logistics が存在する場合のみ DROP（冪等）
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = _schema AND table_name = 'products_logistics'
    ) THEN
        EXECUTE format('DROP TABLE %I.products_logistics', _schema);
        RAISE NOTICE 'migration 20260903_140000: dropped %.products_logistics', _schema;
    ELSE
        RAISE NOTICE 'migration 20260903_140000: %.products_logistics already absent, skipping', _schema;
    END IF;
END $body$;
