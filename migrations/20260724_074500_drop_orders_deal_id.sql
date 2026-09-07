-- orders.deal_id と対応するFKを全tenantから削除する（冪等）
DO $$
DECLARE
  s RECORD;
  table_exists BOOLEAN;
  column_exists BOOLEAN;
  fk_exists BOOLEAN;
  applied_count INTEGER := 0;
  skipped_count INTEGER := 0;
  orders_rows BIGINT;
BEGIN
  FOR s IN
    SELECT nspname
    FROM pg_namespace
    WHERE nspname ~ '^tenant_[0-9]+$'
    ORDER BY nspname
  LOOP
    SELECT to_regclass(format('%I.orders', s.nspname)) IS NOT NULL
      INTO table_exists;

    IF NOT table_exists THEN
      skipped_count := skipped_count + 1;
      RAISE NOTICE '[orders.deal_id] %: orders table not found; skipped', s.nspname;
      CONTINUE;
    END IF;

    SELECT EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = s.nspname
        AND table_name = 'orders'
        AND column_name = 'deal_id'
    ) INTO column_exists;

    SELECT EXISTS (
      SELECT 1
      FROM pg_constraint c
      JOIN pg_class r ON r.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = r.relnamespace
      WHERE n.nspname = s.nspname
        AND r.relname = 'orders'
        AND c.conname = 'orders_deal_id_fkey'
    ) INTO fk_exists;

    IF NOT column_exists AND NOT fk_exists THEN
      skipped_count := skipped_count + 1;
      RAISE NOTICE '[orders.deal_id] %: deal_id column and FK not found; skipped', s.nspname;
      CONTINUE;
    END IF;

    IF fk_exists THEN
      EXECUTE format('ALTER TABLE %I.orders DROP CONSTRAINT orders_deal_id_fkey', s.nspname);
    END IF;

    IF column_exists THEN
      EXECUTE format('ALTER TABLE %I.orders DROP COLUMN deal_id', s.nspname);
    END IF;

    EXECUTE format('SELECT count(*) FROM %I.orders', s.nspname) INTO orders_rows;
    applied_count := applied_count + 1;
    RAISE NOTICE '[orders.deal_id] %: applied (orders_rows=%)', s.nspname, orders_rows;
  END LOOP;

  RAISE NOTICE '[orders.deal_id] summary: applied=%, skipped=%', applied_count, skipped_count;
END $$;
