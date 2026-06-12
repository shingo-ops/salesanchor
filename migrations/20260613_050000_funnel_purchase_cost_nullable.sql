-- Migration 105: order_financials.purchase_cost を NULL 許容・DEFAULT 削除
--              （ファネルダッシュボード PR1）
--
-- 目的:
--   purchase_cost の DEFAULT 0 を削除し NULL 許容に変更する。
--   - NULL  = 未入力（仕入原価を把握していない）
--   - 0     = 実際に仕入原価がゼロ（e.g. 自社製品）
--   これにより粗利のカバレッジ注記（§2a）が NULL 件数ベースで正確に機能する。
--
-- 設計判断:
--   - ADR-138: PO確定事項 §2a。既存29件は全件 purchase_cost > 0 確認済み（2026-06-12計測）。
--   - 既存レコードの値は変更しない（ALTER COLUMN ... DROP DEFAULT のみ）。
--   - 他の原価カラム（purchase_shipping, paypal_fee 等）は今回対象外（第2弾判断）。
--
-- 冪等性:
--   - ALTER COLUMN SET NOT NULL を外すため、すでに NULL 許容なら pg_attribute で確認してスキップ。
--   - ALTER COLUMN DROP DEFAULT は重複実行しても安全。
-- 適用対象: 全テナント
-- 作成日: 2026-06-12
-- 関連: docs/handoff/funnel-dashboard-stage1/design.md §2a
--       docs/adr/ADR-138-funnel-dashboard-stage1.md §D1

DO $$
DECLARE
    schema_rec  RECORD;
    col_nullable TEXT;
    has_default BOOLEAN;
BEGIN
    FOR schema_rec IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Migration 105: processing schema %', schema_rec.schema_name;

        -- order_financials テーブルの存在確認
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.schema_name
              AND table_name   = 'order_financials'
        ) THEN
            RAISE NOTICE '  order_financials テーブルが存在しません。スキップ。';
            CONTINUE;
        END IF;

        -- 現在の NULL 許容状態と DEFAULT の確認
        SELECT is_nullable INTO col_nullable
        FROM information_schema.columns
        WHERE table_schema = schema_rec.schema_name
          AND table_name   = 'order_financials'
          AND column_name  = 'purchase_cost';

        SELECT column_default IS NOT NULL INTO has_default
        FROM information_schema.columns
        WHERE table_schema = schema_rec.schema_name
          AND table_name   = 'order_financials'
          AND column_name  = 'purchase_cost';

        -- NOT NULL 制約を DROP（NULL 許容化）
        IF col_nullable = 'NO' THEN
            EXECUTE format(
                'ALTER TABLE %I.order_financials
                 ALTER COLUMN purchase_cost DROP NOT NULL',
                schema_rec.schema_name
            );
            RAISE NOTICE '  purchase_cost: NOT NULL 制約を削除しました。';
        ELSE
            RAISE NOTICE '  purchase_cost: すでに NULL 許容です。スキップ。';
        END IF;

        -- DEFAULT 0 を削除（NULL = 未入力を区別するため）
        IF has_default THEN
            EXECUTE format(
                'ALTER TABLE %I.order_financials
                 ALTER COLUMN purchase_cost DROP DEFAULT',
                schema_rec.schema_name
            );
            RAISE NOTICE '  purchase_cost: DEFAULT を削除しました。';
        ELSE
            RAISE NOTICE '  purchase_cost: DEFAULT なし。スキップ。';
        END IF;

    END LOOP;
    RAISE NOTICE 'Migration 105: complete';
END
$$;
