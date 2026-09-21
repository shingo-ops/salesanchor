-- ADR-157: Create buyback price logger tables
-- 外部買取店（シンソク / 買取ホムラ）の価格を定期取得して蓄積するテーブル。
-- public スキーマに配置（テナント横断の共用データ）。

CREATE TABLE IF NOT EXISTS public.buyback_shop_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shop_code TEXT NOT NULL,
  external_product_id TEXT NOT NULL,
  product_name TEXT NOT NULL,
  card_game TEXT NOT NULL,
  product_type TEXT,
  image_url TEXT,
  -- 将来の自社商品マスタとのリンク用（当初は NULL）
  product_id UUID NULL,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(shop_code, external_product_id)
);

CREATE TABLE IF NOT EXISTS public.buyback_price_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shop_product_id UUID NOT NULL REFERENCES public.buyback_shop_products(id),
  -- シンソク: price_s/a/am/b/c に対応（S=美品〜C=可）
  -- 買取ホムラ: price_s のみ使用（単一価格）
  price_s INTEGER,
  price_a INTEGER,
  price_am INTEGER,
  price_b INTEGER,
  price_c INTEGER,
  fetched_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_buyback_price_logs_product_time
  ON public.buyback_price_logs(shop_product_id, fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_buyback_shop_products_shop_game
  ON public.buyback_shop_products(shop_code, card_game);
