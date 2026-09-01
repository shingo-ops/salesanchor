-- Migration: add_unit_inference_columns_t004
--
-- 背景:
--   TCG 単位復旧エンジン (E3a: recoverUnitFromProductName) と
--   E5 (recalcConditionFromResolvedUnit) の実装に必要な列を
--   tenant_004.analysis_results に追加する。
--
-- 追加列:
--   unit_inferred    TEXT  — E2 価格帯推定結果 (将来用)
--   unit_basis       TEXT  — 単位決定根拠 ('NAME_RECOVERY:{term}' 等)
--   unit_confidence  TEXT  — 信頼度 (将来用)
--   unit_infer_reason TEXT — 推定理由詳細 (将来用)
--
-- 設計判断:
--   - additive-only: 列追加のみ。既存列・行を削除/変更しない
--   - 冪等性: IF NOT EXISTS ガード
--   - tenant_004 のみ対象（他テナントループなし）
--
-- 出典: GAS AnalysisV2UnitRecovery.gs:66-84 ヘッダー定義
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
        RAISE NOTICE 'migration 20260901_120000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- Step 1: analysis_results に列追加 (additive-only)
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'analysis_results' AND column_name = 'unit_inferred'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.analysis_results ADD COLUMN unit_inferred TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_120000: added analysis_results.unit_inferred';
    ELSE
        RAISE NOTICE 'migration 20260901_120000: analysis_results.unit_inferred already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'analysis_results' AND column_name = 'unit_basis'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.analysis_results ADD COLUMN unit_basis TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_120000: added analysis_results.unit_basis';
    ELSE
        RAISE NOTICE 'migration 20260901_120000: analysis_results.unit_basis already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'analysis_results' AND column_name = 'unit_confidence'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.analysis_results ADD COLUMN unit_confidence TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_120000: added analysis_results.unit_confidence';
    ELSE
        RAISE NOTICE 'migration 20260901_120000: analysis_results.unit_confidence already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'analysis_results' AND column_name = 'unit_infer_reason'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.analysis_results ADD COLUMN unit_infer_reason TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_120000: added analysis_results.unit_infer_reason';
    ELSE
        RAISE NOTICE 'migration 20260901_120000: analysis_results.unit_infer_reason already exists, skipping';
    END IF;

    -- ----------------------------------------------------------------
    -- Step 2: unit_basis インデックス (NAME_RECOVERY: prefix 検索用)
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = _schema AND tablename = 'analysis_results'
          AND indexname = 'idx_analysis_results_unit_basis'
    ) THEN
        EXECUTE format(
            $q$CREATE INDEX idx_analysis_results_unit_basis ON %I.analysis_results (unit_basis) WHERE unit_basis != ''$q$,
            _schema
        );
        RAISE NOTICE 'migration 20260901_120000: created idx_analysis_results_unit_basis';
    END IF;

END;
$$;
