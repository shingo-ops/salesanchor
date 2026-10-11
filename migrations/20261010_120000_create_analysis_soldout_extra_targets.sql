-- 便2-1（docs/handoff/v102-shime-multi-targets/design.md §4）。構造のみ。値の操作は含めない（ADR-1007）。
CREATE TABLE IF NOT EXISTS public.analysis_soldout_extra_targets (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_result_id UUID NOT NULL REFERENCES public.analysis_results(id) ON DELETE CASCADE,
    product_id         INTEGER NOT NULL,
    condition_id       INTEGER NOT NULL,
    ref_message_id     UUID NOT NULL,
    ref_line           INTEGER NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (analysis_result_id, product_id, condition_id)
);
CREATE INDEX IF NOT EXISTS analysis_soldout_extra_targets_pair_idx
    ON public.analysis_soldout_extra_targets (product_id, condition_id);
COMMENT ON TABLE public.analysis_soldout_extra_targets IS 'v102: 1つの〆の件が完売にする2つ目以降の (商品, 状態)。1つ目は analysis_results の行そのもの。ADR-158 のマージが仮の行として順位付けに使う';
COMMENT ON COLUMN public.analysis_soldout_extra_targets.ref_message_id IS '根拠: 参照した在庫の投稿 source_messages.id';
COMMENT ON COLUMN public.analysis_soldout_extra_targets.ref_line IS '根拠: 参照した在庫の行番号（1始まり）';
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='salesanchor_app') THEN
        GRANT SELECT, INSERT, DELETE ON public.analysis_soldout_extra_targets TO salesanchor_app;
    END IF;
END $$;
