-- Migration: 20260902_110100_tcg_products_classification_ids
-- 目的: tcg_products の UUID 4 列に FK 制約を追加し、GAS 実データで全 268 行を埋める
--
-- 前提: 20260902_110000_tcg_classification_masters.sql が適用済みであること
-- 冪等性:
--   - ADD CONSTRAINT IF NOT EXISTS で重複 FK 追加を防ぐ
--   - UPDATE は同じ値への更新になっても副作用なし

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260902_110100: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- ADR-1002: tcg_products が Phase 2c で削除済みの場合はスキップ
    IF to_regclass(format('%I.tcg_products', _schema)) IS NULL THEN
        RAISE NOTICE 'ADR-1002: tcg_products は Phase 2c で削除済み、スキップ: %', _schema;
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- 1. tcg_products 4 UUID 列に FK 制約を追加（IF NOT EXISTS）
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_division_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_division_id
                    FOREIGN KEY (division_id)
                    REFERENCES %I.tcg_major_categories (id)
        $q$, _schema, _schema);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_work_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_work_id
                    FOREIGN KEY (work_id)
                    REFERENCES %I.tcg_series (id)
        $q$, _schema, _schema);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_manufacturer_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_manufacturer_id
                    FOREIGN KEY (manufacturer_id)
                    REFERENCES %I.tcg_manufacturers (id)
        $q$, _schema, _schema);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_product_category_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_product_category_id
                    FOREIGN KEY (product_category_id)
                    REFERENCES %I.tcg_product_categories (id)
        $q$, _schema, _schema);
    END IF;

    -- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-09):
    -- 全 268 商品の分類 ID を埋める UPDATE と、埋まったことの検証（RAISE EXCEPTION）を外した。
    -- 元の内容は git history で参照可能。

    RAISE NOTICE '20260902_110100: ADR-1007 neutralized: FK constraints added, classification fill removed in schema %', _schema;
END $$;
