-- ============================================================================
-- Migration 20261007_100000: 実行済み記録（ledger）の表 ops.migration_ledger（ADR-1005 段階2）
--
-- 目的:
--   scripts/run_all_migrations.sh が「どの手順を実行したか」を DB に記録し、
--   まだ記録されていない手順だけを 1 回実行するための表。構造だけの migration（値は入れない）。
--
-- 置き場所を専用スキーマ ops にする理由:
--   public に作ると、salesanchor_app に SELECT/INSERT/UPDATE/DELETE が自動で付く
--   （migrations/20260605_030000_create_salesanchor_app_role.sql:21-22
--     ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public GRANT ... TO salesanchor_app）。
--   アプリのロールが記録を書き換えられる状態は避けたい。ops スキーマにはその設定が無く、
--   スキーマの USAGE も付かないので、アプリのロールは触れない。以下で、明示的に取り消しもする。
--   ops は tenant_NNN の走査（nspname ~ '^tenant_\d+$'）にも入らない。
--
-- 冪等: CREATE ... IF NOT EXISTS、REVOKE は何度流しても同じ。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.migration_ledger (
    id          BIGSERIAL    PRIMARY KEY,
    scope       TEXT         NOT NULL DEFAULT 'public',
    kind        TEXT         NOT NULL CHECK (kind IN ('sql', 'py')),
    filename    TEXT         NOT NULL,
    checksum    TEXT         NOT NULL,
    status      TEXT         NOT NULL CHECK (status IN ('applied', 'baseline')),
    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    duration_ms INTEGER,
    git_sha     TEXT,
    CONSTRAINT migration_ledger_scope_filename_key UNIQUE (scope, filename)
);

COMMENT ON TABLE ops.migration_ledger IS
    '実行済みの migration の記録（ADR-1005 段階2）。scope=public の行は run_all_migrations.sh が書く。status=baseline は「実行せずに記録だけ入れた」行。';
COMMENT ON COLUMN ops.migration_ledger.checksum IS
    'ファイル内容の sha256（改行は LF に正規化）。実行済みファイルの書き換えを検出する。';

-- アプリのロールに触らせない（public のデフォルト権限が及ばないことを、明示で保証する）
REVOKE ALL ON SCHEMA ops FROM PUBLIC;
REVOKE ALL ON TABLE ops.migration_ledger FROM PUBLIC;
REVOKE ALL ON SEQUENCE ops.migration_ledger_id_seq FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        REVOKE ALL ON SCHEMA ops FROM salesanchor_app;
        REVOKE ALL ON TABLE ops.migration_ledger FROM salesanchor_app;
        REVOKE ALL ON SEQUENCE ops.migration_ledger_id_seq FROM salesanchor_app;
    END IF;
END $$;

-- ============================================================================
-- Rollback（緊急時のみ手動。記録を消すと、次のデプロイで全件が実行される）:
--   ops.migration_ledger を削除する文と、ops スキーマを削除する文を、この順で実行する。
-- ============================================================================
