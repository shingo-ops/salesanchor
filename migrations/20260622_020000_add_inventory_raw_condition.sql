-- 20260622_020000_add_inventory_raw_condition.sql
-- public.inventory に raw_condition を追加する additive migration。
-- 段階1の地盤: 既存 condition を壊さず、原文の根拠テキストを保持するための列。

ALTER TABLE public.inventory
    ADD COLUMN IF NOT EXISTS raw_condition TEXT;
