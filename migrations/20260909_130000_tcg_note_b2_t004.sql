-- NOTE-B2: value-carrying note labels and normalization rules (tenant_004)
-- Design: docs/handoff/tcg-product-master-growth/design-note-master.md B2-3 through B2-7
-- Idempotent: additive columns, deterministic updates, conflict-safe inserts
-- Validation counts only IDs owned by this migration.

DO $body$
DECLARE
    _schema   TEXT := 'tenant_004';
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260909_130000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format(
        'ALTER TABLE %I.tcg_note_master ADD COLUMN IF NOT EXISTS match_type TEXT NOT NULL DEFAULT ''LITERAL''',
        _schema
    );
    EXECUTE format(
        'ALTER TABLE %I.tcg_note_master ADD COLUMN IF NOT EXISTS search_pattern TEXT',
        _schema
    );
    EXECUTE format(
        'ALTER TABLE %I.tcg_note_master ADD COLUMN IF NOT EXISTS label_template TEXT',
        _schema
    );

    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
END $body$;
