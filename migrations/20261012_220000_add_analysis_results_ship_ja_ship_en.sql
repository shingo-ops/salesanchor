-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS ship_ja TEXT;
ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS ship_en TEXT;
COMMENT ON COLUMN public.analysis_results.ship_ja IS
    '発送日（v102）。備考マスタの分類「発送時期系」でそろえた形、当たらない部分は拾った文字。違えば同じ投稿の中で別の件として配信';
COMMENT ON COLUMN public.analysis_results.ship_en IS
    'ship_ja の英語。全部の部分がマスタに当たったときだけ入る。配信シートには出さない';
