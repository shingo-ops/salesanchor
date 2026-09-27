-- extraction_attempts に Gemini API トークン数・コストカラムを追加
-- input_tokens: APIへの入力トークン数
-- output_tokens: APIからの出力トークン数
-- cost_usd: USD換算コスト（NUMERIC(10,6)は最小単価0.000001まで対応）
ALTER TABLE public.extraction_attempts ADD COLUMN IF NOT EXISTS input_tokens integer;
ALTER TABLE public.extraction_attempts ADD COLUMN IF NOT EXISTS output_tokens integer;
ALTER TABLE public.extraction_attempts ADD COLUMN IF NOT EXISTS cost_usd numeric(10,6);
