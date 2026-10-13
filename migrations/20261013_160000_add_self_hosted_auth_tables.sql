-- ADR-1013 便1: ログイン自社化の置き場（構造のみ・冪等・値は入れない）
-- 列名 password_argon2_hash: password_hash は 20260612_150000_drop_password_hash.sql が毎デプロイ消すため使わない
-- RLS は付けない: public.users と同じく、テナントが決まる前（ログイン時）に引くため
-- ロールバック: 列と表は残してコードが使わない（削除は別便・PO GO）

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_argon2_hash TEXT NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ NULL;

COMMENT ON COLUMN public.users.password_argon2_hash IS 'Argon2id のハッシュ文字列。NULL はパスワード未設定（ADR-1013）';
COMMENT ON COLUMN public.users.password_changed_at IS '最後にパスワードを変えた時刻。これより前に発行したトークンを拒否する基準（ADR-1013）';
COMMENT ON COLUMN public.users.failed_login_count IS '連続したログイン失敗の回数。成功で 0（ADR-1013）';
COMMENT ON COLUMN public.users.locked_until IS 'ログイン停止の期限。NULL か過去なら停止なし（ADR-1013）';

CREATE TABLE IF NOT EXISTS public.webauthn_credentials (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    credential_id BYTEA NOT NULL,
    public_key BYTEA NOT NULL,
    sign_count BIGINT NOT NULL DEFAULT 0,
    transports TEXT[] NOT NULL DEFAULT '{}',
    backup_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    backup_state BOOLEAN NOT NULL DEFAULT FALSE,
    aaguid UUID NULL,
    label TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_webauthn_credentials_credential_id UNIQUE (credential_id),
    CONSTRAINT ck_webauthn_credentials_credential_id_len CHECK (octet_length(credential_id) BETWEEN 1 AND 1023),
    CONSTRAINT ck_webauthn_credentials_sign_count CHECK (sign_count >= 0)
);
CREATE INDEX IF NOT EXISTS ix_webauthn_credentials_user_id ON public.webauthn_credentials (user_id);
COMMENT ON TABLE public.webauthn_credentials IS 'パスキーの公開鍵（顔・指紋そのものは端末から出ない）。ADR-1013';
COMMENT ON COLUMN public.webauthn_credentials.user_id IS '人の正本 public.users.id';
COMMENT ON COLUMN public.webauthn_credentials.credential_id IS '認証器が作ったパスキーの ID（W3C は 1023 バイト以下）';
COMMENT ON COLUMN public.webauthn_credentials.public_key IS 'COSE 形式の公開鍵';
COMMENT ON COLUMN public.webauthn_credentials.sign_count IS '署名回数。同期型パスキーは 0 のまま';
COMMENT ON COLUMN public.webauthn_credentials.transports IS '端末との通信方法（usb・nfc・ble・internal・hybrid）';
COMMENT ON COLUMN public.webauthn_credentials.backup_eligible IS 'バックアップ可能なパスキーか';
COMMENT ON COLUMN public.webauthn_credentials.backup_state IS 'いまバックアップされているか';
COMMENT ON COLUMN public.webauthn_credentials.aaguid IS '認証器の種類を表す ID';
COMMENT ON COLUMN public.webauthn_credentials.label IS '利用者が付ける名前';
COMMENT ON COLUMN public.webauthn_credentials.created_at IS '登録した時刻';
COMMENT ON COLUMN public.webauthn_credentials.last_used_at IS '最後にログインに使った時刻';

CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    token_hash BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_password_reset_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_password_reset_tokens_purpose CHECK (purpose IN ('reset', 'invite')),
    CONSTRAINT ck_password_reset_tokens_token_hash_len CHECK (octet_length(token_hash) = 32)
);
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON public.password_reset_tokens (user_id);
COMMENT ON TABLE public.password_reset_tokens IS '再設定リンク（reset・30分）と初回設定リンク（invite・72時間）の使い捨て鍵。ハッシュだけ保存。ADR-1013';
COMMENT ON COLUMN public.password_reset_tokens.user_id IS '人の正本 public.users.id';
COMMENT ON COLUMN public.password_reset_tokens.purpose IS 'reset＝再設定／invite＝新規ユーザーの初回設定';
COMMENT ON COLUMN public.password_reset_tokens.token_hash IS '鍵の sha256（32 バイト）。鍵そのものは保存しない';
COMMENT ON COLUMN public.password_reset_tokens.expires_at IS '期限';
COMMENT ON COLUMN public.password_reset_tokens.used_at IS '使った時刻。NULL は未使用';
COMMENT ON COLUMN public.password_reset_tokens.created_at IS '作った時刻';

CREATE TABLE IF NOT EXISTS public.auth_refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL,
    family_id UUID NOT NULL,
    family_created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NULL,
    user_agent_hash BYTEA NULL,
    CONSTRAINT uq_auth_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_auth_refresh_tokens_token_hash_len CHECK (octet_length(token_hash) = 32)
);
CREATE INDEX IF NOT EXISTS ix_auth_refresh_tokens_user_id ON public.auth_refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_auth_refresh_tokens_family_id ON public.auth_refresh_tokens (family_id);
COMMENT ON TABLE public.auth_refresh_tokens IS 'ログイン継続用の更新トークン。ハッシュだけ保存。使うたびに入れ替え、使い回しを検知したら family ごと失効。ADR-1013';
COMMENT ON COLUMN public.auth_refresh_tokens.user_id IS '人の正本 public.users.id';
COMMENT ON COLUMN public.auth_refresh_tokens.token_hash IS 'トークンの sha256（32 バイト）';
COMMENT ON COLUMN public.auth_refresh_tokens.family_id IS '最初のログインから入れ替わった一連のトークンの組 ID';
COMMENT ON COLUMN public.auth_refresh_tokens.family_created_at IS '組の作成時刻。期限はここから絶対 30 日';
COMMENT ON COLUMN public.auth_refresh_tokens.expires_at IS '期限';
COMMENT ON COLUMN public.auth_refresh_tokens.revoked_at IS '失効した時刻。NULL は有効';
COMMENT ON COLUMN public.auth_refresh_tokens.created_at IS '作った時刻';
COMMENT ON COLUMN public.auth_refresh_tokens.last_used_at IS '最後に使った時刻';
COMMENT ON COLUMN public.auth_refresh_tokens.user_agent_hash IS 'ブラウザ情報の sha256。記録と検知だけに使い、拒否には使わない';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.webauthn_credentials, public.password_reset_tokens, public.auth_refresh_tokens TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.webauthn_credentials_id_seq, public.password_reset_tokens_id_seq, public.auth_refresh_tokens_id_seq TO salesanchor_app;
    END IF;
END $$;
