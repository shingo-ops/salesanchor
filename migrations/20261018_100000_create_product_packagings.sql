-- ADR-1028 便1: 商品の荷姿（単位ごとの入数・重さ・出典）。空の表を作るだけ。値は書かない（ADR-155・ADR-1007）。冪等。
-- ロールバック: DROP TABLE IF EXISTS public.product_packagings;

CREATE TABLE IF NOT EXISTS public.product_packagings (
    id                 SERIAL       PRIMARY KEY,
    product_id         INTEGER      NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    unit_id            INTEGER      NOT NULL REFERENCES public.quantity_units(id),
    contained_unit_id  INTEGER               REFERENCES public.quantity_units(id),
    contained_count    INTEGER,
    count_source       TEXT,
    count_source_urls  TEXT[]       NOT NULL DEFAULT '{}',
    weight_kg          NUMERIC(8,3),
    weight_source      TEXT,
    weight_source_urls TEXT[]       NOT NULL DEFAULT '{}',
    note               TEXT,
    updated_by         TEXT,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT product_packagings_product_unit_key UNIQUE (product_id, unit_id),
    CONSTRAINT product_packagings_not_self_check
        CHECK (contained_unit_id IS NULL OR contained_unit_id <> unit_id),
    CONSTRAINT product_packagings_count_pair_check
        CHECK ((contained_unit_id IS NULL) = (contained_count IS NULL)),
    CONSTRAINT product_packagings_count_positive_check
        CHECK (contained_count IS NULL OR contained_count > 0),
    CONSTRAINT product_packagings_weight_positive_check
        CHECK (weight_kg IS NULL OR weight_kg > 0),
    CONSTRAINT product_packagings_not_empty_check
        CHECK (contained_count IS NOT NULL OR weight_kg IS NOT NULL),
    CONSTRAINT product_packagings_count_source_check
        CHECK ((contained_count IS NULL) = (count_source IS NULL)
            AND (count_source IS NULL OR count_source IN ('official', 'official_store', 'retailer', 'measured', 'legacy'))),
    CONSTRAINT product_packagings_weight_source_check
        CHECK ((weight_kg IS NULL) = (weight_source IS NULL)
            AND (weight_source IS NULL OR weight_source IN ('official', 'official_store', 'retailer', 'measured', 'legacy'))),
    CONSTRAINT product_packagings_count_urls_check
        CHECK (array_position(count_source_urls, NULL) IS NULL AND (count_source IS NULL
            OR (count_source IN ('official', 'official_store') AND cardinality(count_source_urls) >= 1)
            OR (count_source = 'retailer' AND cardinality(count_source_urls) >= 2)
            OR count_source IN ('measured', 'legacy'))),
    CONSTRAINT product_packagings_weight_urls_check
        CHECK (array_position(weight_source_urls, NULL) IS NULL AND (weight_source IS NULL
            OR (weight_source IN ('official', 'official_store') AND cardinality(weight_source_urls) >= 1)
            OR (weight_source = 'retailer' AND cardinality(weight_source_urls) >= 2)
            OR weight_source IN ('measured', 'legacy'))),
    CONSTRAINT product_packagings_note_size_check
        CHECK (note IS NULL OR char_length(note) <= 1000)
);

-- 商品ごとの検索は UNIQUE (product_id, unit_id) の索引が使えるので、別の索引は作らない

CREATE OR REPLACE FUNCTION public.set_updated_at_product_packagings()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_product_packagings_updated_at ON public.product_packagings;
CREATE TRIGGER trg_product_packagings_updated_at BEFORE UPDATE ON public.product_packagings
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_product_packagings();

COMMENT ON TABLE public.product_packagings IS
    'ADR-1028: 商品の荷姿。1行=商品×単位。中に入る単位と数、その単位1つの重さ、それぞれの出典。入数・重さの正本';
COMMENT ON COLUMN public.product_packagings.count_source IS
    'official=公式サイト / official_store=公式通販 / retailer=販売サイト(URL2つ以上の一致) / measured=実測 / legacy=旧列から写した値';

ALTER TABLE public.product_packagings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_packagings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_packagings_read ON public.product_packagings;
CREATE POLICY product_packagings_read ON public.product_packagings
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS product_packagings_write ON public.product_packagings;
CREATE POLICY product_packagings_write ON public.product_packagings
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
