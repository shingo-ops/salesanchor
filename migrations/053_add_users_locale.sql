-- ADR-027: users テーブルに locale カラムを追加
-- ユーザー個人単位の言語設定（'ja' / 'en'）
-- ADD COLUMN IF NOT EXISTS で idempotent
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS locale VARCHAR(10) NOT NULL DEFAULT 'ja';

-- 既存ユーザーは全員 'ja' に設定（DEFAULT 'ja' で自動設定済）
