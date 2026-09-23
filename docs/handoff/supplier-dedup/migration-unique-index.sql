-- ============================================================================
-- 仕入元マスタ重複防止 — 部分 UNIQUE インデックス
--
-- 用途: line_name の重複を DB レベルで防止する
-- 前提: cleanup-dedup.sql が実行済みで重複が0であること
-- 冪等: IF NOT EXISTS で安全
-- ============================================================================

-- 部分一意インデックス:
-- - line_name IS NOT NULL: NULL の仕入元（テナント画面登録等）は対象外
-- - is_active = TRUE: 論理削除済みレコードは対象外
-- - tenant_id IS NULL: 共用マスタのみ保護（テナント固有は対象外）
CREATE UNIQUE INDEX IF NOT EXISTS idx_suppliers_line_name_active_unique
ON public.suppliers (line_name)
WHERE line_name IS NOT NULL AND is_active = TRUE AND tenant_id IS NULL;
