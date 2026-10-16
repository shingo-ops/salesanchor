-- ADR-1020 便1: 共用商品の「調べたが存在しない」空欄の記録。値の書き込みはしない（ADR-155）。冪等。
-- ロールバック: DROP TABLE IF EXISTS public.product_blank_confirmations;

CREATE TABLE IF NOT EXISTS public.product_blank_confirmations (
    product_id   INTEGER     NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    field_code   TEXT        NOT NULL,
    confirmed_by TEXT        NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    note         TEXT,
    CONSTRAINT product_blank_confirmations_pkey PRIMARY KEY (product_id, field_code),
    CONSTRAINT product_blank_confirmations_field_code_check
        CHECK (field_code IN ('name_en', 'mark', 'release_date', 'exclude_keywords')),
    CONSTRAINT product_blank_confirmations_note_size_check
        CHECK (note IS NULL OR char_length(note) <= 1000)
);

COMMENT ON TABLE public.product_blank_confirmations IS
    'ADR-1020: 共用商品の空欄を「調べたが存在しない」と確かめた記録。値が入ると消す';

ALTER TABLE public.product_blank_confirmations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_blank_confirmations FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_blank_confirmations_read ON public.product_blank_confirmations;
CREATE POLICY product_blank_confirmations_read ON public.product_blank_confirmations
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS product_blank_confirmations_write ON public.product_blank_confirmations;
CREATE POLICY product_blank_confirmations_write ON public.product_blank_confirmations
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
