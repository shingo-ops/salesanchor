-- SA-02 Stage 2 前提: conversation_logs に is_manual カラムを追加
-- 対象ADR: ADR-096
-- 追加内容:
--   is_manual  BOOLEAN  NULL — 自動取り込み行=false、手動記録=true、未分類=NULL
--
-- 背景:
--   20260604_090000_create_conversation_logs.sql で is_manual が未定義のまま本番適用された。
--   Stage 2 移行スクリプト（migrate_sa02_stage2_meta_to_conv_logs.py）が
--   is_manual=false で INSERT するため、このカラムが必要。
--
-- 本番適用条件: CI緑で進行可（ADD COLUMN は非破壊操作）

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
        -- テーブルが存在しない場合はスキップ（冪等性確保）
        IF to_regclass(schema_rec.nspname || '.conversation_logs') IS NULL THEN
            CONTINUE;
        END IF;

        -- is_manual（自動/手動区別フラグ）
        EXECUTE format(
            $q$
            ALTER TABLE %I.conversation_logs
            ADD COLUMN IF NOT EXISTS is_manual BOOLEAN DEFAULT NULL;
            $q$,
            schema_rec.nspname
        );

        RAISE NOTICE 'SA-02 Stage2 pre-migration: is_manual added to %.conversation_logs', schema_rec.nspname;
    END LOOP;
END;
$$;
