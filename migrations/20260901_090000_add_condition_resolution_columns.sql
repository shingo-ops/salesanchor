-- Migration: add_condition_resolution_columns
--
-- 背景:
--   TCG 状態解決エンジンを GAS の R1〜R4 ロジックに合わせるため、
--   tenant_004.conditions に不足していた 3 列を追加し、
--   GAS 状態マスタの実データで seed する。
--
-- 設計判断:
--   - additive-only: 列追加のみ。既存列・行を削除/変更しない
--   - 冪等性: ADD COLUMN IF NOT EXISTS + UPDATE (WHERE code IN ...)
--   - tenant_004 のみ対象（他テナントループなし）
--   - app_kubun 列は既存（空欄）。priority / search_kw / exclude_kw は今回追加
--   - units.kubun は既存・値投入済み → 今回変更なし
--
-- 出典: GAS backupConditionMaster07() 実測値 2026-09-01
--   CN0001 Case        / 優先度4 / 適用区分:箱系大
--   CN0002 Damaged case/ 優先度2 / 適用区分:箱系大
--   CN0003 Sealed box  / 優先度4 / 適用区分:箱系
--   CN0004 Damaged sealed box / 優先度2 / 適用区分:箱系
--   CN0005 No shrink box / 優先度3 / 適用区分:(空=全)
--   CN0006 Opened box  / 優先度3 / 適用区分:(空=全)
--   CN0007 Unsearched pack / 優先度3 / 適用区分:(空=全)
--   CN0008 FLAG_SINGLE / 優先度1 / 適用区分:枚系,単位不明
--   CN0009 Opened case / 優先度2 / 適用区分:箱系大
--   CN0010 Searched pack / 優先度2 / 適用区分:パック系
--
-- 作成日: 2026-09-01

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ----------------------------------------------------------------
    -- ガード: tenant_004 が存在しない場合はスキップ
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260901_090000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- Step 1: conditions テーブルに列追加 (additive-only)
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'priority'
    ) THEN
        EXECUTE format('ALTER TABLE %I.conditions ADD COLUMN priority INTEGER', _schema);
        RAISE NOTICE 'migration 20260901_090000: added conditions.priority';
    ELSE
        RAISE NOTICE 'migration 20260901_090000: conditions.priority already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'search_kw'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.conditions ADD COLUMN search_kw TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_090000: added conditions.search_kw';
    ELSE
        RAISE NOTICE 'migration 20260901_090000: conditions.search_kw already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'exclude_kw'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.conditions ADD COLUMN exclude_kw TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_090000: added conditions.exclude_kw';
    ELSE
        RAISE NOTICE 'migration 20260901_090000: conditions.exclude_kw already exists, skipping';
    END IF;

    -- ----------------------------------------------------------------
    -- Step 2: 優先度インデックス
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = _schema AND tablename = 'conditions'
          AND indexname = 'idx_conditions_priority'
    ) THEN
        EXECUTE format(
            'CREATE INDEX idx_conditions_priority ON %I.conditions (priority ASC NULLS LAST)',
            _schema
        );
        RAISE NOTICE 'migration 20260901_090000: created idx_conditions_priority';
    END IF;

    -- DEPRECATED: UPDATE values removed — values now managed via app UI/CSV per ADR-155
    -- Original UPDATE set app_kubun/priority/search_kw/exclude_kw for CN0001-CN0010
    -- Kept: DDL (ALTER TABLE ADD COLUMN, CREATE INDEX) above

END;
$$;
