-- ADR-110: 翻訳サブシステム — グロッサリ + 確信度 + 送信下訳
--
-- 変更内容:
--   1. public.translation_glossary テーブル作成（テナント共通ベース + テナント追加）
--   2. {schema}.message_translations に confidence / original_language 列追加（ADR-088 拡張）
--   3. {schema}.outbound_translation_drafts テーブル作成（送信下訳 + 人確認管理）
--
-- 冪等: CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
-- 適用: 全テナントスキーマ（pg_namespace 走査）
-- 作成日: 2026-06-04

-- ==========================================================================
-- 1. public.translation_glossary（グロッサリ: 全テナント共有ベース + テナント追加）
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.translation_glossary (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER,                        -- NULL = 全テナント共有
    source_term         TEXT NOT NULL,                  -- 翻訳前の語
    target_text         TEXT,                           -- NULL = 「訳さない」（原語保持）
    language_pair       VARCHAR(20) NOT NULL DEFAULT 'en->ja',
    term_type           VARCHAR(30) NOT NULL DEFAULT 'general',
        -- 'product_name' | 'brand' | 'grade' | 'abbreviation' | 'jargon' | 'general'
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    source_ref          VARCHAR(50),                    -- 'product_master' = 自動 seed
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_translation_glossary UNIQUE (tenant_id, source_term, language_pair)
);

CREATE INDEX IF NOT EXISTS idx_translation_glossary_tenant
    ON public.translation_glossary (tenant_id);

CREATE INDEX IF NOT EXISTS idx_translation_glossary_lang_pair
    ON public.translation_glossary (language_pair, is_active);

CREATE INDEX IF NOT EXISTS idx_translation_glossary_source_term
    ON public.translation_glossary (lower(source_term));

-- ==========================================================================
-- 2. {schema}.message_translations 拡張（confidence / original_language 追加）
-- ==========================================================================

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- confidence 列追加（既存なら no-op）
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.nspname
              AND table_name   = 'message_translations'
              AND column_name  = 'confidence'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.message_translations ADD COLUMN confidence REAL',
                schema_rec.nspname
            );
            RAISE NOTICE 'migration 20260604_220000: %.message_translations.confidence 追加', schema_rec.nspname;
        END IF;

        -- original_language 列追加
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.nspname
              AND table_name   = 'message_translations'
              AND column_name  = 'original_language'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.message_translations ADD COLUMN original_language VARCHAR(10)',
                schema_rec.nspname
            );
            RAISE NOTICE 'migration 20260604_220000: %.message_translations.original_language 追加', schema_rec.nspname;
        END IF;
    END LOOP;
END
$$;

-- ==========================================================================
-- 3. {schema}.outbound_translation_drafts（送信下訳 + 人確認状態管理）
-- ==========================================================================

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        EXECUTE format($q$
            CREATE TABLE IF NOT EXISTS %I.outbound_translation_drafts (
                id              SERIAL PRIMARY KEY,
                tenant_id       INTEGER NOT NULL,
                lead_id         INTEGER,
                original_text   TEXT NOT NULL,       -- 担当者の日本語下書き
                draft_text      TEXT NOT NULL,       -- AI 生成英訳下訳
                confidence      REAL,                -- 0.0–1.0
                flagged_terms   JSONB,               -- [{term, reason}]
                model           VARCHAR(50) NOT NULL,
                confirmed_at    TIMESTAMPTZ,         -- NULL = 未確認
                final_text      TEXT,                -- 人が編集した最終テキスト
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        $q$, schema_rec.nspname);

        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_outbound_drafts_tenant_lead
             ON %I.outbound_translation_drafts (tenant_id, lead_id)',
            schema_rec.nspname
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_outbound_drafts_unconfirmed
             ON %I.outbound_translation_drafts (tenant_id, confirmed_at)
             WHERE confirmed_at IS NULL',
            schema_rec.nspname
        );

        RAISE NOTICE 'migration 20260604_220000: %.outbound_translation_drafts 作成', schema_rec.nspname;
    END LOOP;
END
$$;

-- ==========================================================================
-- 4. tenant_llm_budgets に翻訳監視デバウンス列追加
-- ==========================================================================

ALTER TABLE public.tenant_llm_budgets
    ADD COLUMN IF NOT EXISTS last_translation_monitor_notified_at TIMESTAMPTZ;
