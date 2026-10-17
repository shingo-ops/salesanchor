-- ADR-1028 便2 事後確認（読み取りの道・1 文）。K3・K4・K5 を 1 つの結果に並べる。
-- 期待: K3 が CASE|146・BOX|176（計 322）、K4 が 0|0|0|0、K5 が 4 行（既存 3 行は前と同じ + CARD 40）
WITH r AS (
 SELECT p.id, p.boxes_per_case, p.case_weight_kg, p.packs_per_box, p.box_weight_kg,
   (SELECT x.contained_count FROM ai_ro.public__product_packagings x JOIN ai_ro.public__quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'CASE') AS r_bpc,
   (SELECT x.weight_kg       FROM ai_ro.public__product_packagings x JOIN ai_ro.public__quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'CASE') AS r_cwk,
   (SELECT x.contained_count FROM ai_ro.public__product_packagings x JOIN ai_ro.public__quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'BOX')  AS r_ppb,
   (SELECT x.weight_kg       FROM ai_ro.public__product_packagings x JOIN ai_ro.public__quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'BOX')  AS r_bwk
 FROM ai_ro.public__products p)
SELECT 'K3' AS k, concat_ws('|', u.code, count(*)) AS v
  FROM ai_ro.public__product_packagings x JOIN ai_ro.public__quantity_units u ON u.id = x.unit_id GROUP BY u.code
UNION ALL SELECT 'K3_TOTAL', count(*)::text FROM ai_ro.public__product_packagings
UNION ALL SELECT 'K4', concat_ws('|',
       count(*) FILTER (WHERE boxes_per_case IS DISTINCT FROM r_bpc),
       count(*) FILTER (WHERE case_weight_kg IS DISTINCT FROM r_cwk),
       count(*) FILTER (WHERE packs_per_box  IS DISTINCT FROM r_ppb),
       count(*) FILTER (WHERE box_weight_kg  IS DISTINCT FROM r_bwk)) FROM r
UNION ALL SELECT 'K5', coalesce(id::text, '<NULL>') || ' | ' || coalesce(code::text, '<NULL>') || ' | ' || coalesce(name::text, '<NULL>') || ' | ' || coalesce(name_en::text, '<NULL>') || ' | ' || coalesce(value::text, '<NULL>') || ' | ' || coalesce(display_order::text, '<NULL>') || ' | ' || coalesce(is_active::text, '<NULL>') FROM ai_ro.public__quantity_units
