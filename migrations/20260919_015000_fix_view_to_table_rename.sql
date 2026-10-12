-- ============================================================================
-- Migration 20260919_015000: VIEW → TABLE 解消
--
-- 背景:
--   本番DBに手動SSH操作で作成された4つのVIEWが存在し、
--   後続マイグレーション (20260919_020000 等) が同名のTABLEに対する
--   CREATE INDEX / ALTER TABLE を実行しようとして失敗する。
--
--   VIEW名        → 実体テーブル
--   units         → line_units (8行)
--   unit_aliases  → line_unit_aliases (39行)
--   conditions    → line_conditions (11行)
--   condition_aliases → line_condition_aliases (31行)
--
-- 変更内容:
--   1. 4つのVIEWをDROP (CASCADE — 依存オブジェクトはない)
--   2. line_* テーブルを本来の名前にRENAME
--   データの移動・削除はゼロ（名前変更のみ）
--   FK制約・インデックスはPostgreSQLがRENAMEに自動追従
--
-- 冪等性:
--   DO $$ ブロックで VIEW存在を確認してからDROP+RENAME
--   2回目以降の実行ではVIEWが存在しないためスキップ
--
-- 作成日: 2026-09-22
-- ============================================================================

DO $$
BEGIN
    -- units: VIEW → TABLE
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'units' AND c.relkind = 'v') THEN
        DROP VIEW public.units CASCADE;
        ALTER TABLE public.line_units RENAME TO units;
        RAISE NOTICE 'Renamed line_units → units (VIEW dropped)';
    ELSE
        RAISE NOTICE 'public.units is not a VIEW — skipping';
    END IF;

    -- unit_aliases: VIEW → TABLE
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'unit_aliases' AND c.relkind = 'v') THEN
        DROP VIEW public.unit_aliases CASCADE;
        ALTER TABLE public.line_unit_aliases RENAME TO unit_aliases;
        RAISE NOTICE 'Renamed line_unit_aliases → unit_aliases (VIEW dropped)';
    ELSE
        RAISE NOTICE 'public.unit_aliases is not a VIEW — skipping';
    END IF;

    -- conditions: VIEW → TABLE
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'conditions' AND c.relkind = 'v') THEN
        DROP VIEW public.conditions CASCADE;
        ALTER TABLE public.line_conditions RENAME TO conditions;
        RAISE NOTICE 'Renamed line_conditions → conditions (VIEW dropped)';
    ELSE
        RAISE NOTICE 'public.conditions is not a VIEW — skipping';
    END IF;

    -- condition_aliases: VIEW → TABLE
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'condition_aliases' AND c.relkind = 'v') THEN
        DROP VIEW public.condition_aliases CASCADE;
        ALTER TABLE public.line_condition_aliases RENAME TO condition_aliases;
        RAISE NOTICE 'Renamed line_condition_aliases → condition_aliases (VIEW dropped)';
    ELSE
        RAISE NOTICE 'public.condition_aliases is not a VIEW — skipping';
    END IF;
END $$;
