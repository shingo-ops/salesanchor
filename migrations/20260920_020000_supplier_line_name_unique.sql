-- 仕入元マスタ重複防止: line_name 部分 UNIQUE インデックス（構造変更のみ）
-- 前提: 既存重複は cleanup-dedup.sql で解消済み、line_name カラムは 20260603_010000 で追加済み
-- ADR-155対応: CREATE INDEX は構造変更として許可
-- NOTE: テーブル・カラム未存在時はスキップ（CI個別テスト対応、information_schema での存在チェック）
DO $$
DECLARE
    col_exists BOOLEAN;
BEGIN
    -- Guard: to_regclass で表存在、information_schema.columns で列存在を確認
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
              AND column_name = 'line_name'
    ) INTO col_exists;

    IF to_regclass('public.suppliers') IS NOT NULL AND col_exists THEN
        CREATE UNIQUE INDEX IF NOT EXISTS idx_suppliers_line_name_active_unique ON public.suppliers (line_name) WHERE line_name IS NOT NULL AND is_active = TRUE AND tenant_id IS NULL;
    END IF;
END $$;
