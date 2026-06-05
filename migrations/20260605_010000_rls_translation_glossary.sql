-- ADR-SA-17: translation_glossary に RLS を追加
--
-- 背景:
--   ADR-110 が作成した public.translation_glossary は RLS 未設定だった。
--   監査（2026-06-05）で I-8（テナント私有辞書の他テナント不可視）が
--   アプリ層フィルタのみで DB 直接アクセス時は保護なしと判明。
--   本 migration で DB 層まで塞ぐ。
--
-- ポリシー設計:
--   読み取り (SELECT):
--     自テナント行 (tenant_id = app.tenant_id) OR 共有行 (tenant_id IS NULL)
--   書き込み (INSERT/UPDATE/DELETE):
--     テナント行のみ: tenant_id = app.tenant_id
--     共有行 (tenant_id IS NULL): app.is_operator = 'true' のセッションのみ
--
-- セッション変数:
--   app.tenant_id  — 既存パターン。auth/dependencies.py で SET
--   app.is_operator — 新規。is_super_admin=true のセッションで SET 'true'
--                     未設定は '' 扱い（false 相当）
--
-- 冪等: テーブル存在チェック / DROP POLICY IF EXISTS / ENABLE は再実行無害
-- 依存: migrations/20260604_220000_create_translation_glossary.sql
--       （テーブル未作成環境ではスキップ。本番・開発では先行 migration 適用済み）
-- 作成日: 2026-06-05

DO $$
BEGIN
    -- 先行 migration が未適用の環境（CI テスト DB の初回など）はスキップ
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'translation_glossary'
    ) THEN
        RAISE NOTICE 'migration 20260605_010000: translation_glossary が存在しないためスキップ（先行 migration 未適用）';
        RETURN;
    END IF;

    -- ================================================================
    -- 1. RLS 有効化
    -- ================================================================
    EXECUTE 'ALTER TABLE public.translation_glossary ENABLE ROW LEVEL SECURITY';
    -- FORCE: テーブルオーナー（superuser 以外）も必ずポリシーを通す
    EXECUTE 'ALTER TABLE public.translation_glossary FORCE ROW LEVEL SECURITY';

    -- ================================================================
    -- 2. SELECT ポリシー — 自テナント行 + 共有行（全認証ユーザー）
    -- ================================================================
    EXECUTE 'DROP POLICY IF EXISTS tg_select ON public.translation_glossary';
    EXECUTE $pol$
        CREATE POLICY tg_select
            ON public.translation_glossary
            FOR SELECT
            USING (
                tenant_id IS NULL
                OR tenant_id = current_setting('app.tenant_id', true)::INTEGER
            )
    $pol$;

    -- ================================================================
    -- 3. INSERT ポリシー
    --    テナント行: 自テナントのみ
    --    共有行 (tenant_id IS NULL): operator のみ
    -- ================================================================
    EXECUTE 'DROP POLICY IF EXISTS tg_insert ON public.translation_glossary';
    EXECUTE $pol$
        CREATE POLICY tg_insert
            ON public.translation_glossary
            FOR INSERT
            WITH CHECK (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
    $pol$;

    -- ================================================================
    -- 4. UPDATE ポリシー
    -- ================================================================
    EXECUTE 'DROP POLICY IF EXISTS tg_update ON public.translation_glossary';
    EXECUTE $pol$
        CREATE POLICY tg_update
            ON public.translation_glossary
            FOR UPDATE
            USING (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
            WITH CHECK (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
    $pol$;

    -- ================================================================
    -- 5. DELETE ポリシー
    -- ================================================================
    EXECUTE 'DROP POLICY IF EXISTS tg_delete ON public.translation_glossary';
    EXECUTE $pol$
        CREATE POLICY tg_delete
            ON public.translation_glossary
            FOR DELETE
            USING (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
    $pol$;

    RAISE NOTICE 'migration 20260605_010000: translation_glossary RLS ポリシー適用完了';
    RAISE NOTICE '  SELECT  : 自テナント行 + 共有行 (tenant_id IS NULL)';
    RAISE NOTICE '  INSERT  : テナント行=自テナント / 共有行=app.is_operator=true';
    RAISE NOTICE '  UPDATE  : テナント行=自テナント / 共有行=app.is_operator=true';
    RAISE NOTICE '  DELETE  : テナント行=自テナント / 共有行=app.is_operator=true';
    RAISE NOTICE '  注意    : app.is_operator をセッションに SET する実装が必要';
    RAISE NOTICE '            (auth/dependencies.py: is_super_admin=true 時に SET true)';
END
$$;
