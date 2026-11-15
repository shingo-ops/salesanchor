-- limit=500
SELECT 'PRECHECK' k, id::text, code, canonical, coalesce(app_kubun,'') app_kubun,
       (SELECT count(*) FROM ai_ro.public__line_conditions WHERE search_kw LIKE '%切れ込み%' OR coalesce(exclude_kw,'') LIKE '%切れ込み%')::text kw_rows,
       right(search_kw, 20) tail
FROM ai_ro.public__line_conditions WHERE id = 13 AND code = 'CN0002' AND canonical = 'Damaged case'
UNION ALL
SELECT 'KIREKOMI_LINES', count(*)::text, '', '', '', '', ''
FROM ai_ro.public__source_messages sm CROSS JOIN LATERAL unnest(string_to_array(sm.raw_text, E'\n')) AS g(l)
WHERE sm.line_posted_at > now() - interval '180 days' AND g.l LIKE '%切れ込み%'
