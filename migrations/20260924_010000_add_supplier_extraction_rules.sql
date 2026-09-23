-- 仕入元ごとの抽出ルール列追加
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_price_format TEXT;
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_qty_format TEXT;
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_order_pattern TEXT;
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_default_unit TEXT;
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_notes TEXT;
