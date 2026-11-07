-- K5-4 集計ビュー v_company_stats の conversation_count・last_conversation_at。ビューは ai_ro に無いため、ビューの式を表から直接計算して比べる。
-- 今の形 = 20260612_120000（conversation_logs・COUNT(DISTINCT id)・MAX(occurred_at)・消した印を見ない）、新しい形 = card §6（meta_messages・消した印なし・MAX(COALESCE(occurred_at, created_at))）。
-- ビューは会社の表に LEFT JOIN するので、会社ごとの集まりが同じならビューの行も同じ。読み取り専用（ai_ro）。NNN を会社の3桁に替えて1社ずつ流す。合格: mismatch = 0。反映の前と後の両方で流す。
SELECT 'NNN' AS t,
  (SELECT count(*) FROM (SELECT company_id, count(DISTINCT id) AS n, MAX(occurred_at) AS ts FROM ai_ro.tenant_NNN__conversation_logs WHERE company_id IS NOT NULL GROUP BY company_id) o FULL JOIN (SELECT company_id, count(DISTINCT id) AS n, MAX(COALESCE(occurred_at, created_at)) AS ts FROM ai_ro.tenant_NNN__meta_messages WHERE company_id IS NOT NULL AND deleted_at IS NULL GROUP BY company_id) nw USING (company_id) WHERE (o.n, o.ts) IS DISTINCT FROM (nw.n, nw.ts)) AS mismatch;
