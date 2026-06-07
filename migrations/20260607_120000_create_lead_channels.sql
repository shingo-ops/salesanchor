-- ADR-119: lead_channels テーブル作成（既存テナント全件）
-- 1 lead : N channels — クロスプラットフォーム名寄せの lookup 権威テーブル
-- 冪等（CREATE TABLE IF NOT EXISTS）
-- GRANT は 20260605_040000 の ALTER DEFAULT PRIVILEGES で自動付与済み

DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT nspname FROM pg_namespace
    WHERE nspname ~ '^tenant_[0-9]+$'
    ORDER BY nspname
  LOOP
    -- テーブル本体
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I.lead_channels (
          id          SERIAL PRIMARY KEY,
          lead_id     INTEGER NOT NULL REFERENCES %I.leads(id) ON DELETE CASCADE,
          platform    VARCHAR(30)  NOT NULL,
          external_id VARCHAR(255) NOT NULL,
          display_name VARCHAR(255),
          created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          UNIQUE (platform, external_id)
      )',
      r.nspname, r.nspname
    );

    -- lead_id 引き当て用
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_lead_channels_lead_id
          ON %I.lead_channels (lead_id)',
      r.nspname
    );

    -- NOTE: UNIQUE (platform, external_id) が暗黙的に B-tree インデックスを作成するため、
    --       (platform, external_id) への明示的インデックスは不要（重複防止）。

    RAISE NOTICE 'lead_channels created/verified for schema: %', r.nspname;
  END LOOP;
END $$;
