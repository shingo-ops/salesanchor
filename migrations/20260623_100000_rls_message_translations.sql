-- SA-18 Phase2 ③-b(5): tenant スキーマ message_translations に RLS を有効化
--
-- 背景:
--   ③-a で tenant_id 列を追加・backfill（全テナント NULL ゼロ確認済み）。
--   ③-b(4) で salesanchor_app 接続切替完了（bypassrls=false、42501 ゼロ確認済み）。
--   残る message_translations は RLS 未設定のため DB 直接アクセス時の保護がなかった。
--   本 migration で DB 層まで塞ぐ。
--
-- ポリシー設計:
--   message_translations は翻訳キャッシュ（テナント私有データ）のみ。共有行なし。
--   ALL ポリシー（USING のみ）: tenant_id = 当セッションの app.tenant_id
--
-- キャスト:
--   NULLIF(current_setting('app.tenant_id', true), '')::INTEGER を使用。
--   - missing_ok=true: 変数未設定なら NULL を返す（エラーでなくフェイルクローズ）
--   - NULLIF: clear_tenant_context が SET app.tenant_id='' した場合も NULL 扱い → 全行 deny
--   参照: migrations/20260605_020000_fix_translation_glossary_rls_cast.sql
--
-- 冪等:
--   DROP POLICY IF EXISTS + ENABLE ROW LEVEL SECURITY は再実行無害
--   テーブル不存在スキーマはスキップ
--
-- 適用対象:
--   pg_namespace で tenant_[0-9]+ スキーマを動的に列挙（新規テナントは次回 migration から適用）
--   既存: tenant_001 / tenant_003 / tenant_004 / tenant_005 / tenant_006
--
-- 依存:
--   ③-a: tenant_id 列が存在し NULL ゼロであること
--   ③-b(3): salesanchor_app が SELECT/INSERT/UPDATE/DELETE GRANT 済みであること
--
-- 作成日: 2026-06-23

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- テーブルが存在しないスキーマはスキップ（CI テスト DB 初回など）
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = r.nspname AND tablename = 'message_translations'
        ) THEN
            RAISE NOTICE 'rls_message_translations: %.message_translations が存在しないためスキップ', r.nspname;
            CONTINUE;
        END IF;

        -- RLS 有効化（冪等）
        EXECUTE format('ALTER TABLE %I.message_translations ENABLE ROW LEVEL SECURITY', r.nspname);
        -- FORCE: テーブルオーナー（jarvis）も必ずポリシーを通す
        EXECUTE format('ALTER TABLE %I.message_translations FORCE ROW LEVEL SECURITY', r.nspname);

        -- 既存ポリシー削除（冪等）
        EXECUTE format(
            'DROP POLICY IF EXISTS message_translations_tenant_isolation ON %I.message_translations',
            r.nspname
        );

        -- ALL ポリシー: 自テナント行のみ (SELECT / INSERT / UPDATE / DELETE)
        -- WITH CHECK 省略 → USING 式が INSERT/UPDATE にも適用される
        -- INSERT/UPDATE 時: row.tenant_id が NULLIF(app.tenant_id,'')::INT と一致しなければ 42501
        EXECUTE format($pol$
            CREATE POLICY message_translations_tenant_isolation
                ON %I.message_translations
                USING (
                    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                )
        $pol$, r.nspname);

        RAISE NOTICE 'rls_message_translations: %.message_translations RLS 有効化・ポリシー適用完了', r.nspname;
    END LOOP;
END
$$;
