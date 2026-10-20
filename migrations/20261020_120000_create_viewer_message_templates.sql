-- ADR-1019 段11 便1: 閲覧者向け文面のテンプレート表（構造のみ・データなし・冪等）
-- 全体共通（テナント別ではない）のため RLS なし。初期値は専用 CLI（viewer_template_cli）で入れる。
CREATE TABLE IF NOT EXISTS public.viewer_message_templates (
    key                TEXT PRIMARY KEY,
    body               TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 1800),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL
);

COMMENT ON TABLE public.viewer_message_templates IS '閲覧者向け文面のテンプレート（鍵は backend/app/services/viewer_message_templates.py の台帳）';
COMMENT ON COLUMN public.viewer_message_templates.key IS '文面の鍵（台帳の9件）';
COMMENT ON COLUMN public.viewer_message_templates.body IS '本文（差し込み項目は {name} 形式・1〜1800文字）';
COMMENT ON COLUMN public.viewer_message_templates.updated_at IS '最後に直した時刻';
COMMENT ON COLUMN public.viewer_message_templates.updated_by_user_id IS '最後に直した社員 public.users.id（seed は NULL）';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE ON public.viewer_message_templates TO salesanchor_app;
    END IF;
END $$;
