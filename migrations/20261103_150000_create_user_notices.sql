-- アプリ内の鈴: 各社スキーマに user_notices（人ごとの知らせ・未読つき）を作る（追加のみ・冪等）
-- 本文・Discord の id の列は作らない。link_url は書き込みの場所で、書いた人の id は含まない。
-- GRANT は ALTER DEFAULT PRIVILEGES（20260605_040000）で自動付与済み。
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT nspname FROM pg_namespace
    WHERE nspname ~ '^tenant_[0-9]+$'
    ORDER BY nspname
  LOOP
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I.user_notices (
          id           BIGSERIAL PRIMARY KEY,
          user_id      INTEGER NOT NULL,
          kind         TEXT NOT NULL,
          actor_name   TEXT,
          channel_name TEXT,
          link_url     TEXT,
          created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
          read_at      TIMESTAMPTZ
      )',
      r.nspname
    );
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_user_notices_user_created
          ON %I.user_notices (user_id, created_at DESC)',
      r.nspname
    );
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_user_notices_user_unread
          ON %I.user_notices (user_id) WHERE read_at IS NULL',
      r.nspname
    );
    EXECUTE format('COMMENT ON TABLE %I.user_notices IS %L', r.nspname,
      '人ごとのアプリ内の知らせ（鈴）。宛先の人数分の行を持つ');
    EXECUTE format('COMMENT ON COLUMN %I.user_notices.user_id IS %L', r.nspname,
      '宛先の public.users.id');
    EXECUTE format('COMMENT ON COLUMN %I.user_notices.kind IS %L', r.nspname,
      '知らせの種類（例 discord_outside_ticket_post）');
    EXECUTE format('COMMENT ON COLUMN %I.user_notices.actor_name IS %L', r.nspname,
      '書いた人の Discord の表示名（本文・id ではない）');
    EXECUTE format('COMMENT ON COLUMN %I.user_notices.channel_name IS %L', r.nspname,
      '書き込まれたチャンネル名');
    EXECUTE format('COMMENT ON COLUMN %I.user_notices.link_url IS %L', r.nspname,
      '書き込みへのリンク（サーバー・チャンネル・書き込みの番号。書いた人の id は含まない）');
    EXECUTE format('COMMENT ON COLUMN %I.user_notices.created_at IS %L', r.nspname,
      '知らせを作った日時');
    EXECUTE format('COMMENT ON COLUMN %I.user_notices.read_at IS %L', r.nspname,
      '既読にした日時（NULL は未読）');
    RAISE NOTICE 'user_notices created/verified for schema: %', r.nspname;
  END LOOP;
END $$;
