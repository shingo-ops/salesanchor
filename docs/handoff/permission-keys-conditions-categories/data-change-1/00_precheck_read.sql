SELECT 'TOTAL' AS k, count(*)::text AS v FROM ai_ro.public__permissions
UNION ALL SELECT 'NEW_EXISTING', count(*)::text FROM ai_ro.public__permissions WHERE resource IN ('conditions','product_categories')
UNION ALL SELECT 'CAT_EXISTING', count(*)::text FROM ai_ro.public__permissions WHERE category IN ('状態マスタ','商品カテゴリ')
UNION ALL SELECT 'MAX_ID', max(id)::text FROM ai_ro.public__permissions;
