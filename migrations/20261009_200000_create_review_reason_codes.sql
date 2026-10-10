-- 便A（docs/handoff/v102-prod-switch/design.md §12）。構造のみ。初期行は data/review_reason_codes/ の1回だけのデータ変更（ADR-1007）。
CREATE TABLE IF NOT EXISTS public.review_reason_codes (
    code       TEXT PRIMARY KEY CHECK (code ~ '^[a-z][a-z0-9_]*$'),
    source     TEXT NOT NULL CHECK (source IN ('gemini', 'system')),
    fix_stage  TEXT NOT NULL CHECK (fix_stage IN ('extraction', 'analysis')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.review_reason_codes IS '要確認の理由コードの正本。出どころ（gemini=Gemini が自分で申告／system=システムが見つけた）と直す工程。画面の言葉は ja/en.json の reviewReason.<code>';
COMMENT ON COLUMN public.review_reason_codes.source IS 'gemini / system';
COMMENT ON COLUMN public.review_reason_codes.fix_stage IS 'extraction=Gemini の書き写しを直す／analysis=マスタ・商品割当で直す';
-- アプリは読むだけ（書くのは設計者のデータ変更のみ）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='salesanchor_app') THEN
        GRANT SELECT ON public.review_reason_codes TO salesanchor_app;
    END IF;
END $$;
