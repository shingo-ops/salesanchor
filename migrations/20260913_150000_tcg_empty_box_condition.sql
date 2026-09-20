-- CARD-LINE-EMPTY-BOX-REVIEW-01: tenant_004 only, no historical row rewrites.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
BEGIN
    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
    RAISE NOTICE '20260913_150000: no-op (values deprecated per ADR-155)';
END;
$body$;
COMMIT;
