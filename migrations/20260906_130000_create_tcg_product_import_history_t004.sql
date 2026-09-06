-- Migration: 20260906_130000_create_tcg_product_import_history_t004
-- IMPORT-01: tcg_product_import_jobs / tcg_product_import_rows — 商品マスタCSV取り込み履歴
--            （tenant_004 専用・additive only）
--
-- 設計判断:
--   - 新規テーブル2本のみ。ALTER / DROP なし。既存テーブルには一切触れない。
--   - 1ファイル＝1スキーマ（既存 _t004 / _t001 の作法に合わせる）。tenant_001 は別ファイル。
--   - raw_sha256 の UNIQUE で同一ファイルの二重取り込みを防ぐ（既存 import_jobs の方式を踏襲）。
--   - 桁数は実測値に合わせた: raw_sha256 VARCHAR(64) と status VARCHAR(30) は import_jobs と同じ、
--     product_code VARCHAR(20) は tcg_products.code と同じ、mark は tcg_products.mark が
--     桁数制限なしの character varying であるため TEXT とする。
--   - product_code は非FK（履歴であり、元行が消えても保持する設計）。
--   - result は本機能が定義する値（created / skipped / error）。実測ではなく設計上の選択。
--   - 検算は今回作成した2テーブルのみを名前指定でカウントする。スキーマ全体の件数は数えない
--     （全件カウントは 2026-09-05 のデプロイ失敗の直接原因であったため禁止）。
--   - 冪等: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
--
-- 根拠: docs/handoff/tcg-product-import/design.md 5-6
-- 作成日: 2026-09-06

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
    _table_count INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260906_130000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    RAISE NOTICE '20260906_130000: creating product import history tables in schema %', _schema;

    -- ----------------------------------------------------------------
    -- 1. tcg_product_import_jobs: 取り込み1回ぶんのメタデータ
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_product_import_jobs (
            id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            filename      TEXT         NOT NULL,
            raw_sha256    VARCHAR(64)  NOT NULL,
            total_rows    INTEGER      NOT NULL DEFAULT 0,
            created_rows  INTEGER      NOT NULL DEFAULT 0,
            skipped_rows  INTEGER      NOT NULL DEFAULT 0,
            executed_by   TEXT,
            status        VARCHAR(30)  NOT NULL DEFAULT 'ok',
            started_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            completed_at  TIMESTAMPTZ
        )
    $q$, _schema);

    EXECUTE format($q$
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tcg_product_import_jobs_raw_sha256
            ON %I.tcg_product_import_jobs (raw_sha256)
    $q$, _schema);

    -- ----------------------------------------------------------------
    -- 2. tcg_product_import_rows: CSVの1行ごとの結果
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_product_import_rows (
            id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id          UUID         NOT NULL
                                             REFERENCES %I.tcg_product_import_jobs (id) ON DELETE CASCADE,
            row_no          INTEGER      NOT NULL,
            japanese_title  TEXT         NOT NULL,
            mark            TEXT,
            result          VARCHAR(20)  NOT NULL,
            product_code    VARCHAR(20),
            messages        TEXT,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_tcg_product_import_rows_job_id
            ON %I.tcg_product_import_rows (job_id)
    $q$, _schema);

    -- ----------------------------------------------------------------
    -- 3. 検算: 今回作成した2テーブルのみを名前指定でカウント
    -- ----------------------------------------------------------------
    SELECT COUNT(*) INTO _table_count
    FROM information_schema.tables
    WHERE table_schema = _schema
      AND table_name IN ('tcg_product_import_jobs', 'tcg_product_import_rows');

    RAISE NOTICE '20260906_130000: schema % 作成テーブル数 = % (期待値: 2)', _schema, _table_count;

    IF _table_count <> 2 THEN
        RAISE EXCEPTION '20260906_130000: 作成テーブル数が 2 ではありません: %', _table_count;
    END IF;

    RAISE NOTICE '20260906_130000: 完了。schema % に tcg_product_import_jobs / tcg_product_import_rows を作成', _schema;
END $$;
