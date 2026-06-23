-- 20260623_050000_drop_inventory_condition.sql
-- public.inventory.condition を削除する最終段の migration。
--
-- 注意:
-- - これは手動 GO 専用。run_all_migrations.sh では自動実行しない。
-- - 先に condition を参照するコードをすべて軸列へ切り替え、
--   nullable 化と backfill を完了させた後にだけ適用する。

ALTER TABLE public.inventory
    DROP COLUMN condition;
