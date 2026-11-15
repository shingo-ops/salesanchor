-- ADR-033: users テーブルに theme カラムを追加
-- ユーザー個人単位のテーマ設定（'light' / 'dark'）
-- ADD COLUMN IF NOT EXISTS で idempotent
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS theme VARCHAR(10) NOT NULL DEFAULT 'light';

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): 審査用の利用者1人の theme を 'light' に戻す UPDATE を外した。
-- 列の既定値 'light' で足りる。毎回の本番反映で、画面で変えた色を戻していた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #3
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: review user theme reset removed (054)'; END $$;
