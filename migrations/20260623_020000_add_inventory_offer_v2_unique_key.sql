-- 20260623_020000_add_inventory_offer_v2_unique_key.sql
-- 2b: condition ベースの旧キーを軸列ベースへ移行するための新 UNIQUE index。
--
-- 重要:
-- - runner は transaction で包まない前提（scripts/run_all_migrations.sh を確認）
-- - 実適用前に read-only 衝突チェックを必須とする
--   SELECT supplier_id, product_id, COALESCE(seal, ''), COALESCE(search_cond, ''),
--          COALESCE(grade, ''), damage, COALESCE(unit, ''), offer_type,
--          COALESCE(ship_timing, ''), COUNT(*)
--   FROM public.inventory
--   GROUP BY 1,2,3,4,5,6,7,8,9
--   HAVING COUNT(*) > 1;
--
-- 先に新キーを作成し、検証後に旧キーを外す。

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_inventory_offer_v2
    ON public.inventory (
        supplier_id,
        product_id,
        COALESCE(seal, ''),
        COALESCE(search_cond, ''),
        COALESCE(grade, ''),
        damage,
        COALESCE(unit, ''),
        offer_type,
        COALESCE(ship_timing, '')
    );

DROP INDEX IF EXISTS uq_inventory_offer_key;
