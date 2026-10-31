-- ADR-1013 便6: ログイン直後のパスキー登録の案内で「今はスキップ」を押した記録（冪等）
-- RLS なし: public.webauthn_credentials と同じく、テナントが決まる前に引くため
CREATE TABLE IF NOT EXISTS public.passkey_enroll_prompt_skips (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    skipped_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_passkey_enroll_prompt_skips_user_at
    ON public.passkey_enroll_prompt_skips (user_id, skipped_at);
COMMENT ON TABLE public.passkey_enroll_prompt_skips IS 'ログイン直後のパスキー登録の案内で「今はスキップ」を押した記録。直近 180 日で 3 回あれば案内を出さない';
COMMENT ON COLUMN public.passkey_enroll_prompt_skips.user_id IS 'スキップした人';
COMMENT ON COLUMN public.passkey_enroll_prompt_skips.skipped_at IS 'スキップした時刻';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT ON public.passkey_enroll_prompt_skips TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.passkey_enroll_prompt_skips_id_seq TO salesanchor_app;
    END IF;
END $$;
