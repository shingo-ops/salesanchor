-- ADR-1055 段A: 知らない機械からのログインを、いつもの機械で許可するまで止める仕組みの置き場
-- 追加のみ・冪等・値は入れない。RLS は付けない（ADR-1018 Decision 6 の認証トークン3表と同じ理由:
--   ログイン前・会社が決まる前に、印や依頼の hash の一致で1行を引くため。生の値は保存せず hash だけを置き、本人の行は user_id で絞る）
-- ロールバック: 表と列は残してコードが使わない（削除は別便・PO 判断）

CREATE TABLE IF NOT EXISTS public.user_trusted_devices (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL,
    label VARCHAR(100) NULL,
    user_agent VARCHAR(500) NULL,
    created_via VARCHAR(20) NOT NULL,
    created_ip VARCHAR(45) NULL,
    created_location VARCHAR(200) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NULL,
    last_ip VARCHAR(45) NULL,
    last_location VARCHAR(200) NULL,
    revoked_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_user_trusted_devices_user_token UNIQUE (user_id, token_hash),
    CONSTRAINT ck_user_trusted_devices_created_via CHECK (
        created_via IN ('bootstrap', 'first_login', 'passkey', 'device_approval', 'recovery_code', 'admin_approval', 'cli')
    )
);
CREATE INDEX IF NOT EXISTS ix_user_trusted_devices_user_id ON public.user_trusted_devices (user_id);
COMMENT ON TABLE public.user_trusted_devices IS 'いつもの機械の印（Cookie sa_device）。ハッシュだけ保存。ADR-1055';
COMMENT ON COLUMN public.user_trusted_devices.id IS '機械の ID';
COMMENT ON COLUMN public.user_trusted_devices.user_id IS '人の正本 public.users.id。1つの印を複数の人が使える';
COMMENT ON COLUMN public.user_trusted_devices.token_hash IS '印の sha256（32 バイト）。印そのものは保存しない';
COMMENT ON COLUMN public.user_trusted_devices.label IS '機械の呼び名（管理用の命令で付ける）';
COMMENT ON COLUMN public.user_trusted_devices.user_agent IS '登録したときのブラウザ情報';
COMMENT ON COLUMN public.user_trusted_devices.created_via IS '登録の経路（bootstrap・first_login・passkey・device_approval・recovery_code・admin_approval・cli）';
COMMENT ON COLUMN public.user_trusted_devices.created_ip IS '登録したときの IP';
COMMENT ON COLUMN public.user_trusted_devices.created_location IS '登録したときの場所の目安（IP から引く）';
COMMENT ON COLUMN public.user_trusted_devices.created_at IS '登録した時刻';
COMMENT ON COLUMN public.user_trusted_devices.last_used_at IS '最後に使った時刻。180日使わないと失効扱い';
COMMENT ON COLUMN public.user_trusted_devices.last_ip IS '最後に使ったときの IP';
COMMENT ON COLUMN public.user_trusted_devices.last_location IS '最後に使ったときの場所の目安';
COMMENT ON COLUMN public.user_trusted_devices.revoked_at IS '取り消した時刻。NULL は有効';

CREATE TABLE IF NOT EXISTS public.auth_login_requests (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    match_number CHAR(2) NOT NULL,
    candidates VARCHAR(8) NOT NULL,
    pending_token_hash BYTEA NOT NULL,
    device_token_hash BYTEA NULL,
    label VARCHAR(100) NULL,
    user_agent VARCHAR(500) NULL,
    ip VARCHAR(45) NULL,
    location VARCHAR(200) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ NULL,
    decided_via VARCHAR(20) NULL,
    decided_by_user_id BIGINT NULL REFERENCES public.users(id) ON DELETE SET NULL,
    decided_device_id BIGINT NULL REFERENCES public.user_trusted_devices(id) ON DELETE SET NULL,
    decided_note VARCHAR(200) NULL,
    reject_reason VARCHAR(30) NULL,
    failed_code_attempts SMALLINT NOT NULL DEFAULT 0,
    CONSTRAINT uq_auth_login_requests_pending_token_hash UNIQUE (pending_token_hash),
    CONSTRAINT ck_auth_login_requests_status CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'completed')),
    CONSTRAINT ck_auth_login_requests_decided_via CHECK (decided_via IS NULL OR decided_via IN ('device', 'admin', 'recovery_code'))
);
CREATE INDEX IF NOT EXISTS ix_auth_login_requests_user_created ON public.auth_login_requests (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_auth_login_requests_status_expires ON public.auth_login_requests (status, expires_at);
COMMENT ON TABLE public.auth_login_requests IS '知らない機械からのログインの許可依頼。有効30分。ADR-1055';
COMMENT ON COLUMN public.auth_login_requests.id IS '依頼の ID（UUID）';
COMMENT ON COLUMN public.auth_login_requests.user_id IS '依頼した人。public.users.id';
COMMENT ON COLUMN public.auth_login_requests.status IS 'pending＝許可待ち／approved＝許可済み／rejected＝拒否／expired＝期限切れ／completed＝待つ機械が入った';
COMMENT ON COLUMN public.auth_login_requests.match_number IS '待つ機械に出す2けたの番号';
COMMENT ON COLUMN public.auth_login_requests.candidates IS 'いつもの機械に出す候補3つ（例 47,12,85）';
COMMENT ON COLUMN public.auth_login_requests.pending_token_hash IS '待つ機械の Cookie sa_login_pending の sha256。生の値は保存しない';
COMMENT ON COLUMN public.auth_login_requests.device_token_hash IS '待つ機械に既にある印の sha256。無ければ NULL';
COMMENT ON COLUMN public.auth_login_requests.label IS '機械の種類の表示（例 iPhone・Safari）';
COMMENT ON COLUMN public.auth_login_requests.user_agent IS '待つ機械のブラウザ情報';
COMMENT ON COLUMN public.auth_login_requests.ip IS '待つ機械の IP';
COMMENT ON COLUMN public.auth_login_requests.location IS '待つ機械の場所の目安';
COMMENT ON COLUMN public.auth_login_requests.created_at IS '依頼した時刻';
COMMENT ON COLUMN public.auth_login_requests.expires_at IS '期限';
COMMENT ON COLUMN public.auth_login_requests.decided_at IS '決まった時刻';
COMMENT ON COLUMN public.auth_login_requests.decided_via IS '決めた道（device＝いつもの機械／admin＝管理者／recovery_code＝予備の合言葉）';
COMMENT ON COLUMN public.auth_login_requests.decided_by_user_id IS '管理者が許可したときの、その人の public.users.id';
COMMENT ON COLUMN public.auth_login_requests.decided_device_id IS '許可・拒否を押したいつもの機械';
COMMENT ON COLUMN public.auth_login_requests.decided_note IS '管理者が許可したときの本人確認の方法（管理者の許可のときだけ必須）';
COMMENT ON COLUMN public.auth_login_requests.reject_reason IS '拒否の理由（wrong_number など）';
COMMENT ON COLUMN public.auth_login_requests.failed_code_attempts IS '予備の合言葉の間違い回数。5回で依頼を拒否にする';

CREATE TABLE IF NOT EXISTS public.user_recovery_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    code_id CHAR(4) NOT NULL,
    code_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL,
    used_request_id UUID NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_recovery_codes_active
    ON public.user_recovery_codes (user_id, code_id)
    WHERE used_at IS NULL AND revoked_at IS NULL;
COMMENT ON TABLE public.user_recovery_codes IS '予備の合言葉（1人10個・1回ずつ）。本体は argon2 のハッシュだけ保存。ADR-1055';
COMMENT ON COLUMN public.user_recovery_codes.id IS '行の ID';
COMMENT ON COLUMN public.user_recovery_codes.user_id IS '持ち主。public.users.id';
COMMENT ON COLUMN public.user_recovery_codes.code_id IS '見出し4文字。その人の中で（未使用・有効の間）一意';
COMMENT ON COLUMN public.user_recovery_codes.code_hash IS '本体の argon2 ハッシュ。生の値は保存しない';
COMMENT ON COLUMN public.user_recovery_codes.created_at IS '作った時刻';
COMMENT ON COLUMN public.user_recovery_codes.used_at IS '使った時刻。NULL は未使用';
COMMENT ON COLUMN public.user_recovery_codes.revoked_at IS '作り直しで無効にした時刻。行は消さない';
COMMENT ON COLUMN public.user_recovery_codes.used_request_id IS '使ったときの依頼の ID';

ALTER TABLE public.auth_refresh_tokens
    ADD COLUMN IF NOT EXISTS trusted_device_id BIGINT NULL REFERENCES public.user_trusted_devices(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_auth_refresh_tokens_trusted_device_id ON public.auth_refresh_tokens (trusted_device_id);
COMMENT ON COLUMN public.auth_refresh_tokens.trusted_device_id IS 'この組が結び付いているいつもの機械。NULL は機械なし（ADR-1055）';

ALTER TABLE public.auth_events ADD COLUMN IF NOT EXISTS user_id BIGINT NULL;
ALTER TABLE public.auth_events ADD COLUMN IF NOT EXISTS reason VARCHAR(50) NULL;
ALTER TABLE public.auth_events ADD COLUMN IF NOT EXISTS is_new_device BOOLEAN NULL;
CREATE INDEX IF NOT EXISTS ix_auth_events_user_created ON public.auth_events (user_id, created_at DESC);
COMMENT ON COLUMN public.auth_events.user_id IS '誰のログインか（ADR-1055）。不明なら NULL';
COMMENT ON COLUMN public.auth_events.reason IS '成否の理由（ok・bad_password・device_approval_required など）。パスワードは書かない';
COMMENT ON COLUMN public.auth_events.is_new_device IS '初めての機械か。判定していないときは NULL';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_trusted_devices, public.auth_login_requests, public.user_recovery_codes TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.user_trusted_devices_id_seq, public.user_recovery_codes_id_seq TO salesanchor_app;
    END IF;
END $$;
