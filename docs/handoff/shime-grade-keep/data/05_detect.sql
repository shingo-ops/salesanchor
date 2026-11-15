-- limit=500
WITH lj AS (SELECT DISTINCT ON (source_message_id) id, source_message_id FROM ai_ro.public__extraction_jobs ORDER BY source_message_id, created_at DESC, id DESC),
r AS (SELECT sm.id sm_id, sm.supplier_channel_id ch, sm.line_posted_at t, ar.product_id, ar.condition_id, ar.status, ar.price_normalized p, ei.line_start
 FROM ai_ro.public__source_messages sm JOIN lj ON lj.source_message_id=sm.id JOIN ai_ro.public__extraction_items ei ON ei.extraction_job_id=lj.id JOIN ai_ro.public__analysis_results ar ON ar.extraction_item_id=ei.id
 WHERE sm.line_posted_at > now()-interval '30 days' AND ar.product_id IS NOT NULL),
d AS (SELECT sm_id, ch, t, product_id, condition_id, count(*) n, count(DISTINCT p) np FROM r WHERE status='In Stock' GROUP BY 1,2,3,4,5 HAVING count(*)>1 AND count(DISTINCT p)>1),
x AS (SELECT d.*, (SELECT r2.sm_id FROM r r2 WHERE r2.ch=d.ch AND r2.product_id=d.product_id AND r2.condition_id=d.condition_id AND r2.t>d.t ORDER BY r2.t LIMIT 1) nx FROM d)
SELECT left(x.sm_id::text,8) dup_sm, x.t, x.product_id, x.condition_id, x.n, left(x.nx::text,8) nx_sm, r2.t nx_t, r2.line_start nx_line, left(replace(split_part(sm2.raw_text,E'\n',r2.line_start),E'\t',' '),80) nx_text,
 (SELECT string_agg(left(replace(split_part(sm.raw_text,E'\n',ei.line_start),E'\t',' '),40)||'~'||left(replace(split_part(sm.raw_text,E'\n',ei.line_end),E'\t',' '),50),' || ' ORDER BY ei.line_start) FROM lj JOIN ai_ro.public__extraction_items ei ON ei.extraction_job_id=lj.id JOIN ai_ro.public__analysis_results ar ON ar.extraction_item_id=ei.id JOIN ai_ro.public__source_messages sm ON sm.id=lj.source_message_id WHERE lj.source_message_id=x.sm_id AND ar.product_id=x.product_id AND ar.condition_id=x.condition_id AND ar.status='In Stock') dup_text
FROM x JOIN r r2 ON r2.sm_id=x.nx AND r2.product_id=x.product_id AND r2.condition_id=x.condition_id AND r2.status='Sold out' JOIN ai_ro.public__source_messages sm2 ON sm2.id=x.nx ORDER BY x.t
