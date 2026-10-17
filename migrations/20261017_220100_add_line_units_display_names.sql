-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。ADR-1027
-- 値は docs/handoff/bundle-sale/data/units_display_*.sql で入れる。
ALTER TABLE public.line_units
    ADD COLUMN IF NOT EXISTS name_ja text NULL,
    ADD COLUMN IF NOT EXISTS name_en text NULL;
COMMENT ON COLUMN public.line_units.name_ja IS '配信の商品名に出す単位の日本語の呼び名。NULL のときは canonical を使う。ADR-1027';
COMMENT ON COLUMN public.line_units.name_en IS '配信の商品名に出す単位の英語の呼び名。NULL のときは canonical を使う。ADR-1027';
