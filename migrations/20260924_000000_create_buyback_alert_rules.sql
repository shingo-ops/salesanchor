-- ADR-157: 買取価格変動アラートルール
-- public スキーマ（buyback_shop_products と同じ）
-- CI test DB では buyback_shop_products が未作成の場合があるため DO $$ ガードで保護
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'buyback_shop_products'
  ) THEN
    RAISE NOTICE 'buyback_shop_products does not exist, creating buyback_alert_rules without FK';
    CREATE TABLE IF NOT EXISTS public.buyback_alert_rules (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        card_game TEXT,
        shop_code TEXT,
        product_type TEXT,
        shop_product_id UUID,
        direction TEXT NOT NULL DEFAULT 'down' CHECK (direction IN ('down', 'up', 'both')),
        threshold_pct NUMERIC(5,2) NOT NULL CHECK (threshold_pct > 0),
        price_grade TEXT NOT NULL DEFAULT 'price_s' CHECK (price_grade IN ('price_s', 'price_a', 'price_am', 'price_b', 'price_c')),
        is_active BOOLEAN NOT NULL DEFAULT true,
        last_notified_at TIMESTAMPTZ,
        cooldown_minutes INTEGER NOT NULL DEFAULT 360,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  ELSE
    CREATE TABLE IF NOT EXISTS public.buyback_alert_rules (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        card_game TEXT,
        shop_code TEXT,
        product_type TEXT,
        shop_product_id UUID REFERENCES public.buyback_shop_products(id),
        direction TEXT NOT NULL DEFAULT 'down' CHECK (direction IN ('down', 'up', 'both')),
        threshold_pct NUMERIC(5,2) NOT NULL CHECK (threshold_pct > 0),
        price_grade TEXT NOT NULL DEFAULT 'price_s' CHECK (price_grade IN ('price_s', 'price_a', 'price_am', 'price_b', 'price_c')),
        is_active BOOLEAN NOT NULL DEFAULT true,
        last_notified_at TIMESTAMPTZ,
        cooldown_minutes INTEGER NOT NULL DEFAULT 360,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_buyback_alert_rules_active
    ON public.buyback_alert_rules (is_active) WHERE is_active = true;
