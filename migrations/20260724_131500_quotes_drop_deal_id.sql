-- quotes.deal_id と対応FKを全 tenant スキーマから削除する（冪等）。
-- 実適用前提のmigration。データ行の書き込みは行わない。
DO $migration$
DECLARE
    s RECORD;
    quotes_exists BOOLEAN;
    deal_id_exists BOOLEAN;
    fk_exists BOOLEAN;
    applied_count INTEGER := 0;
    skipped_count INTEGER := 0;
BEGIN
    FOR s IN
        SELECT nspname
        FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = s.nspname
              AND table_name = 'quotes'
        ) INTO quotes_exists;

        IF NOT quotes_exists THEN
            skipped_count := skipped_count + 1;
            RAISE NOTICE '[quotes.deal_id] %: quotes table absent; skipped', s.nspname;
            CONTINUE;
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = s.nspname
              AND table_name = 'quotes'
              AND column_name = 'deal_id'
        ) INTO deal_id_exists;

        IF NOT deal_id_exists THEN
            skipped_count := skipped_count + 1;
            RAISE NOTICE '[quotes.deal_id] %: deal_id absent; skipped', s.nspname;
            CONTINUE;
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class r ON r.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = r.relnamespace
            WHERE n.nspname = s.nspname
              AND r.relname = 'quotes'
              AND c.conname = 'quotes_deal_id_fkey'
        ) INTO fk_exists;

        IF fk_exists THEN
            EXECUTE format(
                'ALTER TABLE %I.quotes DROP CONSTRAINT quotes_deal_id_fkey',
                s.nspname
            );
        ELSE
            RAISE NOTICE '[quotes.deal_id] %: quotes_deal_id_fkey absent; continuing', s.nspname;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.quotes DROP COLUMN deal_id',
            s.nspname
        );
        applied_count := applied_count + 1;
        RAISE NOTICE '[quotes.deal_id] %: applied (FK dropped: %)', s.nspname, fk_exists;
    END LOOP;

    RAISE NOTICE '[quotes.deal_id] summary: applied=%, skipped=%', applied_count, skipped_count;
END
$migration$;
