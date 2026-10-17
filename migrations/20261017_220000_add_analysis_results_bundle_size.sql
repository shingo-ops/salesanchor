-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。ADR-1027
ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS bundle_size integer NULL;
COMMENT ON COLUMN public.analysis_results.bundle_size IS
    'まとめ売りのまとめの数。NULL=まとめ売りでない。ADR-1027';
