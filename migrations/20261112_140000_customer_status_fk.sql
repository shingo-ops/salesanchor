-- 会社と連絡先の状態 便2: status 列を public.customer_statuses に外部キーで結び、旧 CHECK を外す
--
-- 設計: docs/handoff/status-ssot-contact-company/design.md §5（ADR-1076）
-- 全会社の領域（tenant_NNN）の companies・contacts で: 外部キーを NOT VALID で足す → VALIDATE → 旧 CHECK を外す。
-- 止め役は VALIDATE そのもの: 会社・連絡先の status に表に無い値があれば外部キー違反で失敗し、移行全体が止まる（4行の投入前に流すと止まる）。
-- 表や status 列が無い領域は飛ばす。外部キーが有効で旧 CHECK が無い領域は飛ばす（流し直しで ALTER を出さない・鍵を取りに行かない）。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）
--
-- ロールバック（領域ごと・PO GO）: docs/handoff/status-ssot-contact-company/card-bin2.md「戻し方」

DO $fk$
DECLARE
    _schema TEXT;
    _tbl    TEXT;
    _fk     TEXT;
    _chk    TEXT;
    _valid  BOOLEAN;
BEGIN
    FOR _schema IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' ORDER BY nspname
    LOOP
        FOREACH _tbl IN ARRAY ARRAY['companies', 'contacts']
        LOOP
            _fk  := _tbl || '_status_fkey';
            _chk := _tbl || '_status_check';

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = _schema AND table_name = _tbl AND column_name = 'status'
            ) THEN
                RAISE NOTICE 'customer_status_fk: %.% に status 列が無いので飛ばす', _schema, _tbl;
                CONTINUE;
            END IF;

            _valid := NULL;
            SELECT con.convalidated INTO _valid
            FROM pg_constraint con
            WHERE con.conrelid = format('%I.%I', _schema, _tbl)::regclass
              AND con.conname = _fk;

            IF _valid IS TRUE AND NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = format('%I.%I', _schema, _tbl)::regclass AND conname = _chk
            ) THEN
                CONTINUE;
            END IF;

            IF _valid IS NULL THEN
                EXECUTE format(
                    'ALTER TABLE %I.%I ADD CONSTRAINT %I FOREIGN KEY (status) REFERENCES public.customer_statuses (code) NOT VALID',
                    _schema, _tbl, _fk);
            END IF;
            IF _valid IS NOT TRUE THEN
                EXECUTE format('ALTER TABLE %I.%I VALIDATE CONSTRAINT %I', _schema, _tbl, _fk);
            END IF;
            EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I', _schema, _tbl, _chk);
            RAISE NOTICE 'customer_status_fk: %.% を外部キーに付け替えた', _schema, _tbl;
        END LOOP;
    END LOOP;
END $fk$;
