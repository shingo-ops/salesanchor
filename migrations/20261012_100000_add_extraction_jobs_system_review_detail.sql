-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
ALTER TABLE public.extraction_jobs ADD COLUMN IF NOT EXISTS system_review_detail JSONB;
COMMENT ON COLUMN public.extraction_jobs.system_review_detail IS
    'v102 システムが見つけた要確認の明細（行番号・間の行の商品候補）。解析のたびに上書き。原文は入れない';
