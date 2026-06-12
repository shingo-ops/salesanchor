-- Migration 101: deals.closed_at 追加（ファネルダッシュボード PR1）
--
-- 目的:
--   成約・失注の確定タイムスタンプを記録する。
--   過去データはバックフィルしない（NULL のまま = 集計対象外）。
--   won/lost 遷移時に deals.py PATCH で closed_at = NOW() をセットする（PR3 で実装）。
--
-- 設計判断:
--   - ADR-138 §D1-1: バックフィルなし。過去分は closed_at IS NULL で集計対象外と明記。
--   - クリーンスレート方針（PO宣言 2026-06-12）: 既存 won/lost レコードは近似不要。
--
-- 冪等性: ADD COLUMN IF NOT EXISTS で再実行可能。
-- 適用対象: 全テナント
-- 作成日: 2026-06-12
-- 関連: docs/handoff/funnel-dashboard-stage1/design.md §2.1
--       docs/adr/ADR-138-funnel-dashboard-stage1.md §D1-1

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Migration 101: adding deals.closed_at to schema %', schema_rec.schema_name;

        EXECUTE format(
            'ALTER TABLE %I.deals
             ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ',
            schema_rec.schema_name
        );

        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_deals_closed_at
             ON %I.deals (closed_at)
             WHERE closed_at IS NOT NULL',
            schema_rec.schema_name
        );
    END LOOP;
    RAISE NOTICE 'Migration 101: complete';
END
$$;
