-- 便A dryrun: 入れて検査して必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('pid_unresolved', 'system', 'analysis'),
    ('multi_candidate', 'system', 'analysis'),
    ('note_unmatched', 'system', 'analysis'),
    ('empty_box', 'system', 'analysis'),
    ('empty_box_ambiguous', 'system', 'analysis'),
    ('empty_box_master_unavailable', 'system', 'analysis'),
    ('unit_unresolved', 'system', 'analysis'),
    ('price_unresolved', 'system', 'analysis'),
    ('excluded', 'system', 'analysis'),
    ('item_shape_invalid', 'system', 'extraction'),
    ('price_not_in_lines', 'system', 'extraction'),
    ('duplicate_price_line', 'system', 'extraction'),
    ('ship', 'system', 'extraction'),
    ('condition', 'system', 'extraction'),
    ('quantity_no_number', 'system', 'extraction'),
    ('possible_footer_line', 'system', 'extraction'),
    ('unit_unknown', 'system', 'analysis'),
    ('category_unknown', 'system', 'analysis'),
    ('heading_ship_with_own_ship', 'system', 'extraction'),
    ('no_items', 'system', 'extraction'),
    ('possible_missing_item', 'system', 'extraction'),
    ('product_not_in_master', 'system', 'analysis'),
    ('product_multiple', 'system', 'analysis'),
    ('condition_multiple_candidates', 'system', 'analysis'),
    ('condition_unknown', 'system', 'analysis'),
    ('gemini_unsure', 'gemini', 'extraction'),
    ('gemini_unsure_invalid', 'system', 'extraction'),
    ('response_unreadable', 'system', 'extraction'),
    ('extract_exception', 'system', 'analysis');
DO $$
DECLARE n int; g int; s int; e int; a int;
BEGIN
    SELECT count(*), count(*) FILTER (WHERE source='gemini'), count(*) FILTER (WHERE source='system'),
           count(*) FILTER (WHERE fix_stage='extraction'), count(*) FILTER (WHERE fix_stage='analysis')
      INTO n, g, s, e, a FROM public.review_reason_codes;
    IF n <> 29 OR g <> 1 OR s <> 28 OR e <> 13 OR a <> 16 THEN
        RAISE EXCEPTION 'CHECK_NG rows=% gemini=% system=% extraction=% analysis=%', n, g, s, e, a;
    END IF;
END $$;
SELECT 'CHECK_OK 1';
ROLLBACK;
SELECT 'DRYRUN_OK';
