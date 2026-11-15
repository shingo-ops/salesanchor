-- limit=500
-- 設計 K1 の実際の投稿での確認。便1 の反映の時刻より後の投稿で、原文に「切れ込み」を含む行と、その行を件の行に持つ解析行の状態を出す。
-- 流す前に、下の timestamptz '2026-11-15 00:00+09' を便1 の反映の時刻に書き換える。出力には原文の一部が入るので、作業記録（リポジトリ外）にだけ置く。
WITH lj AS (SELECT DISTINCT ON (source_message_id) id, source_message_id FROM ai_ro.public__extraction_jobs ORDER BY source_message_id, created_at DESC, id DESC),
l AS (SELECT sm.id sm_id, sm.supplier_channel_id ch, sm.line_posted_at t, g.n, g.l FROM ai_ro.public__source_messages sm CROSS JOIN LATERAL unnest(string_to_array(sm.raw_text, E'\n')) WITH ORDINALITY AS g(l,n) WHERE sm.line_posted_at > timestamptz '2026-11-15 00:00+09' AND g.l LIKE '%切れ込み%')
SELECT left(l.sm_id::text,8) sm8, left(l.ch::text,8) ch8, to_char(l.t AT TIME ZONE 'Asia/Tokyo','MM-DD HH24:MI') t, l.n, left(replace(l.l,E'\t',' '),60) line,
 left(ei.id::text,8) ei8, ar.product_id, lc.canonical, ar.condition_basis, ar.status, ar.is_current, ar.engine_version
FROM l LEFT JOIN lj ON lj.source_message_id=l.sm_id
LEFT JOIN ai_ro.public__extraction_items ei ON ei.extraction_job_id=lj.id AND (','||replace(trim(both '[]{}' from ei.source_lines::text),' ','')||',') LIKE '%,'||l.n||',%'
LEFT JOIN ai_ro.public__analysis_results ar ON ar.extraction_item_id=ei.id
LEFT JOIN ai_ro.public__line_conditions lc ON lc.id=ar.condition_id
ORDER BY l.t, l.n
