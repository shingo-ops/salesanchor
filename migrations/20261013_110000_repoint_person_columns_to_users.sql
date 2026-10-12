-- ADR-1008 P2: 「人」を指す残りの列の参照先を tenant staff(id) から public.users(id) に付け替える。
-- 対象: bots.owner_staff_id / order_commissions.staff_id / calendar_owner_settings.staff_id /
--       tenant_meta_config.connected_by_staff_id / meta_messages.sent_by_staff_id / meta_messages.seen_by_staff_id
-- 列名は変えない（毎デプロイ全 migration を流し直すため。列名変更は ADR-1005 の後）。構造のみ。値の付け替えは別途 D3。
-- 冪等: 表または列が無ければ飛ばす。staff 向け外部キーを外し、fk_<表>_<列>_user が無ければ作る。2回流しても同じ結果。

DO $$
DECLARE
    schema_rec RECORD;
    target RECORD;
    fk_name text;
    new_fk_name text;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        FOR target IN
            SELECT * FROM (VALUES
                ('bots',                   'owner_staff_id',          'NO ACTION'),
                ('order_commissions',      'staff_id',                'SET NULL'),
                ('calendar_owner_settings','staff_id',                'CASCADE'),
                ('tenant_meta_config',     'connected_by_staff_id',   'SET NULL'),
                ('meta_messages',          'sent_by_staff_id',        'SET NULL'),
                ('meta_messages',          'seen_by_staff_id',        'SET NULL')
            ) AS t(tbl, col, on_delete)
        LOOP
            IF to_regclass(schema_rec.nspname || '.' || target.tbl) IS NULL THEN
                CONTINUE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = schema_rec.nspname
                  AND table_name = target.tbl
                  AND column_name = target.col
            ) THEN
                CONTINUE;
            END IF;

            -- その列の staff(id) 向け外部キーを全て外す
            FOR fk_name IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = (schema_rec.nspname || '.' || target.tbl)::regclass
                  AND contype = 'f'
                  AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (' || target.col || ') REFERENCES%'
                  AND pg_get_constraintdef(oid) LIKE '%staff(id)%'
            LOOP
                EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT %I', schema_rec.nspname, target.tbl, fk_name);
            END LOOP;

            new_fk_name := 'fk_' || target.tbl || '_' || target.col || '_user';
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = (schema_rec.nspname || '.' || target.tbl)::regclass
                  AND contype = 'f'
                  AND conname = new_fk_name
            ) THEN
                EXECUTE format(
                    'ALTER TABLE %I.%I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES public.users(id) ON DELETE %s',
                    schema_rec.nspname, target.tbl, new_fk_name, target.col, target.on_delete
                );
            END IF;
        END LOOP;
    END LOOP;
END $$;
