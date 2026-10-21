-- 受信箱「新規」バッジ: leads に「現在の担当者が開いた時刻」を追加（全テナント）
-- 設計: docs/handoff/inbox-new-assignment-badge/design.md §3-1
--
-- 意味:
--   NULL      = 現在の担当者はまだ開いていない → 受信箱に「新規」バッジを出す
--   時刻あり  = 現在の担当者が開いた → バッジを出さない
--   担当が変わったときは NULL に戻す（backend/app/routers/leads.py の update_lead）
--
-- 【再実行の安全性（重要）】
--   scripts/run_all_migrations.sh は毎デプロイで全マイグレーションを再実行する
--   （同ファイル先頭の注意書き）。起動条件は .github/workflows/deploy.yml の
--   migrations フィルタで backend/** や scripts/** も含むため、実際に何度も流れる。
--
--   そのため「列を足す」と「既存行を埋める」を **列がまだ無いときだけ** 実行する。
--   既に列があるスキーマは CONTINUE で完全にスキップする。
--
--   これを怠ると、2 回目以降の実行で
--     UPDATE ... SET assignment_opened_at = NOW() WHERE assignment_opened_at IS NULL
--   が「担当になったがまだ開いていない」行（＝バッジを出すべき行）を埋めてしまい、
--   デプロイのたびに全員のバッジが消える。審査（2026-10-15）で指摘された欠陥。
--
-- 既存行の扱い:
--   列を新設した瞬間だけ、既に担当が付いている行を NOW() で埋める。
--   埋めないと導入直後に担当付きの全会話へ「新規」が付き、意味のない大量表示になる。
--
-- 手本:
--   migrations/20260718_100000_leads_add_deal_columns.sql（全テナントループ）
--   migrations/20261013_150000_staff_email_from_users.sql:11-19（information_schema で守る）
--
-- 不可逆操作は含まない（表の削除・列の削除は行わない）。
--
-- 【assigned_to が無いスキーマへの対応（CI で実発生・2026-10-17）】
--   .github/workflows/migration-test.yml の試験用 tenant_001.leads は
--   assigned_to を持たない最小定義（本番の leads は
--   migrations/003_add_phase1_tenant_tables.sql:92 で assigned_to を持つ）。
--   つまり「leads 表はあるが assigned_to が無いスキーマ」が実在するため、
--   埋め直し UPDATE は assigned_to の有無を確認してから実行する
--   （列の追加自体は assigned_to の有無に関係なく常に行う）。
DO $$
DECLARE
    s TEXT;
    col_exists BOOLEAN;
    assigned_to_exists BOOLEAN;
BEGIN
    FOR s IN
        SELECT n.nspname
        FROM pg_namespace n
        WHERE n.nspname ~ '^tenant_[0-9]+$'
          AND EXISTS (
              SELECT 1 FROM information_schema.tables t
              WHERE t.table_schema = n.nspname
                AND t.table_name = 'leads'
          )
        ORDER BY n.nspname
    LOOP
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns c
            WHERE c.table_schema = s
              AND c.table_name = 'leads'
              AND c.column_name = 'assignment_opened_at'
        ) INTO col_exists;

        IF col_exists THEN
            RAISE NOTICE 'leads.assignment_opened_at already present on % (skip)', s;
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.leads ADD COLUMN assignment_opened_at TIMESTAMPTZ', s
        );

        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns c
            WHERE c.table_schema = s
              AND c.table_name = 'leads'
              AND c.column_name = 'assigned_to'
        ) INTO assigned_to_exists;

        IF assigned_to_exists THEN
            EXECUTE format(
                'UPDATE %I.leads SET assignment_opened_at = NOW() WHERE assigned_to IS NOT NULL', s
            );
            RAISE NOTICE 'leads.assignment_opened_at added and backfilled on %', s;
        ELSE
            RAISE NOTICE 'leads.assignment_opened_at added on % (no assigned_to column, backfill skipped)', s;
        END IF;
    END LOOP;
END $$;
