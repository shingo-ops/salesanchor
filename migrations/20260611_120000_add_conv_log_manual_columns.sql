-- SA-02 Stage 3: conversation_logs に手動記録用カラムを追加
-- 対象ADR: ADR-096
-- 追加内容:
--   deleted_at     TIMESTAMPTZ  NULL — 論理削除（ゴミ箱方式・J3判断）
--   recorded_by_user_id INTEGER NULL — 手動記録者のユーザーID
-- 本番適用条件: CI緑で進行可（ADD COLUMN は非破壊操作・ADR-096 §9）

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
        -- deleted_at（論理削除タイムスタンプ）
        EXECUTE format(
            $q$
            ALTER TABLE %I.conversation_logs
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
            $q$,
            schema_rec.nspname
        );

        -- recorded_by_user_id（手動記録者）
        EXECUTE format(
            $q$
            ALTER TABLE %I.conversation_logs
            ADD COLUMN IF NOT EXISTS recorded_by_user_id INTEGER DEFAULT NULL;
            $q$,
            schema_rec.nspname
        );

        -- deleted_at インデックス（集計フィルタ用）
        EXECUTE format(
            $q$
            CREATE INDEX IF NOT EXISTS idx_conv_logs_deleted_at
            ON %I.conversation_logs (deleted_at)
            WHERE deleted_at IS NOT NULL;
            $q$,
            schema_rec.nspname
        );

        RAISE NOTICE 'SA-02 Stage3 migration applied to schema: %', schema_rec.nspname;
    END LOOP;
END;
$$;
