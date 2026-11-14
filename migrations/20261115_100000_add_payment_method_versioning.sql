-- invoice-create-portfolio 便V: 振込先を版で持つ（design.md §3-8・ADR-1079）
-- 目的: 振込先を直しても消しても前の版を残し、発行済みの請求書が元の振込先を指し続けるようにする。
-- 中身（全テナント・冪等）:
--   tenant_invoice_payment_methods に superseded_by_id（次の版）と deleted_at（消した時刻）を足す
--   次の版を自分に向けない決まり・同じ表への外部キー・次の版は前の版1つだけの一意索引
--   見張りの関数3つと見張り6つ（振込先の行は消さない・版は書き換えない・詳細は書き足すだけ・表を空にしない）
-- 決まり: ADR-155（全テナントを回す移行）・ロック待ちは run_sql の lock_timeout に従う（ADR-1037）
-- 戻し方（手で流す。ここには書くだけ）:
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_methods_version_guard ON <schema>.tenant_invoice_payment_methods
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_bank_immutable ON <schema>.tenant_invoice_payment_bank
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_wise_immutable ON <schema>.tenant_invoice_payment_wise
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_methods_no_wipe ON <schema>.tenant_invoice_payment_methods
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_bank_no_wipe ON <schema>.tenant_invoice_payment_bank
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_wise_no_wipe ON <schema>.tenant_invoice_payment_wise
--   DROP FUNCTION IF EXISTS <schema>.trg_payment_detail_immutable()
--   DROP FUNCTION IF EXISTS <schema>.trg_payment_method_version_guard()
--   DROP FUNCTION IF EXISTS <schema>.trg_payment_version_no_wipe()
--   DROP INDEX IF EXISTS <schema>.uq_tenant_invoice_payment_methods_superseded_by
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP CONSTRAINT IF EXISTS fk_tenant_invoice_payment_methods_superseded_by
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP CONSTRAINT IF EXISTS chk_tenant_invoice_payment_methods_superseded_not_self
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP COLUMN IF EXISTS deleted_at
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP COLUMN IF EXISTS superseded_by_id

DO $$
DECLARE
    r RECORD;
    v_count INTEGER := 0;
    v_methods REGCLASS;
    v_detail CONSTANT TEXT := $pv_detail$
DECLARE
    v_id INTEGER;
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'payment detail rows are immutable (versioned). Add a new version instead.';
    END IF;
    IF NEW.payment_method_id IS NOT NULL THEN
        EXECUTE 'SELECT id, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.payment_method_id || ' FOR SHARE'
            INTO v_id, v_superseded, v_deleted;
        IF v_id IS NULL OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'payment detail can be added only to the current version of a payment method';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_detail$;
    v_method CONSTANT TEXT := $pv_method$
DECLARE
    v_id INTEGER;
    v_region VARCHAR(20);
    v_type VARCHAR(10);
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'payment methods cannot be deleted. Set deleted_at instead.';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.superseded_by_id IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a new payment method must start as the current version';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.region IS DISTINCT FROM OLD.region
        OR NEW.method_type IS DISTINCT FROM OLD.method_type
        OR NEW.display_name IS DISTINCT FROM OLD.display_name
        OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'payment method versions are immutable. Add a new version instead.';
    END IF;
    IF OLD.superseded_by_id IS NOT NULL AND NEW.superseded_by_id IS DISTINCT FROM OLD.superseded_by_id THEN
        RAISE EXCEPTION 'superseded_by_id can be set only once';
    END IF;
    IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
        RAISE EXCEPTION 'deleted_at can be set only once';
    END IF;
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL
        AND (OLD.superseded_by_id IS NOT NULL OR NEW.superseded_by_id IS NOT NULL) THEN
        RAISE EXCEPTION 'only the current version can be deleted';
    END IF;
    IF OLD.superseded_by_id IS NULL AND NEW.superseded_by_id IS NOT NULL THEN
        IF OLD.deleted_at IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a deleted payment method cannot be superseded';
        END IF;
        IF NEW.superseded_by_id <= OLD.id THEN
            RAISE EXCEPTION 'the next version must be newer than the current version';
        END IF;
        EXECUTE 'SELECT id, region, method_type, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.superseded_by_id || ' FOR SHARE'
            INTO v_id, v_region, v_type, v_superseded, v_deleted;
        IF v_id IS NULL OR v_region IS DISTINCT FROM OLD.region OR v_type IS DISTINCT FROM OLD.method_type
            OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'the next version must be a current version of the same region and type';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_method$;
    v_wipe CONSTANT TEXT := $pv_wipe$
BEGIN
    RAISE EXCEPTION 'payment version tables cannot be truncated';
    RETURN NULL;
END;
$pv_wipe$;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        IF to_regclass(format('%I.tenant_invoice_payment_methods', r.nspname)) IS NULL THEN
            RAISE EXCEPTION 'tenant_invoice_payment_methods is missing in %', r.nspname;
        END IF;
        v_methods := format('%I.tenant_invoice_payment_methods', r.nspname)::regclass;
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD COLUMN IF NOT EXISTS superseded_by_id INTEGER', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ', r.nspname);
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = v_methods AND conname = 'chk_tenant_invoice_payment_methods_superseded_not_self') THEN
            EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD CONSTRAINT chk_tenant_invoice_payment_methods_superseded_not_self CHECK (superseded_by_id <> id)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = v_methods AND conname = 'fk_tenant_invoice_payment_methods_superseded_by') THEN
            EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD CONSTRAINT fk_tenant_invoice_payment_methods_superseded_by FOREIGN KEY (superseded_by_id) REFERENCES %I.tenant_invoice_payment_methods (id)', r.nspname, r.nspname);
        END IF;
        EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_invoice_payment_methods_superseded_by ON %I.tenant_invoice_payment_methods (superseded_by_id) WHERE superseded_by_id IS NOT NULL', r.nspname);
        EXECUTE format('CREATE OR REPLACE FUNCTION %I.trg_payment_detail_immutable() RETURNS TRIGGER AS %L LANGUAGE plpgsql', r.nspname, v_detail);
        EXECUTE format('CREATE OR REPLACE FUNCTION %I.trg_payment_method_version_guard() RETURNS TRIGGER AS %L LANGUAGE plpgsql', r.nspname, v_method);
        EXECUTE format('CREATE OR REPLACE FUNCTION %I.trg_payment_version_no_wipe() RETURNS TRIGGER AS %L LANGUAGE plpgsql', r.nspname, v_wipe);
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_version_guard' AND tgrelid = format('%I.tenant_invoice_payment_methods', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_methods_version_guard BEFORE INSERT OR UPDATE OR DELETE ON %I.tenant_invoice_payment_methods FOR EACH ROW EXECUTE FUNCTION %I.trg_payment_method_version_guard()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_immutable' AND tgrelid = format('%I.tenant_invoice_payment_bank', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_bank_immutable BEFORE INSERT OR UPDATE OR DELETE ON %I.tenant_invoice_payment_bank FOR EACH ROW EXECUTE FUNCTION %I.trg_payment_detail_immutable()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_immutable' AND tgrelid = format('%I.tenant_invoice_payment_wise', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_wise_immutable BEFORE INSERT OR UPDATE OR DELETE ON %I.tenant_invoice_payment_wise FOR EACH ROW EXECUTE FUNCTION %I.trg_payment_detail_immutable()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_no_wipe' AND tgrelid = format('%I.tenant_invoice_payment_methods', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_methods_no_wipe BEFORE TRUNCATE ON %I.tenant_invoice_payment_methods FOR EACH STATEMENT EXECUTE FUNCTION %I.trg_payment_version_no_wipe()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_no_wipe' AND tgrelid = format('%I.tenant_invoice_payment_bank', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_bank_no_wipe BEFORE TRUNCATE ON %I.tenant_invoice_payment_bank FOR EACH STATEMENT EXECUTE FUNCTION %I.trg_payment_version_no_wipe()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_no_wipe' AND tgrelid = format('%I.tenant_invoice_payment_wise', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_wise_no_wipe BEFORE TRUNCATE ON %I.tenant_invoice_payment_wise FOR EACH STATEMENT EXECUTE FUNCTION %I.trg_payment_version_no_wipe()', r.nspname, r.nspname);
        END IF;
        v_count := v_count + 1;
    END LOOP;
    RAISE NOTICE 'payment method versioning applied to % tenant schemas', v_count;
END $$;
