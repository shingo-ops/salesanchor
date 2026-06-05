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
-- 冪等: IF NOT EXISTS / ALTER TABLE ... ENABLE は再実行無害
-- 作成日: 2026-06-05

-- ==========================================================================
-- 1. RLS 有効化
-- ==========================================================================

ALTER TABLE public.translation_glossary ENABLE ROW LEVEL SECURITY;

-- FORCE: テーブルオーナー（superuser 以外）も必ずポリシーを通す
ALTER TABLE public.translation_glossary FORCE ROW LEVEL SECURITY;

-- ==========================================================================
-- 2. SELECT ポリシー — 自テナント行 + 共有行（全認証ユーザー）
-- ==========================================================================

DROP POLICY IF EXISTS tg_select ON public.translation_glossary;
CREATE POLICY tg_select
    ON public.translation_glossary
    FOR SELECT
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INTEGER
    );

-- ==========================================================================
-- 3. INSERT ポリシー
--    テナント行: 自テナントのみ
--    共有行 (tenant_id IS NULL): operator のみ
-- ==========================================================================

DROP POLICY IF EXISTS tg_insert ON public.translation_glossary;
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
    );

-- ==========================================================================
-- 4. UPDATE ポリシー
--    テナント行: 自テナントのみ
--    共有行: operator のみ
-- ==========================================================================

DROP POLICY IF EXISTS tg_update ON public.translation_glossary;
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
    );

-- ==========================================================================
-- 5. DELETE ポリシー
--    テナント行: 自テナントのみ
--    共有行: operator のみ
-- ==========================================================================

DROP POLICY IF EXISTS tg_delete ON public.translation_glossary;
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
    );

-- ==========================================================================
-- 6. 確認クエリ（apply 後のログ用）
-- ==========================================================================

DO $$
BEGIN
    RAISE NOTICE 'migration 20260605_010000: translation_glossary RLS ポリシー適用完了';
    RAISE NOTICE '  SELECT  : 自テナント行 + 共有行 (tenant_id IS NULL)';
    RAISE NOTICE '  INSERT  : テナント行=自テナント / 共有行=operator';
    RAISE NOTICE '  UPDATE  : テナント行=自テナント / 共有行=operator';
    RAISE NOTICE '  DELETE  : テナント行=自テナント / 共有行=operator';
    RAISE NOTICE '  注意    : app.is_operator をセッションに SET する実装が必要';
    RAISE NOTICE '            (auth/dependencies.py: is_super_admin=true 時に SET true)';
END
$$;
