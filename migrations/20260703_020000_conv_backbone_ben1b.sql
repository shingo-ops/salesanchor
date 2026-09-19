-- 便1b: conversation_logs の背骨必須化 — 遡及lead逆造成 + 条件付き SET NOT NULL
-- 冪等・全テナントループ。leads への INSERT は全テナント実証済みの最小列のみ使用（便1a同型）
DO $$
DECLARE s RECORD; v_ct TEXT; v_ci TEXT; v_tid INT; v_dir TEXT; v_lead INT; n_left INT;
BEGIN
  FOR s IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname LOOP
    -- (1) 宛名なし会話 → 識別子ごとに遡及leadを1件ずつ作成し紐づけ（最小列・1件ループ）
    LOOP
      EXECUTE format('SELECT channel_type, channel_identity, tenant_id, direction FROM %I.conversation_logs WHERE lead_id IS NULL AND channel_identity IS NOT NULL ORDER BY occurred_at ASC LIMIT 1', s.nspname)
        INTO v_ct, v_ci, v_tid, v_dir;
      EXIT WHEN v_ci IS NULL;
      EXECUTE format('INSERT INTO %I.leads (tenant_id, customer_name, status, notes) VALUES ($1, $2, ''lead'', $3) RETURNING id', s.nspname)
        INTO v_lead
        USING v_tid, COALESCE(v_ci, 'unknown'),
              '[便1b] 遡及作成: 宛名なし会話ログの出自lead（channel=' || v_ct || ' / identity=' || v_ci || ' / 初回direction=' || COALESCE(v_dir, '-') || '）';
      EXECUTE format('UPDATE %I.conversation_logs SET lead_id = $1 WHERE lead_id IS NULL AND channel_type = $2 AND channel_identity = $3', s.nspname)
        USING v_lead, v_ct, v_ci;
      v_ct := NULL; v_ci := NULL; v_tid := NULL; v_dir := NULL; v_lead := NULL;
    END LOOP;
    -- (2) 違反0のスキーマのみ NOT NULL（残ればNOTICE: identity無し行・DEMO等）
    EXECUTE format('SELECT count(*) FROM %I.conversation_logs WHERE lead_id IS NULL', s.nspname) INTO n_left;
    IF n_left = 0 THEN
      EXECUTE format('ALTER TABLE %I.conversation_logs ALTER COLUMN lead_id SET NOT NULL', s.nspname);
    ELSE
      RAISE NOTICE '[ben1b] % : conversation_logs.lead_id NULL % 件のためスキップ（DEMO削除後に再実行）', s.nspname, n_left;
    END IF;
  END LOOP;
END $$;
