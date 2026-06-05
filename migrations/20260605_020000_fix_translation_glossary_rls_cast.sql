-- ADR-SA-17: translation_glossary RLS ポリシーを NULLIF 修正版に再作成
--
-- 背景:
--   20260605_010000 のポリシーで current_setting('app.tenant_id', true)::INTEGER が
--   app.tenant_id='' のとき "invalid input syntax for type integer" エラーになることが
--   RLS テストで判明（operator セッションで app.tenant_id 未設定の場合に空文字列になる）。
--
-- 修正:
--   NULLIF(current_setting('app.tenant_id', true), '')::INTEGER に変更。
--   - 未設定 → current_setting(..., true) = NULL → NULLIF(NULL, '') = NULL → NULL::INTEGER = NULL → deny
--   - 空文字列 → NULLIF('', '') = NULL → NULL::INTEGER = NULL → deny
--   - '1' → NULLIF('1', '') = '1' → 1::INTEGER → 正常比較
--
-- 冪等: テーブル存在チェック / DROP POLICY IF EXISTS
-- 依存: migrations/20260605_010000_rls_translation_glossary.sql
-- 作成日: 2026-06-05

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'translation_glossary'
    ) THEN
        RAISE NOTICE 'migration 20260605_020000: translation_glossary が存在しないためスキップ';
        RETURN;
    END IF;

    -- ================================================================
    -- SELECT ポリシー再作成（NULLIF 修正）
    -- ================================================================
    EXECUTE 'DROP POLICY IF EXISTS tg_select ON public.translation_glossary';
    EXECUTE $pol$
        CREATE POLICY tg_select
            ON public.translation_glossary
            FOR SELECT
            USING (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
            )
    $pol$;

    -- ================================================================
    -- INSERT ポリシー再作成（NULLIF 修正）
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
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
    $pol$;

    -- ================================================================
    -- UPDATE ポリシー再作成（NULLIF 修正）
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
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
            WITH CHECK (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
    $pol$;

    -- ================================================================
    -- DELETE ポリシー再作成（NULLIF 修正）
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
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
    $pol$;

    RAISE NOTICE 'migration 20260605_020000: translation_glossary RLS ポリシー NULLIF 修正完了';
END
$$;
