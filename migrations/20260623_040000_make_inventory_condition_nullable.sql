-- 20260623_040000_make_inventory_condition_nullable.sql
-- public.inventory.condition を NULL 許容にして、段階的な退役の準備をする。
-- condition 列の実削除は後続の別 GO で手動適用する。

ALTER TABLE public.inventory
    ALTER COLUMN condition DROP NOT NULL;
