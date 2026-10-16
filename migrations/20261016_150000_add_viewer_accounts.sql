-- ADR-1019 段1: 閲覧専用アカウントの置き場（構造のみ・冪等・データは入れない）
-- RLS は付けない: テナントを持たない public の表で、ログイン時（テナントが決まる前）に引くため
-- viewer_discord_config は段4で作る（ここでは作らない）
-- ロールバック: 表は残してコードが使わない（削除は別便・PO GO）

CREATE TABLE IF NOT EXISTS public.viewer_accounts (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    line_name TEXT NOT NULL,
    inventory_issue TEXT NULL,
    status TEXT NOT NULL,
    password_argon2_hash TEXT NULL,
    password_must_change BOOLEAN NOT NULL DEFAULT false,
    password_changed_at TIMESTAMPTZ NULL,
    discord_user_id VARCHAR(50) NULL,
    discord_channel_id VARCHAR(32) NULL,
    trial_expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_viewer_accounts_inventory_issue_len CHECK (char_length(inventory_issue) <= 1000),
    CONSTRAINT ck_viewer_accounts_status CHECK (status IN ('pending', 'verified', 'trial', 'active', 'suspended'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_viewer_accounts_email_lower ON public.viewer_accounts (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS uq_viewer_accounts_discord_user_id ON public.viewer_accounts (discord_user_id) WHERE discord_user_id IS NOT NULL;
COMMENT ON TABLE public.viewer_accounts IS '在庫の閲覧専用アカウント（社外のお客さん）。アプリの public.users とは別。ADR-1019';
COMMENT ON COLUMN public.viewer_accounts.email IS '前後の空白を除いて小文字にした値。lower(email) で一意';
COMMENT ON COLUMN public.viewer_accounts.line_name IS 'LINE の表示名';
COMMENT ON COLUMN public.viewer_accounts.inventory_issue IS '在庫関連の課題（自由記述・1000文字まで・任意）';
COMMENT ON COLUMN public.viewer_accounts.status IS 'pending／verified／trial／active／suspended。verified は将来用';
COMMENT ON COLUMN public.viewer_accounts.password_argon2_hash IS 'Argon2id のハッシュ文字列。NULL はパスワード未設定';
COMMENT ON COLUMN public.viewer_accounts.password_must_change IS 'true の間は在庫の表示を拒否し、パスワード変更だけを許す';
COMMENT ON COLUMN public.viewer_accounts.password_changed_at IS '最後にパスワードを変えた時刻。これより前に発行したトークンを拒否する基準';
COMMENT ON COLUMN public.viewer_accounts.discord_user_id IS 'Discord の利用者 ID。1つの Discord アカウントには1人だけ';
COMMENT ON COLUMN public.viewer_accounts.discord_channel_id IS 'その人のチケット部屋';
COMMENT ON COLUMN public.viewer_accounts.trial_expires_at IS 'お試しの期限';
COMMENT ON COLUMN public.viewer_accounts.created_at IS '作った時刻';
COMMENT ON COLUMN public.viewer_accounts.updated_at IS '更新した時刻';

CREATE TABLE IF NOT EXISTS public.viewer_login_tokens (
    id BIGSERIAL PRIMARY KEY,
    viewer_account_id BIGINT NOT NULL REFERENCES public.viewer_accounts(id) ON DELETE CASCADE,
    token_sha256 BYTEA NOT NULL,
    purpose TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_viewer_login_tokens_token_sha256 UNIQUE (token_sha256),
    CONSTRAINT ck_viewer_login_tokens_token_sha256_len CHECK (octet_length(token_sha256) = 32),
    CONSTRAINT ck_viewer_login_tokens_purpose CHECK (purpose IN ('signup_code', 'password_reset'))
);
CREATE INDEX IF NOT EXISTS ix_viewer_login_tokens_viewer_account_id ON public.viewer_login_tokens (viewer_account_id);
COMMENT ON TABLE public.viewer_login_tokens IS '申込コードとパスワード再発行の使い捨て鍵。ハッシュだけ保存。ADR-1019';
COMMENT ON COLUMN public.viewer_login_tokens.viewer_account_id IS '閲覧者 viewer_accounts.id';
COMMENT ON COLUMN public.viewer_login_tokens.token_sha256 IS '鍵の sha256（32 バイト）。鍵そのものは保存しない';
COMMENT ON COLUMN public.viewer_login_tokens.purpose IS 'signup_code＝申込コード／password_reset＝パスワード再発行';
COMMENT ON COLUMN public.viewer_login_tokens.expires_at IS '期限';
COMMENT ON COLUMN public.viewer_login_tokens.created_at IS '作った時刻';

CREATE TABLE IF NOT EXISTS public.viewer_login_events (
    id BIGSERIAL PRIMARY KEY,
    viewer_id BIGINT NOT NULL REFERENCES public.viewer_accounts(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    client_ip VARCHAR(45) NULL,
    user_agent VARCHAR(500) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_viewer_login_events_event_type CHECK (event_type IN (
        'login_succeeded', 'login_failed', 'password_changed', 'password_reset_requested',
        'password_reset_done', 'signup', 'code_matched'
    ))
);
CREATE INDEX IF NOT EXISTS ix_viewer_login_events_viewer_id ON public.viewer_login_events (viewer_id);
CREATE INDEX IF NOT EXISTS ix_viewer_login_events_created_at ON public.viewer_login_events (created_at);
COMMENT ON TABLE public.viewer_login_events IS '閲覧者のログイン記録（いつ・誰が・どの IP から）。90日で消す。ADR-1019';
COMMENT ON COLUMN public.viewer_login_events.viewer_id IS '閲覧者 viewer_accounts.id';
COMMENT ON COLUMN public.viewer_login_events.event_type IS 'login_succeeded／login_failed／password_changed／password_reset_requested／password_reset_done／signup／code_matched';
COMMENT ON COLUMN public.viewer_login_events.client_ip IS 'クライアント IP（IPv6 対応）。code_matched は NULL';
COMMENT ON COLUMN public.viewer_login_events.user_agent IS 'User-Agent（先頭500文字）。code_matched は NULL';
COMMENT ON COLUMN public.viewer_login_events.created_at IS '記録した時刻（90日で消すため索引あり）';

CREATE TABLE IF NOT EXISTS public.viewer_status_changes (
    id BIGSERIAL PRIMARY KEY,
    viewer_id BIGINT NOT NULL REFERENCES public.viewer_accounts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    from_status TEXT NULL,
    to_status TEXT NULL,
    from_expires_at TIMESTAMPTZ NULL,
    to_expires_at TIMESTAMPTZ NULL,
    extend_days INTEGER NULL,
    actor TEXT NOT NULL,
    actor_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_viewer_status_changes_action CHECK (action IN ('activate', 'suspend', 'unsuspend', 'extend', 'start_trial')),
    CONSTRAINT ck_viewer_status_changes_actor CHECK (actor IN ('po', 'claude', 'system'))
);
CREATE INDEX IF NOT EXISTS ix_viewer_status_changes_viewer_id ON public.viewer_status_changes (viewer_id);
COMMENT ON TABLE public.viewer_status_changes IS '閲覧者の状態・期限を変えた履歴。ADR-1019';
COMMENT ON COLUMN public.viewer_status_changes.viewer_id IS '閲覧者 viewer_accounts.id';
COMMENT ON COLUMN public.viewer_status_changes.action IS 'activate／suspend／unsuspend／extend／start_trial';
COMMENT ON COLUMN public.viewer_status_changes.from_status IS '変更前の状態';
COMMENT ON COLUMN public.viewer_status_changes.to_status IS '変更後の状態';
COMMENT ON COLUMN public.viewer_status_changes.from_expires_at IS '変更前の期限';
COMMENT ON COLUMN public.viewer_status_changes.to_expires_at IS '変更後の期限';
COMMENT ON COLUMN public.viewer_status_changes.extend_days IS '延長した日数（extend のとき）';
COMMENT ON COLUMN public.viewer_status_changes.actor IS '操作した主体：po／claude／system';
COMMENT ON COLUMN public.viewer_status_changes.actor_user_id IS '操作した社員 public.users.id（system は NULL）';
COMMENT ON COLUMN public.viewer_status_changes.created_at IS '記録した時刻';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.viewer_accounts, public.viewer_login_tokens, public.viewer_login_events, public.viewer_status_changes TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.viewer_accounts_id_seq, public.viewer_login_tokens_id_seq, public.viewer_login_events_id_seq, public.viewer_status_changes_id_seq TO salesanchor_app;
    END IF;
END $$;
