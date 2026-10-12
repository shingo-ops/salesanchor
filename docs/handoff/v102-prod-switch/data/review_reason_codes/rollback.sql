-- 便A 戻し: 使うのは戻すときだけ。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes WHERE code IN ('pid_unresolved', 'multi_candidate', 'note_unmatched', 'empty_box', 'empty_box_ambiguous', 'empty_box_master_unavailable', 'unit_unresolved', 'price_unresolved', 'excluded', 'item_shape_invalid', 'price_not_in_lines', 'duplicate_price_line', 'ship', 'condition', 'quantity_no_number', 'possible_footer_line', 'unit_unknown', 'category_unknown', 'heading_ship_with_own_ship', 'no_items', 'possible_missing_item', 'product_not_in_master', 'product_multiple', 'condition_multiple_candidates', 'condition_unknown', 'gemini_unsure', 'gemini_unsure_invalid', 'response_unreadable', 'extract_exception') RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
