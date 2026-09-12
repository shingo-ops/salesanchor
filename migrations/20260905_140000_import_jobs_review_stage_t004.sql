-- migration: 20260905_140000_import_jobs_review_stage_t004
-- 目的: import_jobs に確認工程（review stage）用カラムを追加
--
-- 追加列:
--   pending_messages  JSONB          窓適用済みメッセージ（確認後に使う）
--   window_start      TIMESTAMPTZ    計算した窓の開始
--   window_end        TIMESTAMPTZ    計算した窓の終了
--   unresolved_names  JSONB          未解決の表示名（配列）
--   review_status     TEXT NOT NULL DEFAULT 'ok'
--                                   'pending_review' | 'ok' | 'discarded'
--
-- 冪等性: ADD COLUMN IF NOT EXISTS
-- 既存行: review_status='ok' になる（DEFAULT で充足）
-- 作成日: 2026-09-05

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ----------------------------------------------------------------
    -- ガード: tenant_004 が存在しない場合はスキップ
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260905_140000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    RAISE NOTICE 'migration 20260905_140000: adding review stage columns to import_jobs in schema %', _schema;

    -- ----------------------------------------------------------------
    -- 1. pending_messages: 窓適用済みメッセージ（保留時のみ非 NULL）
    -- ----------------------------------------------------------------
    EXECUTE format(
        'ALTER TABLE %I.import_jobs ADD COLUMN IF NOT EXISTS pending_messages JSONB',
        _schema
    );

    -- ----------------------------------------------------------------
    -- 2. window_start: 計算した窓の開始（保留時に確定値を保存）
    -- ----------------------------------------------------------------
    EXECUTE format(
        'ALTER TABLE %I.import_jobs ADD COLUMN IF NOT EXISTS window_start TIMESTAMPTZ',
        _schema
    );

    -- ----------------------------------------------------------------
    -- 3. window_end: 計算した窓の終了（保留時に確定値を保存）
    -- ----------------------------------------------------------------
    EXECUTE format(
        'ALTER TABLE %I.import_jobs ADD COLUMN IF NOT EXISTS window_end TIMESTAMPTZ',
        _schema
    );

    -- ----------------------------------------------------------------
    -- 4. unresolved_names: 未解決の表示名（文字列配列の JSONB）
    -- ----------------------------------------------------------------
    EXECUTE format(
        'ALTER TABLE %I.import_jobs ADD COLUMN IF NOT EXISTS unresolved_names JSONB',
        _schema
    );

    -- ----------------------------------------------------------------
    -- 5. review_status: 確認工程ステータス
    --    NOT NULL を付けるのはこの列のみ（DEFAULT 'ok' で既存行も充足）
    --    status 列（import 冪等化フラグ）と別管理
    -- ----------------------------------------------------------------
    EXECUTE format(
        $q$
        ALTER TABLE %I.import_jobs
            ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'ok'
        $q$,
        _schema
    );

    -- ----------------------------------------------------------------
    -- 6. インデックス: pending_review の高速検索
    -- ----------------------------------------------------------------
    EXECUTE format(
        $q$
        CREATE INDEX IF NOT EXISTS ix_import_jobs_review_status
            ON %I.import_jobs (review_status)
            WHERE review_status = 'pending_review'
        $q$,
        _schema
    );

    RAISE NOTICE 'migration 20260905_140000: 完了。import_jobs に 5 列追加（schema %）', _schema;
END $$;
