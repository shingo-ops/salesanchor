-- ============================================================================
-- Migration 20261001_120000: staff テーブルに avatar_token カラム追加
--
-- 目的:
--   担当者アイコン画像（ADR-159 便A）の公開 URL 用 token を保持する。
--   画像実体は ATTACHMENT_ROOT/staff_avatars/<token>.webp。DB は token のみを持つ。
--
-- 設計判断:
--   - additive-only: NULL 可・既存行の backfill 不要（NULL = アイコン未登録）
--   - token は secrets.token_urlsafe(32)（アプリが生成。推測不能）
--   - インデックスなし: 公開ルートは DB を参照しない（token → ファイルのみ）
--
-- 冪等性:
--   DO block で pg_namespace 走査して全 tenant_NNN schema に適用。
--   ADD COLUMN IF NOT EXISTS で再実行可能。
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
        -- staff テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'staff'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.staff ADD COLUMN IF NOT EXISTS avatar_token TEXT',
            schema_rec.nspname
        );

        EXECUTE format(
            $q$COMMENT ON COLUMN %I.staff.avatar_token IS '担当者アイコン画像の公開 URL token（NULL=未登録・ADR-159）'$q$,
            schema_rec.nspname
        );
    END LOOP;
END;
$$;
