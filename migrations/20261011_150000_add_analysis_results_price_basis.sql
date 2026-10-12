-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS price_basis VARCHAR(100);
COMMENT ON COLUMN public.analysis_results.price_basis IS
    '価格の行の決め方の印（v102）。円・¥を除いた探し直しで見つけた件は V102:yen_free、それ以外は NULL';
