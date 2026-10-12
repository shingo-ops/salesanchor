-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
ALTER TABLE public.extraction_attempts ADD COLUMN IF NOT EXISTS thought_summaries JSONB;
COMMENT ON COLUMN public.extraction_attempts.thought_summaries IS
    'Gemini の思考要約（文字列の配列）。応答と同じ試行の行に保存。8MiB を超えるときは NULL';
