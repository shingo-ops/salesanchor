-- 便B（docs/handoff/v102-prod-switch/design.md §4-2）。構造のみ。値の操作は含めない（ADR-1007）。
ALTER TABLE public.extraction_items ADD COLUMN IF NOT EXISTS source_lines INTEGER[];
ALTER TABLE public.extraction_items ADD COLUMN IF NOT EXISTS gemini_index INTEGER;
ALTER TABLE public.extraction_jobs ADD COLUMN IF NOT EXISTS gemini_unsure JSONB;
ALTER TABLE public.extraction_jobs ADD COLUMN IF NOT EXISTS review_reasons TEXT;
COMMENT ON COLUMN public.extraction_items.source_lines IS 'v102: Gemini が書き写した原文の行番号（1始まり・昇順・飛び番あり）。v6 は NULL';
COMMENT ON COLUMN public.extraction_items.gemini_index IS 'v102: Gemini の items の順番（0始まり）。v6 は NULL';
COMMENT ON COLUMN public.extraction_jobs.gemini_unsure IS 'v102: Gemini の unsure 申告（応答のまま）。v6 は NULL';
COMMENT ON COLUMN public.extraction_jobs.review_reasons IS 'v102: 投稿単位の要確認の理由コード（カンマ区切り）。v6 は NULL';
