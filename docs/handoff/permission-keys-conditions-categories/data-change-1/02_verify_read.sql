SELECT 'K1_TOTAL' AS k, count(*)::text AS v FROM ai_ro.public__permissions
UNION ALL SELECT 'K1_NEW', string_agg(key || '|' || category || '|' || description, ' ; ' ORDER BY key) FROM ai_ro.public__permissions WHERE category IN ('状態マスタ','商品カテゴリ')
UNION ALL SELECT 'K1_NEW_COUNT', count(*)::text FROM ai_ro.public__permissions WHERE category IN ('状態マスタ','商品カテゴリ');
