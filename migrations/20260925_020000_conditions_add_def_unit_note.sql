-- ============================================================================
-- Migration 20260925_020000: line_conditions に condition_def_id / unit_id / note 追加
--
-- 目的:
--   ConditionsMasterPanel v2 の UI フォームから状態定義・単位をプルダウンで指定できるよう
--   line_conditions テーブルに外部キー列と自由メモ列を追加する。
--
-- 注意:
--   public.conditions は public.line_conditions の VIEW。
--   ALTER TABLE は必ず line_conditions に対して行い、その後 VIEW を再作成する。
--
-- 依存:
--   20260922_080000_rename_line_analysis_tables.sql  (line_conditions + conditions VIEW)
--   20260921_090000_create_condition_definitions.sql  (condition_definitions テーブル)
--   20260919_020000_master_ssot_public_tables.sql     (public.units テーブル)
--
-- 冪等性: ADD COLUMN IF NOT EXISTS
-- ADR-155 準拠: seed なし
-- ============================================================================

-- ① condition_def_id 追加（既存の場合はスキップ）
ALTER TABLE public.line_conditions
    ADD COLUMN IF NOT EXISTS condition_def_id INTEGER
        REFERENCES public.condition_definitions(id) ON DELETE SET NULL;

-- ② unit_id 追加（既存の場合はスキップ）
ALTER TABLE public.line_conditions
    ADD COLUMN IF NOT EXISTS unit_id INTEGER
        REFERENCES public.units(id) ON DELETE SET NULL;

-- ③ note 追加
ALTER TABLE public.line_conditions
    ADD COLUMN IF NOT EXISTS note TEXT NOT NULL DEFAULT '';

-- ④ インデックス
CREATE INDEX IF NOT EXISTS idx_line_conditions_condition_def_id ON public.line_conditions (condition_def_id);

CREATE INDEX IF NOT EXISTS idx_line_conditions_unit_id ON public.line_conditions (unit_id);

-- ⑤ conditions VIEW を再作成（新列を VIEW 経由でも見えるようにする）
CREATE OR REPLACE VIEW public.conditions AS TABLE public.line_conditions;

-- ⑥ テナントスキーマにも同様のカラムを追加（存在すれば）
DO $$
DECLARE
    _schema TEXT;
BEGIN
    FOR _schema IN
        SELECT nspname FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        -- テナントスキーマ内の line_conditions が BASE TABLE の場合のみ追加
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = _schema AND table_name = 'line_conditions' AND table_type = 'BASE TABLE'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.line_conditions ADD COLUMN IF NOT EXISTS condition_def_id INTEGER REFERENCES public.condition_definitions(id) ON DELETE SET NULL',
                _schema
            );
            EXECUTE format(
                'ALTER TABLE %I.line_conditions ADD COLUMN IF NOT EXISTS unit_id INTEGER REFERENCES public.units(id) ON DELETE SET NULL',
                _schema
            );
            EXECUTE format(
                'ALTER TABLE %I.line_conditions ADD COLUMN IF NOT EXISTS note TEXT NOT NULL DEFAULT ''''',
                _schema
            );
            RAISE NOTICE 'conditions_add_def_unit_note: %.line_conditions に列追加完了', _schema;
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- Rollback:
--   DROP VIEW IF EXISTS public.conditions;
--   ALTER TABLE public.line_conditions DROP COLUMN IF EXISTS note;
--   ALTER TABLE public.line_conditions DROP COLUMN IF EXISTS unit_id;
--   ALTER TABLE public.line_conditions DROP COLUMN IF EXISTS condition_def_id;
--   CREATE OR REPLACE VIEW public.conditions AS TABLE public.line_conditions;
-- ============================================================================
