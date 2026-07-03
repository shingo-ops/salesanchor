-- 便2: order_items 新設＋仕入接続（既存テナント向け・冪等・全スキーマループ）
DO $$
DECLARE s RECORD; tid INT;
BEGIN
  FOR s IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname LOOP
    tid := regexp_replace(s.nspname, '\D', '', 'g')::INT;
    EXECUTE format($q$
      CREATE OR REPLACE FUNCTION %I.trg_set_updated_at()
      RETURNS TRIGGER AS $fn$
      BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
      END;
      $fn$ LANGUAGE plpgsql
    $q$, s.nspname);
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I.order_items (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER NOT NULL DEFAULT %s,
        order_id INTEGER NOT NULL,
        product_id INTEGER REFERENCES public.products(id),
        product_name VARCHAR(255) NOT NULL,
        name_en VARCHAR(255),
        condition VARCHAR(50),
        unit VARCHAR(20),
        sku VARCHAR(100),
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price NUMERIC(15,2) NOT NULL,
        subtotal NUMERIC(15,2) NOT NULL,
        weight NUMERIC(10,3),
        hs_code VARCHAR(20),
        usd_unit_value NUMERIC(15,2),
        exchange_rate_usd NUMERIC(12,4),
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())', s.nspname, tid, s.nspname);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON %I.order_items (order_id)', s.nspname);
    IF to_regclass(format('%I.orders', s.nspname)) IS NOT NULL THEN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint con JOIN pg_namespace n ON n.oid = con.connamespace
                     WHERE con.conname = 'fk_order_items_order' AND n.nspname = s.nspname) THEN
        EXECUTE format('ALTER TABLE %I.order_items ADD CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES %I.orders(id) ON DELETE CASCADE', s.nspname, s.nspname);
      END IF;
    END IF;
    EXECUTE format('ALTER TABLE %I.order_items ENABLE ROW LEVEL SECURITY', s.nspname);
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = s.nspname AND tablename = 'order_items' AND policyname = 'tenant_isolation_order_items') THEN
      EXECUTE format('CREATE POLICY tenant_isolation_order_items ON %I.order_items USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', s.nspname);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE t.tgname = 'trg_order_items_updated_at' AND n.nspname = s.nspname) THEN
      EXECUTE format('CREATE TRIGGER trg_order_items_updated_at BEFORE UPDATE ON %I.order_items FOR EACH ROW EXECUTE FUNCTION %I.trg_set_updated_at()', s.nspname, s.nspname);
    END IF;
    EXECUTE format('ALTER TABLE %I.purchase_orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ', s.nspname);
    EXECUTE format('ALTER TABLE %I.purchase_orders ADD COLUMN IF NOT EXISTS shipping_fee NUMERIC(15,2) DEFAULT 0', s.nspname);
    EXECUTE format('ALTER TABLE %I.purchase_order_items ADD COLUMN IF NOT EXISTS order_item_id INTEGER', s.nspname);
    IF NOT EXISTS (SELECT 1 FROM pg_constraint con JOIN pg_namespace n ON n.oid = con.connamespace
                   WHERE con.conname = 'fk_poi_order_item' AND n.nspname = s.nspname) THEN
      EXECUTE format('ALTER TABLE %I.purchase_order_items ADD CONSTRAINT fk_poi_order_item FOREIGN KEY (order_item_id) REFERENCES %I.order_items(id)', s.nspname, s.nspname);
    END IF;
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_poi_order_item_id ON %I.purchase_order_items (order_item_id)', s.nspname);
  END LOOP;
END $$;
