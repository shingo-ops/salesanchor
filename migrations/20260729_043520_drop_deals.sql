-- 便E: DROP TABLE deals（全テナント）
-- 本番適用済み: 2026-07-29 JST
-- GO受領: 2026-07-28 / Shingo
-- バックアップ: /home/ubuntu/backups/postgres/pre_drop_deals_20260729_042503.dump (2.4M)
--
-- 前提（実測確認済み）:
--   - deals を指すFK: 0件
--   - deals を参照するビュー（v_company_stats 付け替え済み・全テナント）: 0件
--   - deals を参照する関数・トリガー・ルール: 0件
--   - deals 行数: tenant_006=18（QAデモ）・他0
-- CASCADE なし（依存ゼロ実証済み）
-- 冪等: deals テーブルが存在しないテナントはスキップ

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname
              AND tablename = 'deals'
        ) THEN
            RAISE NOTICE '便E: %.deals が存在しない、スキップ（冪等）', schema_rec.nspname;
            CONTINUE;
        END IF;

        EXECUTE format('DROP TABLE %I.deals', schema_rec.nspname);
        RAISE NOTICE '便E: %.deals DROP完了', schema_rec.nspname;
    END LOOP;
END $$;
