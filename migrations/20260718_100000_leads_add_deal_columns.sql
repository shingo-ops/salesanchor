-- deals廃止 段階①: leads に商談列を追加（全テナント・冪等）
-- 設計: docs/specs/db-ssot/deal-removal/design.md §4.5
-- 既存テナント/新テナントの両方で同じ列を持つため、IF NOT EXISTS を付与する。
DO $$
DECLARE
    s TEXT;
BEGIN
    FOR s IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.leads ADD COLUMN IF NOT EXISTS amount NUMERIC(15,2)',
            s
        );
        EXECUTE format(
            'ALTER TABLE %I.leads ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT ''JPY''',
            s
        );
        EXECUTE format(
            'ALTER TABLE %I.leads ADD COLUMN IF NOT EXISTS expected_close_date DATE',
            s
        );
        RAISE NOTICE 'leads columns added or already present on %', s;
    END LOOP;
END $$;
