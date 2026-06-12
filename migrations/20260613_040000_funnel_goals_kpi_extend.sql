-- Migration 104: goals.kpi_type CHECK 制約拡張（ファネルダッシュボード PR1）
--
-- 目的:
--   ファネルダッシュボードに必要な指標を goals テーブルの kpi_type として追加する。
--   - won_count  : 成約件数（既存 deal_count は商談作成数。別指標として追加）
--   - gross_profit: 粗利目標（§2a 第1弾掲載決定）
--
-- 設計判断:
--   - ADR-138 §D1-4: kpi_type の CHECK 制約は PostgreSQL システムカタログから
--     制約名を動的に取得して DROP & ADD を行う（inline CHECK のため名前が自動生成）。
--   - 既存 goals レコードへの影響なし（制約値の追加のみ）。
--
-- 冪等性:
--   - 既に新制約が存在する場合はスキップ（pg_constraint で確認）。
-- 適用対象: 全テナント
-- 作成日: 2026-06-12
-- 関連: docs/handoff/funnel-dashboard-stage1/design.md §2.4
--       docs/adr/ADR-138-funnel-dashboard-stage1.md §D1-4

DO $$
DECLARE
    schema_rec      RECORD;
    constraint_name TEXT;
    already_updated BOOLEAN;
BEGIN
    FOR schema_rec IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Migration 104: processing schema %', schema_rec.schema_name;

        -- goals テーブルが存在しない場合はスキップ
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.schema_name
              AND table_name   = 'goals'
        ) THEN
            RAISE NOTICE '  goals テーブルが存在しません。スキップ。';
            CONTINUE;
        END IF;

        -- 既に won_count が含まれているか確認（冪等性）
        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = schema_rec.schema_name
              AND t.relname = 'goals'
              AND c.contype = 'c'
              AND pg_get_constraintdef(c.oid) LIKE '%won_count%'
        ) INTO already_updated;

        IF already_updated THEN
            RAISE NOTICE '  kpi_type 制約は既に更新済み。スキップ。';
            CONTINUE;
        END IF;

        -- kpi_type の既存 CHECK 制約名を取得
        SELECT c.conname INTO constraint_name
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = schema_rec.schema_name
          AND t.relname = 'goals'
          AND c.contype = 'c'
          AND pg_get_constraintdef(c.oid) LIKE '%kpi_type%'
          AND pg_get_constraintdef(c.oid) NOT LIKE '%owner_check%'
        LIMIT 1;

        -- 既存 CHECK 制約を DROP
        IF constraint_name IS NOT NULL THEN
            EXECUTE format(
                'ALTER TABLE %I.goals DROP CONSTRAINT IF EXISTS %I',
                schema_rec.schema_name,
                constraint_name
            );
            RAISE NOTICE '  DROP 制約: %', constraint_name;
        ELSE
            RAISE WARNING '  kpi_type の CHECK 制約が見つかりません（schema: %）', schema_rec.schema_name;
        END IF;

        -- 新 CHECK 制約を追加（既存5値 + won_count + gross_profit）
        EXECUTE format($sql$
            ALTER TABLE %I.goals
            ADD CONSTRAINT goals_kpi_type_check
            CHECK (kpi_type IN (
                'revenue',
                'deal_count',
                'close_rate',
                'lead_count',
                'conversion_rate',
                'won_count',
                'gross_profit'
            ))
        $sql$, schema_rec.schema_name);

        RAISE NOTICE '  kpi_type 制約を更新しました。';
    END LOOP;
    RAISE NOTICE 'Migration 104: complete';
END
$$;
