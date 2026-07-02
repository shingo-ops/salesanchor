-- 便1b: conversation_logs の背骨必須化 — 遡及lead逆造成 + 条件付き SET NOT NULL
DO $$
DECLARE s RECORD; n_left INT;
BEGIN
  FOR s IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname LOOP
    -- (1) 宛名なし会話 → チャネル識別子ごとに遡及leadを作成し紐づけ（決定的）
    EXECUTE format($f$
      WITH orphan AS (
        SELECT DISTINCT ON (channel_type, channel_identity)
               channel_type, channel_identity, tenant_id,
               CASE WHEN direction = 'inbound' THEN 'inbound' ELSE 'outbound' END AS init
        FROM %I.conversation_logs WHERE lead_id IS NULL AND channel_identity IS NOT NULL
        ORDER BY channel_type, channel_identity, occurred_at ASC
      ),
      created AS (
        INSERT INTO %I.leads (
          tenant_id, customer_name, channel_type, channel_identity, initiative, status, notes
        )
        SELECT
          tenant_id,
          COALESCE(channel_identity, 'unknown'),
          channel_type,
          channel_identity,
          init,
          'lead',
          '[便1b] 遡及作成: 宛名なし会話ログの出自lead'
        FROM orphan
        RETURNING id, channel_type, channel_identity
      )
      UPDATE %I.conversation_logs cl
         SET lead_id = cr.id
        FROM created cr
       WHERE cl.lead_id IS NULL
         AND cl.channel_type = cr.channel_type
         AND cl.channel_identity = cr.channel_identity
    $f$, s.nspname, s.nspname, s.nspname);

    -- (2) 違反0のスキーマのみ NOT NULL（残ればNOTICE: 006のDEMO email 等 channel_identity NULL 行）
    EXECUTE format('SELECT count(*) FROM %I.conversation_logs WHERE lead_id IS NULL', s.nspname) INTO n_left;
    IF n_left = 0 THEN
      EXECUTE format('ALTER TABLE %I.conversation_logs ALTER COLUMN lead_id SET NOT NULL', s.nspname);
    ELSE
      RAISE NOTICE '[ben1b] % : conversation_logs.lead_id NULL % 件のためスキップ（DEMO削除後に再実行）', s.nspname, n_left;
    END IF;
  END LOOP;
END $$;
