-- discord-server-management 便1b: 登録の表の主キーを (tenant_id) から (tenant_id, purpose) に替える（冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md §4-1 改訂1
-- 目的: 1 社が顧客用（customer）と自社用（own）の 2 行を持てるようにする。
--       便1a の一意 uq_tenant_discord_config_tenant_purpose は主キーと同じ中身になるので外す。
--       uq_tenant_discord_config_guild_id（同じサーバーを二重に登録できない）は残す。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順。own の行を消してから戻す）:
--   DELETE FROM public.tenant_discord_config WHERE purpose = 'own';
--   ALTER TABLE public.tenant_discord_config ADD CONSTRAINT uq_tenant_discord_config_tenant_purpose UNIQUE (tenant_id, purpose);
--   ALTER TABLE public.tenant_discord_config DROP CONSTRAINT tenant_discord_config_pkey;
--   ALTER TABLE public.tenant_discord_config ADD CONSTRAINT tenant_discord_config_pkey PRIMARY KEY (tenant_id);

DO $tdc_pk$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conrelid = 'public.tenant_discord_config'::regclass
          AND  contype = 'p'
          AND  pg_get_constraintdef(oid) = 'PRIMARY KEY (tenant_id, purpose)'
    ) THEN
        ALTER TABLE public.tenant_discord_config
            DROP CONSTRAINT IF EXISTS tenant_discord_config_pkey;
        ALTER TABLE public.tenant_discord_config
            ADD CONSTRAINT tenant_discord_config_pkey PRIMARY KEY (tenant_id, purpose);
    END IF;
END
$tdc_pk$;

ALTER TABLE public.tenant_discord_config
    DROP CONSTRAINT IF EXISTS uq_tenant_discord_config_tenant_purpose;
