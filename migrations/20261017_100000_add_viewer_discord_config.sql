-- ADR-1019 段4c: 閲覧者の Discord 受付の設定（運用サーバー1つ。1行だけ）。データは専用スクリプトで入れる（migration でデータを入れない）
CREATE TABLE IF NOT EXISTS public.viewer_discord_config (
    id SMALLINT PRIMARY KEY DEFAULT 1,
    guild_id VARCHAR(32) NOT NULL,
    reception_channel_id VARCHAR(32) NOT NULL,
    ticket_category_id VARCHAR(32) NOT NULL,
    staff_role_id VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_viewer_discord_config_single_row CHECK (id = 1),
    CONSTRAINT uq_viewer_discord_config_guild_id UNIQUE (guild_id)
);
COMMENT ON TABLE public.viewer_discord_config IS '閲覧者の Discord 受付の設定（運用サーバー1つ・1行だけ）。ADR-1019';
COMMENT ON COLUMN public.viewer_discord_config.id IS '常に 1（1行だけ）';
COMMENT ON COLUMN public.viewer_discord_config.guild_id IS '運用サーバーの ID';
COMMENT ON COLUMN public.viewer_discord_config.reception_channel_id IS '受付の部屋（ボタンを置く部屋）の ID';
COMMENT ON COLUMN public.viewer_discord_config.ticket_category_id IS 'チケット部屋を作るカテゴリの ID';
COMMENT ON COLUMN public.viewer_discord_config.staff_role_id IS '部屋を見られるスタッフのロールの ID';
COMMENT ON COLUMN public.viewer_discord_config.created_at IS '作った時刻';
COMMENT ON COLUMN public.viewer_discord_config.updated_at IS '更新した時刻';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE ON public.viewer_discord_config TO salesanchor_app;
    END IF;
END $$;
