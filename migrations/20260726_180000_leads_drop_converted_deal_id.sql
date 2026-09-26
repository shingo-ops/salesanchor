-- leads.converted_deal_id と対応するFKを全tenantから削除する（冪等）
DO $$
DECLARE
  s RECORD;
  table_exists BOOLEAN;
  column_exists BOOLEAN;
  fk_exists BOOLEAN;
  applied_count INTEGER := 0;
  skipped_count INTEGER := 0;
  leads_rows BIGINT;
BEGIN
  FOR s IN
    SELECT nspname
    FROM pg_namespace
    WHERE nspname ~ '^tenant_[0-9]+$'
    ORDER BY nspname
  LOOP
    SELECT to_regclass(format('%I.leads', s.nspname)) IS NOT NULL
      INTO table_exists;
    IF NOT table_exists THEN
      skipped_count := skipped_count + 1;
      RAISE NOTICE '[leads.converted_deal_id] %: leads table not found; skipped', s.nspname;
      CONTINUE;
    END IF;

    SELECT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = s.nspname AND table_name = 'leads' AND column_name = 'converted_deal_id'
    ) INTO column_exists;
    SELECT EXISTS (
      SELECT 1 FROM pg_constraint c
      JOIN pg_class r ON r.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = r.relnamespace
      WHERE n.nspname = s.nspname AND r.relname = 'leads' AND c.conname = 'fk_leads_converted_deal'
    ) INTO fk_exists;

    IF NOT column_exists AND NOT fk_exists THEN
      skipped_count := skipped_count + 1;
      RAISE NOTICE '[leads.converted_deal_id] %: column and FK not found; skipped', s.nspname;
      CONTINUE;
    END IF;
    IF fk_exists THEN
      EXECUTE format('ALTER TABLE %I.leads DROP CONSTRAINT fk_leads_converted_deal', s.nspname);
    END IF;
    IF column_exists THEN
      EXECUTE format('ALTER TABLE %I.leads DROP COLUMN converted_deal_id', s.nspname);
    END IF;
    EXECUTE format('SELECT count(*) FROM %I.leads', s.nspname) INTO leads_rows;
    applied_count := applied_count + 1;
    RAISE NOTICE '[leads.converted_deal_id] %: applied (leads_rows=%)', s.nspname, leads_rows;
  END LOOP;
  RAISE NOTICE '[leads.converted_deal_id] summary: applied=%, skipped=%', applied_count, skipped_count;
END $$;
