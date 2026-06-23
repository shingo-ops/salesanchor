-- 20260623_020000_create_inventory_offer_v2_unique_key.sql
-- 2b 前提: condition ベースの旧キーを軸列ベースへ移行するための新 UNIQUE index を作成する。
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
-- この migration は「新キー作成」のみ。旧キー削除は別 migration に分割する。

-- migration-test.yml の現行-era ベースラインでは 20260602 系が走らないため、
-- この migration 単体で評価できるよう、旧列が未存在なら安全に追加する。
ALTER TABLE public.inventory ADD COLUMN IF NOT EXISTS offer_type VARCHAR(20) NOT NULL DEFAULT 'in_stock';
ALTER TABLE public.inventory ADD COLUMN IF NOT EXISTS ship_timing VARCHAR(20);

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
