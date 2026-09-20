-- MIG PARITY-02 A-3: tcg_note_master (tenant_004)
-- 注記マスタ 22件を新規テーブルへ投入
-- 移植元: investigate2.gs:14994-15134 (_NOTE_MASTER_ROWS_ 定義値)
--         HEADERS_NOTE_MASTER: 00_Constants.gs:38-47
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
        RAISE NOTICE 'migration 20260903_130000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- -------------------------------------------------------------------------
    -- テーブル作成（additive-only / IF NOT EXISTS）
    -- -------------------------------------------------------------------------
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_note_master (
            id               TEXT        PRIMARY KEY,
            label_ja         TEXT        NOT NULL,
            label_en         TEXT        NOT NULL,
            enabled          BOOLEAN     NOT NULL DEFAULT TRUE,
            search_keywords  TEXT        NOT NULL DEFAULT '',
            exclude_keywords TEXT        NOT NULL DEFAULT '',
            category         TEXT        NOT NULL DEFAULT '',
            priority         INTEGER     NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
END $body$;
