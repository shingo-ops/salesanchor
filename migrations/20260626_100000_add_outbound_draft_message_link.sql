-- Migration: 20260626_100000
-- outbound_translation_drafts に送信メッセージ紐付け＋is_edited 列を追加（段階A: outbound翻訳修正）
--
-- 目的:
--   送信した meta_messages.id と翻訳下書きを紐付け、
--   人が英訳を手直ししたか（is_edited）を自動記録する基盤を作る。
--   将来の RAG 学習（段階B）の入力データとして利用。
--
-- 冪等: ADD COLUMN IF NOT EXISTS
-- 影響: {tenant_NNN}.outbound_translation_drafts（追加のみ）
-- 既存行: NULL のまま（機能導入前のため backfill 不要）
-- 作成日: 2026-06-26

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- テーブル不在スキーマはスキップ
        CONTINUE WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.nspname
              AND table_name   = 'outbound_translation_drafts'
        );

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.nspname
              AND table_name   = 'outbound_translation_drafts'
              AND column_name  = 'meta_message_id'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.outbound_translation_drafts ADD COLUMN meta_message_id INTEGER',
                schema_rec.nspname
            );
            RAISE NOTICE 'migration 20260626_100000: %.outbound_translation_drafts.meta_message_id 追加', schema_rec.nspname;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.nspname
              AND table_name   = 'outbound_translation_drafts'
              AND column_name  = 'is_edited'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.outbound_translation_drafts ADD COLUMN is_edited BOOLEAN',
                schema_rec.nspname
            );
            RAISE NOTICE 'migration 20260626_100000: %.outbound_translation_drafts.is_edited 追加', schema_rec.nspname;
        END IF;
    END LOOP;
END
$$;
