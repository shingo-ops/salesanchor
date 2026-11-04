-- discord-server-management 便1a: 登録の表に用途 purpose を足す（足すだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md §4-1 改訂1
-- 目的: 1 社が顧客用と自社用の 2 つのサーバーを登録できるようにする前段。
--       今の行はすべて既定値 'customer' になり、今のプログラムはこの列を知らなくても動く。
--       主キー (tenant_id) は便1b で (tenant_id, purpose) に替える。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順）:
--   ALTER TABLE public.tenant_discord_config DROP CONSTRAINT IF EXISTS uq_tenant_discord_config_tenant_purpose;
--   ALTER TABLE public.tenant_discord_config DROP CONSTRAINT IF EXISTS ck_tenant_discord_config_purpose;
--   ALTER TABLE public.tenant_discord_config DROP COLUMN IF EXISTS purpose;

ALTER TABLE public.tenant_discord_config
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(16) NOT NULL DEFAULT 'customer';

DO $tdc_purpose$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conname = 'ck_tenant_discord_config_purpose'
          AND  conrelid = 'public.tenant_discord_config'::regclass
    ) THEN
        ALTER TABLE public.tenant_discord_config
            ADD CONSTRAINT ck_tenant_discord_config_purpose CHECK (purpose IN ('customer', 'own'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conname = 'uq_tenant_discord_config_tenant_purpose'
          AND  conrelid = 'public.tenant_discord_config'::regclass
    ) THEN
        ALTER TABLE public.tenant_discord_config
            ADD CONSTRAINT uq_tenant_discord_config_tenant_purpose UNIQUE (tenant_id, purpose);
    END IF;
END
$tdc_purpose$;
