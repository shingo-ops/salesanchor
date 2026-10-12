-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
ALTER TABLE public.tcg_distribution_targets ADD COLUMN IF NOT EXISTS review_sheet_name TEXT;
COMMENT ON COLUMN public.tcg_distribution_targets.review_sheet_name IS
    '要確認の一覧を出すタブ名。NULL なら出さない（既定）';
