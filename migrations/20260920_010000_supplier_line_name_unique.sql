-- 仕入元マスタ重複防止: line_name 部分 UNIQUE インデックス（構造変更のみ）
-- 前提: 既存重複は cleanup-dedup.sql で解消済み
-- ADR-155対応: CREATE INDEX は構造変更として許可
CREATE UNIQUE INDEX IF NOT EXISTS idx_suppliers_line_name_active_unique ON public.suppliers (line_name) WHERE line_name IS NOT NULL AND is_active = TRUE AND tenant_id IS NULL;
