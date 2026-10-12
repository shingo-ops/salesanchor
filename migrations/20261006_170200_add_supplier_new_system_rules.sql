-- 新しい仕組み（v8以降の書き写し）だけが読む仕入元ルールの欄を2つ足す。本番 v7 は読まない。
-- 既存の extraction_* 列と同じ作法（TEXT, ADD COLUMN IF NOT EXISTS）。既存の行の値は触らない（NULL のまま）。
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_layout_rules TEXT;
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_hard_cases TEXT;
