-- ============================================================================
-- Migration: 20260622_010000
-- meta_messages に master 統合用の履歴列を追加する（追加のみ）
--
-- 目的:
--   conversation_logs が持つ履歴 / 業務文脈の列を meta_messages に追加し、
--   後続の SSOT 統合で master テーブルとして育てる。
--
-- 方針:
--   - 既存列・既存データ・制約・RLS は変更しない
--   - すべて NULL 許容、IF NOT EXISTS で冪等
--   - index は追加しない
--   - 型は conversation_logs の実 DDL と一致させる
-- ============================================================================

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname
        FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        IF to_regclass(schema_rec.nspname || '.meta_messages') IS NULL THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            $q$
            ALTER TABLE %I.meta_messages
                ADD COLUMN IF NOT EXISTS contact_id          INTEGER,
                ADD COLUMN IF NOT EXISTS company_id          INTEGER,
                ADD COLUMN IF NOT EXISTS deal_id             INTEGER,
                ADD COLUMN IF NOT EXISTS channel_identity    VARCHAR(255),
                ADD COLUMN IF NOT EXISTS original_language   VARCHAR(10),
                ADD COLUMN IF NOT EXISTS status              VARCHAR(20) DEFAULT 'sent',
                ADD COLUMN IF NOT EXISTS analysis            JSONB,
                ADD COLUMN IF NOT EXISTS occurred_at         TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS deleted_at          TIMESTAMPTZ DEFAULT NULL,
                ADD COLUMN IF NOT EXISTS recorded_by_user_id INTEGER DEFAULT NULL,
                ADD COLUMN IF NOT EXISTS is_manual           BOOLEAN DEFAULT NULL
            $q$,
            schema_rec.nspname
        );

        RAISE NOTICE 'migration 20260622_010000: %.meta_messages master columns added', schema_rec.nspname;
    END LOOP;
END
$$;
