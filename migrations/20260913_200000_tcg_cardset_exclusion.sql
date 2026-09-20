-- CARD-LINE-CARDSET-07: one additive keyword, tenant_004 only.
-- ADR-155 準拠修正: 商品データの存在を前提としない。
-- 商品が未登録の場合はスキップ（アプリ/CSV経由で登録後に再実行で反映）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
BEGIN
    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
    RAISE NOTICE '20260913_200000: no-op (values deprecated per ADR-155)';
END;
$body$;
COMMIT;
