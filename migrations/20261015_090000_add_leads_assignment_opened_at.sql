-- 受信箱「新規」バッジ: leads に「現在の担当者が開いた時刻」を追加（全テナント・冪等）
-- 設計: docs/handoff/inbox-new-assignment-badge/design.md §3-1
--
-- 意味:
--   NULL      = 現在の担当者はまだ開いていない → 受信箱に「新規」バッジを出す
--   時刻あり  = 現在の担当者が開いた → バッジを出さない
--   担当が変わったときは NULL に戻す（backend/app/routers/leads.py の update_lead）
--
-- 既存行の扱い:
--   既に担当が付いている行は NOW() で埋める。埋めないと本番反映の瞬間に
--   担当付きの全会話へ「新規」が付き、意味のない大量表示になる（設計 KGI K6）。
--
-- 冪等性:
--   ADD COLUMN IF NOT EXISTS ＋ UPDATE ... WHERE assignment_opened_at IS NULL
--   のため何度流しても同じ結果になる。
--
-- 手本: migrations/20260718_100000_leads_add_deal_columns.sql（全テナントループ）
--       migrations/032_add_company_contact_to_downstream.sql:124（既存行の埋め直し）
--
-- 不可逆操作は含まない（DROP COLUMN / DROP TABLE なし）。
DO $$
DECLARE
    s TEXT;
BEGIN
    FOR s IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.leads ADD COLUMN IF NOT EXISTS assignment_opened_at TIMESTAMPTZ',
            s
        );
        EXECUTE format(
            'UPDATE %I.leads SET assignment_opened_at = NOW() '
            'WHERE assigned_to IS NOT NULL AND assignment_opened_at IS NULL',
            s
        );
        RAISE NOTICE 'leads.assignment_opened_at ready on %', s;
    END LOOP;
END $$;
