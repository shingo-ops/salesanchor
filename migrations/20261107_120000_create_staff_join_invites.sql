-- staff-self-registration 1回目: スタッフ招待の表 staff_join_invites を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/staff-self-registration/design.md §3-1（ADR-1068）
-- 招待の状態と、それを一人の人へつなぐ番号だけを持つ。人の正本は public.users と staff のまま。
--   名前・メールは置かない。鍵と登録番号は生の値を保存せず sha256 だけを置く。
-- RLS: 会社別（FOR ALL・FORCE）。形は migrations/20261016_010000_add_google_config_rls.sql:2-9 と同じ。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック: 表は残してプログラムが使わない（表を消すのは別便・PO GO）。

BEGIN;

CREATE TABLE IF NOT EXISTS public.staff_join_invites (
    id                  BIGSERIAL    PRIMARY KEY,
    tenant_id           INTEGER      NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    role_id             INTEGER      NOT NULL,
    created_by          INTEGER      NOT NULL REFERENCES public.users(id),
    token_hash          BYTEA        NOT NULL,
    expires_at          TIMESTAMPTZ  NOT NULL,
    status              TEXT         NOT NULL DEFAULT 'open',
    user_id             INTEGER      NULL REFERENCES public.users(id) ON DELETE SET NULL,
    staff_id            INTEGER      NULL,
    reg_code_hash       BYTEA        NULL,
    reg_code_expires_at TIMESTAMPTZ  NULL,
    discord_channel_id  TEXT         NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    submitted_at        TIMESTAMPTZ  NULL,
    linked_at           TIMESTAMPTZ  NULL,
    revoked_at          TIMESTAMPTZ  NULL,
    CONSTRAINT uq_staff_join_invites_token_hash UNIQUE (token_hash),
    CONSTRAINT uq_staff_join_invites_reg_code_hash UNIQUE (reg_code_hash),
    CONSTRAINT ck_staff_join_invites_token_hash_len CHECK (octet_length(token_hash) = 32),
    CONSTRAINT ck_staff_join_invites_reg_code_hash_len CHECK (reg_code_hash IS NULL OR octet_length(reg_code_hash) = 32),
    CONSTRAINT ck_staff_join_invites_status CHECK (status IN ('open', 'submitted', 'linked', 'revoked'))
);

CREATE INDEX IF NOT EXISTS ix_staff_join_invites_tenant_status_created
    ON public.staff_join_invites (tenant_id, status, created_at DESC);

ALTER TABLE public.staff_join_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staff_join_invites FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS staff_join_invites_tenant ON public.staff_join_invites;
CREATE POLICY staff_join_invites_tenant ON public.staff_join_invites
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

COMMENT ON TABLE public.staff_join_invites IS 'スタッフ自己登録の招待。招待の状態と、一人の人へつなぐ番号だけを持つ。名前・メールは置かない。鍵と登録番号は sha256 だけ保存（ADR-1068）';
COMMENT ON COLUMN public.staff_join_invites.id IS '招待の番号';
COMMENT ON COLUMN public.staff_join_invites.tenant_id IS '会社 tenants.id';
COMMENT ON COLUMN public.staff_join_invites.role_id IS '付ける役割の番号（会社ごとのスキーマの roles.id・外部キーなし）';
COMMENT ON COLUMN public.staff_join_invites.created_by IS '招待を作った人 users.id';
COMMENT ON COLUMN public.staff_join_invites.token_hash IS '招待リンクの鍵の sha256（32 バイト・生の値は保存しない）。作り直すと上書き';
COMMENT ON COLUMN public.staff_join_invites.expires_at IS 'リンクの期限（72 時間）';
COMMENT ON COLUMN public.staff_join_invites.status IS '状態。open＝受付中・submitted＝申込済み・linked＝本人と連携済み・revoked＝取り消し';
COMMENT ON COLUMN public.staff_join_invites.user_id IS '申込で作った users.id（ユーザー削除時は NULL）';
COMMENT ON COLUMN public.staff_join_invites.staff_id IS '申込で作った staff の番号（会社ごとのスキーマ・外部キーなし）';
COMMENT ON COLUMN public.staff_join_invites.reg_code_hash IS '登録番号の sha256（32 バイト・生の値は保存しない）。未発行は NULL';
COMMENT ON COLUMN public.staff_join_invites.reg_code_expires_at IS '登録番号の期限（7 日）';
COMMENT ON COLUMN public.staff_join_invites.discord_channel_id IS 'Discord の個室の番号（2回目で使う・二重の個室を防ぐ）';
COMMENT ON COLUMN public.staff_join_invites.created_at IS '招待を作った時刻';
COMMENT ON COLUMN public.staff_join_invites.submitted_at IS '申込があった時刻';
COMMENT ON COLUMN public.staff_join_invites.linked_at IS '連携が済んだ時刻';
COMMENT ON COLUMN public.staff_join_invites.revoked_at IS '取り消した時刻';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE
            ON public.staff_join_invites TO salesanchor_app;
        GRANT USAGE, SELECT
            ON SEQUENCE public.staff_join_invites_id_seq TO salesanchor_app;
    END IF;
END $$;

COMMIT;
