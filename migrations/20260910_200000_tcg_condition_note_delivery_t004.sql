-- CARD-LINE-CONDITION-NOTE-01: master-only, never rewrite extraction/results.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
BEGIN
    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
    RAISE NOTICE '20260910_200000: no-op (values deprecated per ADR-155)';
END;
$body$;
COMMIT;
