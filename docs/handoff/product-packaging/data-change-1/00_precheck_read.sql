-- ADR-1028 便2 事前確認（読み取りの道・1 文）。ビューは ai_ro.public__*。
-- 期待: QU が 3 行(10/20/30)・CASE_CAND|146・BOX_CAND|176・LE0 が 4 つとも 0・PACKAGINGS|0・CARD_EXISTS|0
SELECT 'QU' AS k, coalesce(id::text, '<NULL>') || ' | ' || coalesce(code::text, '<NULL>') || ' | ' || coalesce(name::text, '<NULL>') || ' | ' || coalesce(name_en::text, '<NULL>') || ' | ' || coalesce(value::text, '<NULL>') || ' | ' || coalesce(display_order::text, '<NULL>') || ' | ' || coalesce(is_active::text, '<NULL>') AS v FROM ai_ro.public__quantity_units
UNION ALL SELECT 'CASE_CAND', count(*)::text FROM ai_ro.public__products WHERE boxes_per_case IS NOT NULL OR case_weight_kg IS NOT NULL
UNION ALL SELECT 'BOX_CAND', count(*)::text FROM ai_ro.public__products WHERE packs_per_box IS NOT NULL OR box_weight_kg IS NOT NULL
UNION ALL SELECT 'LE0_boxes_per_case', count(*)::text FROM ai_ro.public__products WHERE boxes_per_case <= 0
UNION ALL SELECT 'LE0_case_weight_kg', count(*)::text FROM ai_ro.public__products WHERE case_weight_kg <= 0
UNION ALL SELECT 'LE0_packs_per_box', count(*)::text FROM ai_ro.public__products WHERE packs_per_box <= 0
UNION ALL SELECT 'LE0_box_weight_kg', count(*)::text FROM ai_ro.public__products WHERE box_weight_kg <= 0
UNION ALL SELECT 'PACKAGINGS', count(*)::text FROM ai_ro.public__product_packagings
UNION ALL SELECT 'CARD_EXISTS', count(*)::text FROM ai_ro.public__quantity_units WHERE code = 'CARD'
