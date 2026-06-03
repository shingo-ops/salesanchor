-- Migration: tenant_discord_config に connected_by_staff_id カラム追加
-- Discord OAuth 接続時に誰が接続したかを記録する

ALTER TABLE public.tenant_discord_config
    ADD COLUMN IF NOT EXISTS connected_by_staff_id INTEGER REFERENCES public.staff(id) ON DELETE SET NULL;
