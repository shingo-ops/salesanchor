-- SA-18 Phase2 前提条件修正: RLS ポリシーの変数名誤りを修正
--
-- 背景:
--   conversation_logs と own_inventory の RLS ポリシーが
--   current_setting('app.current_tenant_id') を参���しているが、
--   アプリ（get_current_tenant dependency）が実際に SET するのは
--   'app.tenant_id'（missing_ok=true 付き）。
--
--   'app.current_tenant_id' はコード中で一度も SET されないため、
--   salesanchor_app（NOBYPASSRLS）でこれらのテーブルを参照すると
--   "unrecognized configuration parameter" エラーになり 500 が発生する。
--   jarvis（BYPASSRLS）では RLS が評価されないため顕在化しない。
--
-- 修正内容:
--   両テーブルのポリシーを DROP して正しい変数名・missing_ok=true で再作成す���。
--   参��パター��は smoke[5] を通過した translation_glossary RLS ポリシー
--   （20260605_010000_rls_translation_glossary.sql）と完���一致させる。
--
-- 正しいパターン:
--   current_setting('app.tenant_id', true)::INTEGER
--   ↑ missing_ok=true: 変数未設定時は NULL を返す（エ��ーではなくフェイルクローズ）
--
-- 冪等性:
--   DROP POLICY IF EXISTS + IF NOT EXISTS チェックで再実行無害
--
-- 作成日: 2026-06-07

-- ─── conversation_logs ───────────────────────────────────────────────────────

DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- 誤ったポリシーを削除（IF EXISTS で存在しなくても無害）
        EXECUTE format(
            'DROP POLICY IF EXISTS conversation_logs_tenant_isolation ON %I.conversation_logs',
            r.nspname
        );

        -- 正��い変数名・missing_ok=true で再作成
        -- テーブルが存在しないスキーマはスキップ
        IF EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = r.nspname AND tablename = 'conversation_logs'
        ) THEN
            EXECUTE format($q$
                CREATE POLICY conversation_logs_tenant_isolation ON %I.conversation_logs
                    USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)
            $q$, r.nspname);
            RAISE NOTICE 'fix-rls: %.conversation_logs ポリシー再作成完了', r.nspname;
        END IF;
    END LOOP;
END $$;

-- ─── own_inventory ──────────────────────────────────────────────────────────

DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        EXECUTE format(
            'DROP POLICY IF EXISTS own_inventory_tenant_isolation ON %I.own_inventory',
            r.nspname
        );

        IF EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = r.nspname AND tablename = 'own_inventory'
        ) THEN
            EXECUTE format($q$
                CREATE POLICY own_inventory_tenant_isolation ON %I.own_inventory
                    USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)
            $q$, r.nspname);
            RAISE NOTICE 'fix-rls: %.own_inventory ポリシー再作成完了', r.nspname;
        END IF;
    END LOOP;
END $$;
