-- Migration: tenant_discord_config に connected_by_staff_id カラム追加
-- Discord OAuth 接続時に誰が接続したかを記録する
-- 冪等性: tenant_discord_config が存在する場合のみ ALTER を実行（CI単体テスト環境対応）

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'tenant_discord_config'
  ) THEN
    -- staff テーブルはテナント個別スキーマ（tenant_NNN.staff）のため
    -- public.staff は存在しない。FK 制約は設けず plain INTEGER で記録する。
    ALTER TABLE public.tenant_discord_config
        ADD COLUMN IF NOT EXISTS connected_by_staff_id INTEGER;
  END IF;
END $$;
