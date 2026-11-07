-- K5-3 会社詳細の会話タブ（会社ごとの件数と最新時刻）。今の形 = companies.py:1082-1131（conversation_logs・消した印なし）、新しい形 = card §5（meta_messages・消した印なし）。
-- 読み取り専用（ai_ro）。NNN を会社の3桁に替えて1社ずつ流す。合格: mismatch = 0。反映の前と後の両方で流す。
SELECT 'NNN' AS t,
  (SELECT count(*) FROM (SELECT company_id, count(*) AS n, MAX(occurred_at) AS ts FROM ai_ro.tenant_NNN__conversation_logs WHERE company_id IS NOT NULL AND deleted_at IS NULL GROUP BY company_id) o FULL JOIN (SELECT company_id, count(*) AS n, MAX(COALESCE(occurred_at, created_at)) AS ts FROM ai_ro.tenant_NNN__meta_messages WHERE company_id IS NOT NULL AND deleted_at IS NULL GROUP BY company_id) nw USING (company_id) WHERE (o.n, o.ts) IS DISTINCT FROM (nw.n, nw.ts)) AS mismatch;
