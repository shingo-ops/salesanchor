-- DIST-01 B: tcg_distribution_targets テーブル作成（tenant_004 専用・冪等）
--
-- 配信先マスタ。GAS TenantDistribution.js の TENANT_SHEET_COLS_ を FastAPI へ移植。
-- SA キーは既存 env var TCG_SHEETS_SA_KEY_FILE を流用。
-- sa_key_secret_name は将来の複数SAキー対応のためのメタデータ列（現在は固定値）。

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_200000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_distribution_targets (
            id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            name                    TEXT         NOT NULL,
            spreadsheet_id          TEXT         NOT NULL,
            sheet_name              TEXT         NOT NULL,
            is_active               BOOLEAN      NOT NULL DEFAULT TRUE,
            sa_key_secret_name      TEXT         NOT NULL DEFAULT 'TCG_SHEETS_SA_KEY_FILE',
            last_distributed_at     TIMESTAMPTZ,
            last_distributed_count  INTEGER,
            last_result             TEXT,
            created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    EXECUTE format($ddl$
        CREATE INDEX IF NOT EXISTS idx_dist_targets_is_active
            ON %I.tcg_distribution_targets (is_active)
    $ddl$, _schema);

    RAISE NOTICE 'migration 20260903_200000: tcg_distribution_targets created (or already existed)';
END
$body$;
