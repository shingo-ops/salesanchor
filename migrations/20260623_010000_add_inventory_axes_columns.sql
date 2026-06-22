-- 20260623_010000_add_inventory_axes_columns.sql
-- public.inventory に多軸列を追加する additive migration。

ALTER TABLE public.inventory
    ADD COLUMN IF NOT EXISTS seal VARCHAR(20),
    ADD COLUMN IF NOT EXISTS search_cond VARCHAR(20),
    ADD COLUMN IF NOT EXISTS grade VARCHAR(20),
    ADD COLUMN IF NOT EXISTS damage BOOLEAN NOT NULL DEFAULT FALSE;

