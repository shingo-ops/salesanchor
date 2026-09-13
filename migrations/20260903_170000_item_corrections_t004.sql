-- PARITY-03 Phase 3 Stage 3: 修正履歴テーブル（tenant_004 専用・冪等）
--
-- 設計方針:
--   1修正 = 1行（field_name 単位で append-only）。GAS は上書き方式だが踏襲しない。
--   system_value: Gemini 抽出値（修正時点）、human_value: 人間の修正値
--   extraction_item_id / source_message_id は FK 制約なし（参照先が別スキーマのため）

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_170000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- item_corrections テーブル作成（additive-only / IF NOT EXISTS）
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.item_corrections (
            id                 BIGSERIAL    PRIMARY KEY,
            extraction_item_id UUID         NOT NULL,
            source_message_id  UUID         NOT NULL,
            field_name         TEXT         NOT NULL,
            system_value       TEXT         NOT NULL DEFAULT '',
            human_value        TEXT         NOT NULL,
            corrected_by       TEXT         NOT NULL,
            corrected_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    EXECUTE format($ddl$
        CREATE INDEX IF NOT EXISTS idx_item_corrections_extraction_item_id
            ON %I.item_corrections (extraction_item_id)
    $ddl$, _schema);

    EXECUTE format($ddl$
        CREATE INDEX IF NOT EXISTS idx_item_corrections_corrected_at
            ON %I.item_corrections (corrected_at DESC)
    $ddl$, _schema);

    RAISE NOTICE 'migration 20260903_170000: item_corrections created in schema %', _schema;
END;
$body$;
