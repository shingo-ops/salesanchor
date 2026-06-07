-- Migration: 全テナントに own_inventory テーブルを作成
--
-- 目的 (ADR SA-04/05):
--   A在庫（自社保有在庫）をテナント専用スキーマに分離して管理する。
--   B在庫（public.inventory, 仕入元フィード）とは完全に別テーブル。
--
--   物理在庫数(physical_qty) / 引当済み(reserved_qty) / 利用可能(available_qty) の
--   2段階引当モデルを実装する。
--
-- 影響テーブル: {tenant_NNN}.own_inventory（新規作成）
-- 適用対象: 全テナント（pg_namespace 走査で冪等適用）
-- 冪等: CREATE TABLE IF NOT EXISTS + DO ブロックでポリシー重複チェック

DO $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Processing schema: %', schema_record.schema_name;

        -- own_inventory テーブルを作成
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.own_inventory (
                id             SERIAL PRIMARY KEY,
                tenant_id      INTEGER      NOT NULL,
                product_id     INTEGER      NOT NULL REFERENCES public.products(id),
                physical_qty   INTEGER      NOT NULL DEFAULT 0 CHECK (physical_qty >= 0),
                reserved_qty   INTEGER      NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
                available_qty  INTEGER GENERATED ALWAYS AS (physical_qty - reserved_qty) STORED,
                unit_price     NUMERIC(15,2),
                condition      VARCHAR(50),
                status         VARCHAR(20)  NOT NULL DEFAULT ''active''
                               CHECK (status IN (''active'',''inactive'',''sold_out'')),
                note_ja        TEXT,
                note_en        TEXT,
                antique_ledger_id INTEGER,
                created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)
            )',
            schema_record.schema_name
        );

        -- テーブルコメント
        EXECUTE format(
            'COMMENT ON TABLE %I.own_inventory IS
             ''ADR SA-04/05: A在庫（自社保有）。B在庫（public.inventory）とは完全分離。''',
            schema_record.schema_name
        );

        -- RLS 有効化（冪等: 既に有効でもエラーにならない）
        EXECUTE format(
            'ALTER TABLE %I.own_inventory ENABLE ROW LEVEL SECURITY',
            schema_record.schema_name
        );

        -- RLS ポリシー（冪等: pg_policies で存在確認）
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE schemaname = schema_record.schema_name
              AND tablename  = 'own_inventory'
              AND policyname = 'own_inventory_tenant_isolation'
        ) THEN
            EXECUTE format(
                'CREATE POLICY own_inventory_tenant_isolation ON %I.own_inventory
                 USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)',
                schema_record.schema_name
            );
        END IF;

    END LOOP;
END
$$;
