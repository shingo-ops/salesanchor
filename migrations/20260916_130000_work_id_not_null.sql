-- ADR-1001: public.products.work_id を NOT NULL に変更
-- 前提: 全1,830件で work_id が設定済み（NULL 0件、2026-09-16確認済み）
ALTER TABLE public.products ALTER COLUMN work_id SET NOT NULL;
