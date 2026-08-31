-- Migration: create_tcg_analysis_tables_t004
-- Alembic 源泉: 51c0207e4db4_create_tcg_analysis_tables_v1.py (Revision 1)
--              20260830_000000_mig04_import_tables.py      (Revision 2)
--
-- 背景:
--   TCG 仕入れ解析パイプライン（MIG-04）に必要な 18 テーブルを tenant_004 スキーマに作成する。
--   tenant_004 専用システム（HIGH LIFE JPN）のため他テナントから物理的に到達不可。
--
-- 設計判断:
--   - スキーマ: tenant_004 固定（他テナントループなし・到達不可）
--   - UUID: gen_random_uuid()（PostgreSQL 13+ 組み込み）
--   - 冪等性: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
--   - tenant_004 が存在しない場合はガードでスキップ
--   - CREATE 順序: 依存グラフ（Alembic 定義の親→子順）を維持
--   - 全 FK は tenant_004. 明示修飾
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS → 再実行 no-op
--   - CREATE INDEX IF NOT EXISTS → 再実行 no-op
--
-- 作成日: 2026-08-31

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
        RAISE NOTICE 'migration 20260831_110000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    RAISE NOTICE 'migration 20260831_110000: creating TCG analysis tables in schema %', _schema;

    -- ================================================================
    -- 1. 独立テーブル（FK なし / 自己参照のみ）
    -- ================================================================

    -- 1-1. audit_log: 変更履歴ログ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.audit_log (
            id          BIGSERIAL PRIMARY KEY,
            table_name  VARCHAR(100)                NOT NULL,
            record_id   UUID,
            action      VARCHAR(20)                 NOT NULL,
            changed_by  VARCHAR(100),
            changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            old_values  TEXT,
            new_values  TEXT
        )
    $q$, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_audit_log_changed_at
            ON %I.audit_log (changed_at)
    $q$, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_audit_log_table_record
            ON %I.audit_log (table_name, record_id)
    $q$, _schema);

    -- 1-2. conditions: コンディションマスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.conditions (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code        VARCHAR(20) NOT NULL,
            canonical   TEXT        NOT NULL,
            app_kubun   VARCHAR(50),
            is_active   BOOLEAN     NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (code)
        )
    $q$, _schema);

    -- 1-3. tcg_products: TCG商品マスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_products (
            id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code                  VARCHAR(20) NOT NULL,
            japanese_title        TEXT        NOT NULL,
            release_date          DATE,
            category_class        TEXT        NOT NULL,
            division_id           UUID,
            work_id               UUID,
            manufacturer_id       UUID,
            product_category_id   UUID,
            required_output_value TEXT,
            is_active             BOOLEAN     NOT NULL,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (code)
        )
    $q$, _schema);

    -- 1-4. tcg_suppliers: 仕入先マスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_suppliers (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code       VARCHAR(20) NOT NULL,
            name       TEXT        NOT NULL,
            is_active  BOOLEAN     NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (code)
        )
    $q$, _schema);

    -- 1-5. units: 単位マスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.units (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code       VARCHAR(20) NOT NULL,
            canonical  TEXT        NOT NULL,
            kubun      VARCHAR(50),
            is_active  BOOLEAN     NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (code)
        )
    $q$, _schema);

    -- ================================================================
    -- 2. 第1階層 FK（親: conditions / tcg_products / tcg_suppliers / units）
    -- ================================================================

    -- 2-1. condition_aliases: コンディション別名
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.condition_aliases (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            condition_id UUID        NOT NULL
                             REFERENCES %I.conditions (id) ON DELETE CASCADE,
            alias_text   TEXT        NOT NULL,
            lang         VARCHAR(10) NOT NULL,
            CONSTRAINT uq_condition_aliases_text_lang UNIQUE (alias_text, lang)
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_condition_aliases_condition_id
            ON %I.condition_aliases (condition_id)
    $q$, _schema);

    -- 2-2. product_exclude_keywords: 除外キーワード
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.product_exclude_keywords (
            id         UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID    NOT NULL
                                   REFERENCES %I.tcg_products (id) ON DELETE CASCADE,
            keyword    TEXT    NOT NULL,
            position   INTEGER NOT NULL
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_product_exclude_keywords_product_id
            ON %I.product_exclude_keywords (product_id)
    $q$, _schema);

    -- 2-3. product_search_keywords: 検索キーワード
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.product_search_keywords (
            id         UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID    NOT NULL
                                   REFERENCES %I.tcg_products (id) ON DELETE CASCADE,
            keyword    TEXT    NOT NULL,
            position   INTEGER NOT NULL
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_product_search_keywords_product_id
            ON %I.product_search_keywords (product_id)
    $q$, _schema);

    -- 2-4. products_logistics: 商品ロジスティクス（product_id が PK 兼 FK）
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.products_logistics (
            product_id UUID NOT NULL
                                REFERENCES %I.tcg_products (id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (product_id)
        )
    $q$, _schema, _schema);

    -- 2-5. supplier_channels: 仕入先チャンネル
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.supplier_channels (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            supplier_id UUID        NOT NULL
                                        REFERENCES %I.tcg_suppliers (id) ON DELETE CASCADE,
            channel     VARCHAR(50) NOT NULL,
            external_id TEXT,
            is_active   BOOLEAN     NOT NULL,
            CONSTRAINT uq_supplier_channels_channel_external UNIQUE (channel, external_id)
        )
    $q$, _schema, _schema);

    -- 2-6. unit_aliases: 単位別名
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.unit_aliases (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            unit_id    UUID        NOT NULL
                                       REFERENCES %I.units (id) ON DELETE CASCADE,
            alias_text TEXT        NOT NULL,
            lang       VARCHAR(10) NOT NULL,
            CONSTRAINT uq_unit_aliases_text_lang UNIQUE (alias_text, lang)
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_unit_aliases_unit_id
            ON %I.unit_aliases (unit_id)
    $q$, _schema);

    -- ================================================================
    -- 3. 第2階層 FK（親: supplier_channels）
    -- ================================================================

    -- 3-1. source_messages: 仕入元メッセージ（自己参照 FK: superseded_by）
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.source_messages (
            id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            supplier_channel_id UUID
                                    REFERENCES %I.supplier_channels (id) ON DELETE SET NULL,
            raw_text            TEXT        NOT NULL,
            raw_sha256          VARCHAR(64) NOT NULL,
            received_at         TIMESTAMPTZ,
            superseded_by       UUID
                                    REFERENCES %I.source_messages (id),
            is_active           BOOLEAN     NOT NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema, _schema);

    -- ================================================================
    -- 4. 第3階層 FK（親: source_messages）
    -- ================================================================

    -- 4-1. extraction_jobs: 抽出ジョブ（prompt_version: Revision 2 追加列を初回から含む）
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.extraction_jobs (
            id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            source_message_id UUID        NOT NULL
                                              REFERENCES %I.source_messages (id) ON DELETE CASCADE,
            status            VARCHAR(30) NOT NULL,
            extracted_at      TIMESTAMPTZ,
            error_message     TEXT,
            prompt_version    VARCHAR(50),
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    -- ================================================================
    -- 5. 第4階層 FK（親: extraction_jobs）
    -- ================================================================

    -- 5-1. extraction_items: 抽出アイテム
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.extraction_items (
            id                UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            extraction_job_id UUID    NOT NULL
                                          REFERENCES %I.extraction_jobs (id) ON DELETE CASCADE,
            line_start        INTEGER,
            line_end          INTEGER,
            raw_product_name  TEXT,
            raw_quantity      TEXT,
            raw_price         TEXT,
            raw_unit          TEXT,
            raw_state         TEXT,
            raw_memo          TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    -- ================================================================
    -- 6. 第5階層 FK（親: extraction_items / tcg_products / units / conditions）
    -- ================================================================

    -- 6-1. analysis_results: 解析結果（extraction_item_id に UNIQUE 制約）
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_results (
            id                    UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            extraction_item_id    UUID          NOT NULL
                                                    REFERENCES %I.extraction_items (id) ON DELETE CASCADE,
            product_id            UUID
                                      REFERENCES %I.tcg_products (id),
            pid_resolved          BOOLEAN       NOT NULL,
            pid_basis             VARCHAR(100),
            unit_id               UUID
                                      REFERENCES %I.units (id),
            unit_canonical        VARCHAR(50),
            unit_resolved         BOOLEAN       NOT NULL,
            condition_id          UUID
                                      REFERENCES %I.conditions (id),
            condition_canonical   VARCHAR(100),
            condition_basis       VARCHAR(100),
            quantity_normalized   NUMERIC(14,2),
            price_normalized      NUMERIC(14,2),
            note_ja               TEXT,
            status                VARCHAR(50),
            exclusion             TEXT,
            needs_review          BOOLEAN       NOT NULL,
            review_reasons        TEXT,
            engine_version        VARCHAR(50)   NOT NULL,
            computed_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            UNIQUE (extraction_item_id)
        )
    $q$, _schema, _schema, _schema, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_results_needs_review
            ON %I.analysis_results (needs_review)
    $q$, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_results_pid_resolved
            ON %I.analysis_results (pid_resolved)
    $q$, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_results_unit_resolved
            ON %I.analysis_results (unit_resolved)
    $q$, _schema);

    -- 6-2. item_notes: アイテムメモ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.item_notes (
            id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            extraction_item_id UUID        NOT NULL
                                               REFERENCES %I.extraction_items (id) ON DELETE CASCADE,
            note_text          TEXT        NOT NULL,
            note_type          VARCHAR(50),
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_item_notes_extraction_item_id
            ON %I.item_notes (extraction_item_id)
    $q$, _schema);

    -- 6-3. unparsed_lines: 未解析行
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.unparsed_lines (
            id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            extraction_item_id UUID        NOT NULL
                                               REFERENCES %I.extraction_items (id) ON DELETE CASCADE,
            line_text          TEXT        NOT NULL,
            reason             VARCHAR(100),
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    -- ================================================================
    -- 7. Revision 2 追加テーブル: import_jobs（アップロード履歴・冪等化キー）
    -- ================================================================

    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.import_jobs (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            filename         TEXT        NOT NULL,
            raw_sha256       VARCHAR(64) NOT NULL,
            message_count    INTEGER     NOT NULL DEFAULT 0,
            provider_count   INTEGER     NOT NULL DEFAULT 0,
            unresolved_count INTEGER     NOT NULL DEFAULT 0,
            uploaded_by      TEXT,
            status           VARCHAR(30) NOT NULL DEFAULT 'ok',
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_import_jobs_raw_sha256 UNIQUE (raw_sha256)
        )
    $q$, _schema);

    RAISE NOTICE 'migration 20260831_110000: 完了。18テーブルを schema % に作成', _schema;
END $$;
