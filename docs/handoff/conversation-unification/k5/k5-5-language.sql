-- K5-5 言語判定（画面が使う値: 確定か・確定のときの言語。useInboxState.ts:723）。リードごとに比べる。
-- 今の形 = lang_judge.py:45-111（meta ＋ conversation_logs、原文でない窓口は conversation_logs 側だけ外す）、新しい形 = card §5（meta だけ、原文でない窓口を meta の platform で外す）。
-- 確定 = 件数 3 以上（lang_judge.py:30）。言語は最多の言語。最多が並ぶときは並んだ言語を全部つないで比べる。
-- 読み取り専用（ai_ro）。NNN を会社の3桁に替えて1社ずつ流す（tenant_id の比べにも NNN を数として使う）。
-- 合格: 下見（recon §8-6）で分かっている会社 004 のリード 38（未確定のまま）のほかに mismatch が 0。反映の前と後の両方で流す。
WITH o AS (
  SELECT lead_id, original_language AS l FROM ai_ro.tenant_NNN__meta_messages WHERE direction = 'inbound' AND original_language IS NOT NULL AND deleted_at IS NULL AND lead_id IS NOT NULL
  UNION ALL
  SELECT cl.lead_id, cl.original_language FROM ai_ro.tenant_NNN__conversation_logs cl WHERE cl.direction = 'inbound' AND cl.original_language IS NOT NULL AND cl.deleted_at IS NULL AND cl.lead_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM ai_ro.public__channel_masters cm WHERE cm.platform = cl.channel_type AND cm.is_verbatim = FALSE AND (cm.tenant_id IS NULL OR cm.tenant_id = NNN))
), n AS (
  SELECT m.lead_id, m.original_language AS l FROM ai_ro.tenant_NNN__meta_messages m WHERE m.direction = 'inbound' AND m.original_language IS NOT NULL AND m.deleted_at IS NULL AND m.lead_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM ai_ro.public__channel_masters cm WHERE cm.platform = m.platform AND cm.is_verbatim = FALSE AND (cm.tenant_id IS NULL OR cm.tenant_id = NNN))
), oc AS (SELECT lead_id, l, count(*) AS c FROM o GROUP BY 1, 2),
   nc AS (SELECT lead_id, l, count(*) AS c FROM n GROUP BY 1, 2),
   ot AS (SELECT lead_id, sum(c) AS total, max(c) AS top FROM oc GROUP BY 1),
   nt AS (SELECT lead_id, sum(c) AS total, max(c) AS top FROM nc GROUP BY 1),
   oj AS (SELECT t.lead_id, t.total >= 3 AS conf, CASE WHEN t.total >= 3 THEN string_agg(oc.l, ',' ORDER BY oc.l) END AS lang FROM ot t JOIN oc ON oc.lead_id = t.lead_id AND oc.c = t.top GROUP BY t.lead_id, t.total),
   nj AS (SELECT t.lead_id, t.total >= 3 AS conf, CASE WHEN t.total >= 3 THEN string_agg(nc.l, ',' ORDER BY nc.l) END AS lang FROM nt t JOIN nc ON nc.lead_id = t.lead_id AND nc.c = t.top GROUP BY t.lead_id, t.total)
SELECT 'NNN' AS t, count(*) AS mismatch, string_agg(lead_id::text, ',' ORDER BY lead_id) AS mismatch_leads
FROM oj FULL JOIN nj USING (lead_id)
WHERE (COALESCE(oj.conf, FALSE), oj.lang) IS DISTINCT FROM (COALESCE(nj.conf, FALSE), nj.lang);
