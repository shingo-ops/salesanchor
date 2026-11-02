-- ADR-1055 段W: いつもの機械のホーム画面のアプリへ、許可依頼の通知（web push）を出すための購読の置き場。
-- 追加のみ・冪等。RLS は付けない（段A の表と同じ理由・design.md A-1）。
-- endpoint・p256dh・auth は通知の宛先と鍵なので、ai_cloud の分類では mask にする。

CREATE TABLE IF NOT EXISTS public.user_push_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    trusted_device_id BIGINT NOT NULL REFERENCES public.user_trusted_devices(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_success_at TIMESTAMPTZ,
    failed_count SMALLINT NOT NULL DEFAULT 0,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_user_push_subscriptions_user ON public.user_push_subscriptions (user_id);
CREATE INDEX IF NOT EXISTS ix_user_push_subscriptions_device ON public.user_push_subscriptions (trusted_device_id);

COMMENT ON TABLE public.user_push_subscriptions IS '通知（web push）の購読。1台の機械に有効な購読は1つ（ADR-1055 段W）';
COMMENT ON COLUMN public.user_push_subscriptions.id IS '購読の番号';
COMMENT ON COLUMN public.user_push_subscriptions.user_id IS '購読した人';
COMMENT ON COLUMN public.user_push_subscriptions.trusted_device_id IS '購読した機械（取り消されたら送らない）';
COMMENT ON COLUMN public.user_push_subscriptions.endpoint IS '通知の送り先 URL（機密扱い）';
COMMENT ON COLUMN public.user_push_subscriptions.p256dh IS '通知を暗号にする公開鍵（機密扱い）';
COMMENT ON COLUMN public.user_push_subscriptions.auth IS '通知を暗号にする合言葉（機密扱い）';
COMMENT ON COLUMN public.user_push_subscriptions.created_at IS '作った日時';
COMMENT ON COLUMN public.user_push_subscriptions.last_success_at IS '最後に送れた日時';
COMMENT ON COLUMN public.user_push_subscriptions.failed_count IS '続けて送れなかった回数';
COMMENT ON COLUMN public.user_push_subscriptions.revoked_at IS '取り消した日時。NULL なら有効';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_push_subscriptions TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.user_push_subscriptions_id_seq TO salesanchor_app;
    END IF;
END $$;
