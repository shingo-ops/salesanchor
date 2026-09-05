-- Migration: 20260906_100000_create_tcg_tables_t006
--
-- 目的: tenant_006 スキーマに TCG 解析パイプライン全テーブル（27 本）を作成し、
--       QA に必要な最小限のマスタ（分類 4 テーブル + テスト仕入元 3 件）を seed する。
--
-- 設計判断:
--   - 1 本に集約: t006 はすべてのテーブルが存在しないため、
--     _t004 の ALTER TABLE 列追加を最終形として CREATE TABLE に内包できる。
--     複数ファイルの実行順依存を管理するより安全。
--   - 既存 _t004 ファイルには一切触らない（本番適用済みのため）。
--   - スキーマ名を _schema 変数化 + %I で管理（_t004 と同じ作法）。
--   - tcg_products: FK 制約（division/work/manufacturer/product_category）は
--     分類 4 テーブルを先に作成しているため、CREATE TABLE 時点から宣言。
--
-- 冪等性: CREATE SCHEMA IF NOT EXISTS / CREATE TABLE IF NOT EXISTS / ON CONFLICT DO NOTHING
--
-- _t004 との差異:
--   - スキーマ: tenant_006（tenant_004 には一切影響なし）
--   - seed データ: 分類マスタのみ（_t004 の 268 商品・60 仕入元はコピーしない）
--   - テスト仕入元: SP9001/SP9002/SP9003 + LINE チャンネル各 1 件
--
-- 作成日: 2026-09-06

DO $$
DECLARE
    _schema TEXT := 'tenant_006';
BEGIN

    -- ================================================================
    -- 0. スキーマ作成
    -- ================================================================
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', _schema);
    RAISE NOTICE '20260906_100000: schema % created (or already existed)', _schema;

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
        CREATE INDEX IF NOT EXISTS ix_audit_log_changed_at ON %I.audit_log (changed_at)
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_audit_log_table_record ON %I.audit_log (table_name, record_id)
    $q$, _schema);

    -- 1-2. conditions: コンディションマスタ（最終形: priority/search_kw/exclude_kw を含む）
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.conditions (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code        VARCHAR(20) NOT NULL,
            canonical   TEXT        NOT NULL,
            app_kubun   VARCHAR(50),
            is_active   BOOLEAN     NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            priority    INTEGER,
            search_kw   TEXT        NOT NULL DEFAULT '',
            exclude_kw  TEXT        NOT NULL DEFAULT '',
            UNIQUE (code)
        )
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS idx_conditions_priority
            ON %I.conditions (priority ASC NULLS LAST)
    $q$, _schema);

    -- 1-3. 分類マスタ 4 テーブル（tcg_products の FK に必要なため先に作成）

    -- tcg_major_categories: 大分類マスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_major_categories (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            description  TEXT,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- tcg_series: 作品マスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_series (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            alt_name     TEXT,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- tcg_manufacturers: メーカーマスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_manufacturers (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            alt_name     TEXT,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- tcg_product_categories: 商品区分マスタ
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_product_categories (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            kubun_type   VARCHAR(50) NOT NULL,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- 1-4. tcg_products: TCG商品マスタ（最終形: mark/english_title + FK 制約を含む）
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_products (
            id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code                  VARCHAR(20) NOT NULL,
            japanese_title        TEXT        NOT NULL,
            release_date          DATE,
            category_class        TEXT        NOT NULL,
            division_id           UUID        REFERENCES %I.tcg_major_categories (id),
            work_id               UUID        REFERENCES %I.tcg_series (id),
            manufacturer_id       UUID        REFERENCES %I.tcg_manufacturers (id),
            product_category_id   UUID        REFERENCES %I.tcg_product_categories (id),
            required_output_value TEXT,
            is_active             BOOLEAN     NOT NULL,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            mark                  VARCHAR,
            english_title         VARCHAR,
            UNIQUE (code)
        )
    $q$, _schema, _schema, _schema, _schema, _schema);

    -- 1-5. tcg_suppliers: 仕入先マスタ
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

    -- 1-6. units: 単位マスタ
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

    -- 1-7. import_jobs: アップロード履歴（最終形: review_stage 列を含む）
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
            pending_messages JSONB,
            window_start     TIMESTAMPTZ,
            window_end       TIMESTAMPTZ,
            unresolved_names JSONB,
            review_status    TEXT        NOT NULL DEFAULT 'ok',
            CONSTRAINT uq_import_jobs_raw_sha256 UNIQUE (raw_sha256)
        )
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_import_jobs_review_status
            ON %I.import_jobs (review_status)
            WHERE review_status = 'pending_review'
    $q$, _schema);

    -- 1-8. item_corrections: 修正履歴テーブル（FK 制約なし・参照先が別スキーマのため）
    EXECUTE format($q$
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
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS idx_item_corrections_extraction_item_id
            ON %I.item_corrections (extraction_item_id)
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS idx_item_corrections_corrected_at
            ON %I.item_corrections (corrected_at DESC)
    $q$, _schema);

    -- 1-9. tcg_distribution_targets: 配信先マスタ
    EXECUTE format($q$
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
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS idx_dist_targets_is_active
            ON %I.tcg_distribution_targets (is_active)
    $q$, _schema);

    -- 1-10. tcg_distribution_settings: 配信全体設定
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_distribution_settings (
            key        TEXT         PRIMARY KEY,
            value      TEXT         NOT NULL,
            note       TEXT,
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- ================================================================
    -- 2. 第1階層 FK（親: conditions / tcg_products / tcg_suppliers / units）
    -- ================================================================

    -- 2-1. condition_aliases
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

    -- 2-2. product_exclude_keywords
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

    -- 2-3. product_search_keywords
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

    -- 2-4. products_logistics
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.products_logistics (
            product_id UUID NOT NULL
                                REFERENCES %I.tcg_products (id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (product_id)
        )
    $q$, _schema, _schema);

    -- 2-5. supplier_channels
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

    -- 2-6. unit_aliases
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
        CREATE INDEX IF NOT EXISTS ix_unit_aliases_unit_id ON %I.unit_aliases (unit_id)
    $q$, _schema);

    -- ================================================================
    -- 3. 第2階層 FK（親: supplier_channels）
    -- ================================================================

    -- 3-1. source_messages（自己参照 FK: superseded_by）
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

    -- 4-1. extraction_jobs
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

    -- 5-1. extraction_items
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

    -- 6-1. analysis_results（最終形: unit_inferred/unit_basis/unit_confidence/unit_infer_reason を含む）
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
            unit_inferred         TEXT          NOT NULL DEFAULT '',
            unit_basis            TEXT          NOT NULL DEFAULT '',
            unit_confidence       TEXT          NOT NULL DEFAULT '',
            unit_infer_reason     TEXT          NOT NULL DEFAULT '',
            UNIQUE (extraction_item_id)
        )
    $q$, _schema, _schema, _schema, _schema, _schema, _schema);
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
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS idx_analysis_results_unit_basis
            ON %I.analysis_results (unit_basis)
            WHERE unit_basis != ''
    $q$, _schema);

    -- 6-2. item_notes
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

    -- 6-3. unparsed_lines
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
    -- 7. 再解析履歴テーブル（親: extraction_jobs / analysis_runs）
    -- ================================================================

    -- 7-1. analysis_runs
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_runs (
            id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            extraction_job_id UUID         NOT NULL
                                               REFERENCES %I.extraction_jobs (id) ON DELETE CASCADE,
            run_type          VARCHAR(50)  NOT NULL,
            triggered_by      VARCHAR(100),
            engine_version    VARCHAR(50)  NOT NULL,
            started_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            completed_at      TIMESTAMPTZ,
            total             INTEGER,
            pid_resolved      INTEGER,
            unit_resolved     INTEGER,
            needs_review      INTEGER,
            multi_count       INTEGER,
            none_count        INTEGER
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_runs_extraction_job_id
            ON %I.analysis_runs (extraction_job_id)
    $q$, _schema);

    -- 7-2. analysis_run_snapshots（analysis_result_id は UUID 参照のみ・非 FK）
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_run_snapshots (
            id                    UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id                UUID          NOT NULL
                                                    REFERENCES %I.analysis_runs (id) ON DELETE CASCADE,
            analysis_result_id    UUID          NOT NULL,
            extraction_item_id    UUID          NOT NULL,
            product_id            UUID,
            pid_resolved          BOOLEAN       NOT NULL,
            pid_basis             VARCHAR(100),
            unit_id               UUID,
            unit_canonical        VARCHAR(50),
            unit_resolved         BOOLEAN       NOT NULL,
            condition_id          UUID,
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
            computed_at           TIMESTAMPTZ   NOT NULL,
            updated_at            TIMESTAMPTZ   NOT NULL,
            snapshotted_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_run_snapshots_run_id
            ON %I.analysis_run_snapshots (run_id)
    $q$, _schema);

    RAISE NOTICE '20260906_100000: 27 テーブル作成完了 (schema %)', _schema;

    -- ================================================================
    -- 8. Seed: 分類マスタ（FK 参照に必要な最小限）
    -- ================================================================

    EXECUTE format($q$
        INSERT INTO %I.tcg_major_categories (code, display_name, description) VALUES
            ('DIV01', 'TCG',    'トレーディングカード'),
            ('DIV02', 'Figure', 'フィギュア'),
            ('DIV03', 'Goods',  'グッズ・雑貨')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        INSERT INTO %I.tcg_series (code, display_name, alt_name) VALUES
            ('IP001', 'Pokemon',       'ポケモン'),
            ('IP002', 'One Piece',     'ワンピース'),
            ('IP003', 'Dragon Ball',   'ドラゴンボール'),
            ('IP004', 'Yu-Gi-Oh',      '遊戯王'),
            ('IP005', 'Union Arena',   'ユニオンアリーナ'),
            ('IP006', 'GUNDAM',        'ガンダム'),
            ('IP007', 'Weiss Schwarz', 'Weiss Shwarz'),
            ('IP008', 'Digimon',       'デジモン'),
            ('IP009', 'hololive',      'ホロライブ'),
            ('IP010', 'LORCANA',       'ロルカナ'),
            ('IP011', 'Xross Stars',   'クロススターズ')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        INSERT INTO %I.tcg_manufacturers (code, display_name, alt_name) VALUES
            ('MK001', 'The Pokemon Company', 'ポケモン'),
            ('MK002', 'Bandai',              'バンダイ'),
            ('MK003', 'Takara Tomy',         'タカラトミー'),
            ('MK004', 'Bushiroad',           'ブシロード'),
            ('MK005', 'Konami',              'コナミ')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        INSERT INTO %I.tcg_product_categories (code, display_name, kubun_type) VALUES
            ('PC_BOX',    'Box',    '箱系'),
            ('PC_SINGLE', 'Single', 'シングル系')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    RAISE NOTICE '20260906_100000: 分類マスタ seed 完了（tcg_major_categories:3 / tcg_series:11 / tcg_manufacturers:5 / tcg_product_categories:2）';

    -- ================================================================
    -- 9. Seed: テスト仕入元 3 件 + LINE チャンネル（QA 専用）
    -- ================================================================

    EXECUTE format($q$
        INSERT INTO %I.tcg_suppliers (code, name, is_active) VALUES
            ('SP9001', 'QAテスト仕入元A', TRUE),
            ('SP9002', 'QAテスト仕入元B', TRUE),
            ('SP9003', 'QAテスト仕入元C', TRUE)
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        INSERT INTO %I.supplier_channels (supplier_id, channel, external_id, is_active)
        SELECT s.id, 'line', NULL, TRUE
        FROM   %I.tcg_suppliers s
        WHERE  s.code IN ('SP9001', 'SP9002', 'SP9003')
          AND  NOT EXISTS (
              SELECT 1 FROM %I.supplier_channels sc
              WHERE  sc.supplier_id = s.id
                AND  sc.channel     = 'line'
                AND  sc.external_id IS NULL
          )
    $q$, _schema, _schema, _schema);

    RAISE NOTICE '20260906_100000: テスト仕入元 seed 完了（SP9001/SP9002/SP9003 + LINE チャンネル各 1 件）';

    -- ================================================================
    -- 10. 検算: tenant_006 のテーブル一覧を出力
    --
    --     期待するテーブル一覧（27 本）:
    --       analysis_results, analysis_run_snapshots, analysis_runs,
    --       audit_log, condition_aliases, conditions,
    --       extraction_items, extraction_jobs,
    --       import_jobs, item_corrections, item_notes,
    --       product_exclude_keywords, product_search_keywords, products_logistics,
    --       source_messages, supplier_channels,
    --       tcg_distribution_settings, tcg_distribution_targets,
    --       tcg_major_categories, tcg_manufacturers, tcg_product_categories,
    --       tcg_products, tcg_series, tcg_suppliers,
    --       unit_aliases, units, unparsed_lines
    -- ================================================================
    DECLARE
        _table_count INTEGER;
    BEGIN
        SELECT COUNT(*) INTO _table_count
        FROM information_schema.tables
        WHERE table_schema = _schema
          AND table_type   = 'BASE TABLE'
          AND table_name IN (
              'analysis_results', 'analysis_run_snapshots', 'analysis_runs',
              'audit_log', 'condition_aliases', 'conditions',
              'extraction_items', 'extraction_jobs',
              'import_jobs', 'item_corrections', 'item_notes',
              'product_exclude_keywords', 'product_search_keywords', 'products_logistics',
              'source_messages', 'supplier_channels',
              'tcg_distribution_settings', 'tcg_distribution_targets',
              'tcg_major_categories', 'tcg_manufacturers', 'tcg_product_categories',
              'tcg_products', 'tcg_series', 'tcg_suppliers',
              'unit_aliases', 'units', 'unparsed_lines'
          );

        RAISE NOTICE '20260906_100000: schema % TCG テーブル数 = % (期待値: 27)', _schema, _table_count;

        IF _table_count <> 27 THEN
            RAISE EXCEPTION '20260906_100000: テーブル数が 27 ではありません: %', _table_count;
        END IF;
    END;

    RAISE NOTICE '20260906_100000: 完了。schema % に 27 テーブル作成・seed 完了', _schema;
END $$;
