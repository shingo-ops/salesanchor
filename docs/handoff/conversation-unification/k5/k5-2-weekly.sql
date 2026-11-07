-- K5-2 週次の助言の「会社ごとの最終会話日」。今の形 = analytics.py:2253-2261（conversation_logs・消した印を見ない）、新しい形 = card §5（meta_messages・消した印なし）。
-- 読み取り専用（ai_ro）。NNN を会社の3桁に替えて1社ずつ流す。合格: mismatch = 0。反映の前と後の両方で流す。
SELECT 'NNN' AS t,
  (SELECT count(*) FROM (SELECT company_id, MAX(occurred_at) AS ts FROM ai_ro.tenant_NNN__conversation_logs WHERE company_id IS NOT NULL GROUP BY company_id) o FULL JOIN (SELECT company_id, MAX(COALESCE(occurred_at, created_at)) AS ts FROM ai_ro.tenant_NNN__meta_messages WHERE company_id IS NOT NULL AND deleted_at IS NULL GROUP BY company_id) n USING (company_id) WHERE o.ts IS DISTINCT FROM n.ts) AS mismatch,
  (SELECT count(DISTINCT company_id) FROM ai_ro.tenant_NNN__conversation_logs WHERE company_id IS NOT NULL) AS old_companies,
  (SELECT count(DISTINCT company_id) FROM ai_ro.tenant_NNN__meta_messages WHERE company_id IS NOT NULL AND deleted_at IS NULL) AS new_companies;
