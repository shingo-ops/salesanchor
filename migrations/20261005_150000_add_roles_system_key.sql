-- ============================================================================
-- Migration 20261005_150000: roles に system_key 列（owner / admin の安定識別子）を追加
--
-- 目的:
--   オーナー / システム管理者の権限を、役割の表示名ではなく安定した識別子で判定できるようにする
--   （ADR-1006 とは別件。権限を check 時に計算する方針の前段。構造変更のみ）。
--
-- 設計判断:
--   - additive-only: NULL 可・既存行の backfill はしない（値の設定は別手順で一度だけ行う）
--   - 値の操作は含まない（ADR-155: マイグレーションは構造変更のみ）
--   - 部分一意索引: system_key が NULL でない行だけ、テナント内で一意
--
-- 冪等性:
--   DO block で pg_namespace を走査して全 tenant_NNN schema に適用。
--   ADD COLUMN IF NOT EXISTS / CREATE UNIQUE INDEX IF NOT EXISTS で再実行可能。
--   参考: migrations/20261001_120000_add_staff_avatar_token.sql
-- ============================================================================

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- roles テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'roles'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.roles ADD COLUMN IF NOT EXISTS system_key TEXT',
            schema_rec.nspname
        );

        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_system_key ON %I.roles (system_key) WHERE system_key IS NOT NULL',
            schema_rec.nspname
        );

        EXECUTE format(
            $q$COMMENT ON COLUMN %I.roles.system_key IS 'システムロールの安定識別子（owner / admin。通常ロールは NULL）'$q$,
            schema_rec.nspname
        );
    END LOOP;
END;
$$;
