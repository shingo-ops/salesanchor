-- SA-05: リンクテンプレート SSOT
-- public スキーマ（共有カタログ面・テナント分離なし）
--
-- 設計:
--   - channel を PRIMARY KEY とするシンプルなカタログテーブル
--   - is_verified=FALSE のチャンネルは UI 側で「未検証」バッジを表示
--   - ON CONFLICT DO NOTHING で冪等（再実行 no-op）
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS
--   - INSERT ... ON CONFLICT (channel) DO NOTHING

CREATE TABLE IF NOT EXISTS public.link_templates (
    channel VARCHAR(30) PRIMARY KEY,
    url_pattern TEXT NOT NULL,
    required_ids JSONB NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- 連携リンクの雛形 5 チャネルの seed を外した。link_templates は画面／CSV で管理する。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: link_templates seed removed'; END $$;
