-- テナント削除操作の中央監査ログテーブル新設
-- public スキーマに配置するため DROP SCHEMA 後も記録が残る
CREATE TABLE IF NOT EXISTS public.tenant_deletion_audit (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL,
    tenant_code     TEXT NOT NULL,
    tenant_name     TEXT NOT NULL,
    mode            TEXT NOT NULL CHECK (mode IN ('logical', 'physical')),
    status          TEXT NOT NULL CHECK (status IN ('started', 'succeeded', 'failed')),
    actor_id        INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    actor_email     TEXT NOT NULL,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    meta            JSONB
);
