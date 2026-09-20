-- MIG PARITY-02 A-4: tcg_status_master (tenant_004)
-- ステータスマスタ 9件を新規テーブルへ投入
-- 移植元: GAS スプレッドシート「ステータスマスタ」タブ（全9行）
--         spreadsheetId: 1or39_glwYtF9OfOxXizN8ZjcUKL0hNIeW3qP3nCx3AI
-- 冪等: CREATE IF NOT EXISTS + INSERT ON CONFLICT DO NOTHING

DO $body$
DECLARE
    _schema TEXT    := 'tenant_004';
BEGIN
    -- -------------------------------------------------------------------------
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    -- -------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_150000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- -------------------------------------------------------------------------
    -- テーブル作成（additive-only / IF NOT EXISTS）
    -- -------------------------------------------------------------------------
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_status_master (
            status_id       TEXT        PRIMARY KEY,
            canonical       TEXT        NOT NULL,
            search_pattern  TEXT        NOT NULL DEFAULT '',
            exclude_pattern TEXT        NOT NULL DEFAULT '',
            priority        INTEGER     NOT NULL,
            enabled         BOOLEAN     NOT NULL DEFAULT TRUE,
            note            TEXT        NOT NULL DEFAULT '',
            match_type      TEXT        NOT NULL,
            effect          TEXT        NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
END $body$;
