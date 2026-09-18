-- ============================================================================
-- Migration 20260918_100000: tcg_suppliers → tenant_suppliers リネーム
--
-- 背景:
--   仕入元マスタ SSOT 完了後、tcg_suppliers のデータは public.suppliers に
--   移植済み。テナント独自の仕入元登録用にテーブル構造のみ残し、
--   名称を tenant_suppliers に変更する。
--
-- 冪等性:
--   - tcg_suppliers が存在すれば RENAME + TRUNCATE
--   - 既に tenant_suppliers なら skip
--
-- 作成日: 2026-09-18
-- ============================================================================

DO $$
DECLARE
    _schema TEXT;
BEGIN
    FOR _schema IN
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind = 'r'
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_suppliers'
        ORDER BY n.nspname
    LOOP
        EXECUTE format('ALTER TABLE %I.tcg_suppliers RENAME TO tenant_suppliers', _schema);
        EXECUTE format('TRUNCATE %I.tenant_suppliers', _schema);
        RAISE NOTICE 'Renamed and truncated %.tcg_suppliers → tenant_suppliers', _schema;
    END LOOP;
END $$;
