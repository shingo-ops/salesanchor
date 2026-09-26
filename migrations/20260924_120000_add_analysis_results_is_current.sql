-- ADR-158: 商品単位の差分更新（Product-Level Supersession）
-- analysis_results に is_current フラグを追加
-- 配信の可視性をメッセージ単位→商品単位に変更するための基盤
-- DEFAULT TRUE: 既存データは全て有効（現行動作を維持）
-- 冪等: IF NOT EXISTS

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'analysis_results'
      AND column_name = 'is_current'
  ) THEN
    ALTER TABLE public.analysis_results
      ADD COLUMN is_current BOOLEAN NOT NULL DEFAULT TRUE;

    COMMENT ON COLUMN public.analysis_results.is_current IS
      '配信可視性フラグ。同一仕入元で新メッセージの解析が完了した際、'
      '新メッセージにも存在する product_id の旧行は FALSE に更新される。'
      '新メッセージに存在しない product_id の旧行は TRUE のまま残り配信に継続表示される。';

    CREATE INDEX IF NOT EXISTS
      ix_analysis_results_is_current
      ON public.analysis_results (is_current)
      WHERE is_current = TRUE;
  END IF;
END
$$;
