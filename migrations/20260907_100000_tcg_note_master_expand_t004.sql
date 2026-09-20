-- MIG NOTE-EXPAND-A: tcg_note_master 固定札26件追加＋既存2行の検索語更新 (tenant_004)
-- 設計: docs/handoff/tcg-product-master-growth/design-note-master.md 4-2
-- 対象ADR: ADR-154
-- 冪等: INSERT ON CONFLICT DO NOTHING / UPDATE は同値の再代入
-- 件数確認は本ファイルが投入する26件の範囲のみを数える（テーブル全体は数えない）

DO $body$
DECLARE
    _schema TEXT    := 'tenant_004';
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260907_100000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
END $body$;
