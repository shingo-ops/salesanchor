-- ADR-SA-17: 翻訳サブシステム改訂 — 双方向自動判定 / 即時翻訳 / 辞書2層化＋昇格
--
-- 変更内容（すべて additive-only / 冪等）:
--   1. <tenant_schema>.message_translations に status 列追加（I-4: 言語・確信度・status 含む）
--   2. public.translation_glossary に昇格フロー用カラム追加（I-9: share_status / 提案・レビュー日時）
--   3. public.translation_glossary に RLS 有効化（I-8: Layer2 私有辞書のテナント分離・防御多重化）
--   4. public.permissions に translation.glossary.view / translation.glossary.edit を seed
--      （I-7 のテナント辞書ページ。共有辞書ページは require_super_admin で構造的に分離するため権限キー不要）
--
-- 冪等: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS / pg_policies 確認 / ON CONFLICT DO NOTHING
-- 適用: public 横断表 + 全テナントスキーマ（pg_namespace 走査）
-- 作成日: 2026-06-05
-- 関連: 20260604_220000_create_translation_glossary.sql（本 migration の前提）

-- ==========================================================================
-- 1. message_translations.status 追加（即時翻訳の状態を保持）
--    値: 'completed'（翻訳済）/ 'failed'（即時翻訳失敗・sweeper 拾い対象）
--    既存行はすべて翻訳済のため DEFAULT 'completed'。
-- ==========================================================================

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        CONTINUE WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.nspname
              AND table_name   = 'message_translations'
        );

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.nspname
              AND table_name   = 'message_translations'
              AND column_name  = 'status'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.message_translations '
                'ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT ''completed''',
                schema_rec.nspname
            );
            RAISE NOTICE 'migration SA-17: %.message_translations.status 追加', schema_rec.nspname;
        END IF;
    END LOOP;
END
$$;

-- ==========================================================================
-- 2. translation_glossary 昇格フロー用カラム（I-9）
--    share_status: 'none'（既定）/ 'proposed'（テナントが共有提案）/
--                  'approved'（operator 承認・共有へ匿名コピー済）/ 'rejected'（却下）
--    昇格は非破壊（私有エントリは残す）・自動昇格しない（コードで operator 承認必須）。
-- ==========================================================================

ALTER TABLE public.translation_glossary
    ADD COLUMN IF NOT EXISTS share_status VARCHAR(20) NOT NULL DEFAULT 'none';

ALTER TABLE public.translation_glossary
    ADD COLUMN IF NOT EXISTS share_proposed_at TIMESTAMPTZ;

ALTER TABLE public.translation_glossary
    ADD COLUMN IF NOT EXISTS share_reviewed_at TIMESTAMPTZ;

-- share_status の値域を制約（冪等: 既存制約があればスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_translation_glossary_share_status'
    ) THEN
        ALTER TABLE public.translation_glossary
            ADD CONSTRAINT ck_translation_glossary_share_status
            CHECK (share_status IN ('none', 'proposed', 'approved', 'rejected'));
    END IF;
END
$$;

-- 昇格レビューキュー（提案中の私有エントリ）の高速参照
CREATE INDEX IF NOT EXISTS idx_translation_glossary_share_status
    ON public.translation_glossary (share_status)
    WHERE share_status = 'proposed';

-- ==========================================================================
-- 3. RLS: Layer2 私有辞書のテナント分離（I-8・防御多重化）
--    request path（app.tenant_id 設定済）でのみ厳格分離。
--    batch / operator パス（app.tenant_id 未設定）では全行可視にして既存バッチを壊さない。
--    共有ベース（tenant_id IS NULL）は常に可視（全テナント読み取り専用）。
--    ※ 一次防御はアプリ層フィルタ（services/translation_glossary.py の WHERE 句）。
-- ==========================================================================

ALTER TABLE public.translation_glossary ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'translation_glossary'
          AND policyname = 'translation_glossary_tenant_isolation'
    ) THEN
        CREATE POLICY translation_glossary_tenant_isolation
            ON public.translation_glossary
            USING (
                tenant_id IS NULL
                OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
                OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
            );
    END IF;
END
$$;

-- ==========================================================================
-- 4. 権限 seed: テナント辞書ページ（I-7: tenant_admin / tenant_staff 用）
--    共有辞書ページは require_super_admin（is_super_admin）で構造分離 → 権限キー不要。
--    パターン: migrations/042_seed_meta_inbox_permissions.sql 準拠。
-- ==========================================================================

INSERT INTO public.permissions (key, resource, action, description, category) VALUES
    ('translation.glossary.view', 'translation', 'glossary_view',
     'テナント辞書（私有グロッサリ）の閲覧', 'メッセージ'),
    ('translation.glossary.edit', 'translation', 'glossary_edit',
     'テナント辞書の追加・編集・削除・共有提案', 'メッセージ')
ON CONFLICT (key) DO NOTHING;

DO $glossary_perms$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables WHERE schemaname = schema_rec.nspname AND tablename = 'roles'
        ) OR NOT EXISTS (
            SELECT 1 FROM pg_tables WHERE schemaname = schema_rec.nspname AND tablename = 'role_permissions'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'INSERT INTO %I.role_permissions (role_id, permission_id) '
            'SELECT r.id, p.id FROM %I.roles r CROSS JOIN public.permissions p '
            'WHERE r.name IN (''オーナー'', ''システム管理者'') '
            '  AND p.key IN (''translation.glossary.view'', ''translation.glossary.edit'') '
            'ON CONFLICT (role_id, permission_id) DO NOTHING',
            schema_rec.nspname, schema_rec.nspname
        );
    END LOOP;
END $glossary_perms$;
