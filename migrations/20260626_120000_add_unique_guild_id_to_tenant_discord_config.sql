-- ADR-146: Discord B方式移行 — tenant_discord_config.guild_id に UNIQUE 制約追加
--
-- 目的: 1 Guild = 1 テナント を DB レベルで保証する (ADR-146 K3)。
--       B方式では guild_id → tenant_id の逆引きを行うため、
--       同一 guild_id が複数 tenant に紐づくと振り分けが曖昧になる。
--
-- 前提: guild_id カラムは 099_add_discord_guild_config.sql で既に存在する。
--       本番 tenant_discord_config の行数は現時点で 0 または 1 行（004 のみ）。
--
-- ロールバック:
--   ALTER TABLE public.tenant_discord_config DROP CONSTRAINT IF EXISTS uq_tenant_discord_config_guild_id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conname = 'uq_tenant_discord_config_guild_id'
          AND  conrelid = 'public.tenant_discord_config'::regclass
    ) THEN
        ALTER TABLE public.tenant_discord_config
            ADD CONSTRAINT uq_tenant_discord_config_guild_id UNIQUE (guild_id);
    END IF;
END;
$$;
