-- Migration: analysis_run_snapshots.unit_id / condition_id UUID → INTEGER
-- Date: 2026-09-24
-- Purpose: public.analysis_run_snapshots の unit_id / condition_id は
--          20260921_110000_pipeline_tables_public.sql で UUID 型で作成されたが、
--          analysis_results.unit_id / condition_id は INTEGER 型のため型不一致が発生する。
--          reanalyze_extraction_job() のスナップショット保存に必要な型統一を行う。
--
-- 既存データ: unit_id の uuid 値はすべて旧テナント004時代の値であり、
--             public.units には対応エントリが存在しない（孤立データ）。
--             NULL に初期化して integer 型に変換する。
-- Backfill: 次回 reanalyze_extraction_job() 実行時に integer 値が入る。
-- Rollback: unit_id / condition_id を DROP して UUID 型で再追加。

BEGIN;

DO $$
BEGIN
  -- unit_id: UUID → INTEGER
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'analysis_run_snapshots'
      AND column_name  = 'unit_id'
      AND data_type    = 'uuid'
  ) THEN
    ALTER TABLE public.analysis_run_snapshots DROP COLUMN unit_id;
    ALTER TABLE public.analysis_run_snapshots ADD COLUMN unit_id INTEGER;
    RAISE NOTICE 'analysis_run_snapshots.unit_id: UUID → INTEGER 変換完了';
  ELSE
    RAISE NOTICE 'analysis_run_snapshots.unit_id: すでに INTEGER 型またはカラムなし。スキップ';
  END IF;

  -- condition_id: UUID → INTEGER
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'analysis_run_snapshots'
      AND column_name  = 'condition_id'
      AND data_type    = 'uuid'
  ) THEN
    ALTER TABLE public.analysis_run_snapshots DROP COLUMN condition_id;
    ALTER TABLE public.analysis_run_snapshots ADD COLUMN condition_id INTEGER;
    RAISE NOTICE 'analysis_run_snapshots.condition_id: UUID → INTEGER 変換完了';
  ELSE
    RAISE NOTICE 'analysis_run_snapshots.condition_id: すでに INTEGER 型またはカラムなし。スキップ';
  END IF;
END $$;

COMMIT;
