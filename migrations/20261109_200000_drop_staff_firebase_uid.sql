-- firebase-removal 便4: 全テナントの staff から使わない列 firebase_uid を外す（構造のみ・冪等・ADR-1007）
--
-- 設計: docs/handoff/firebase-removal/design.md §5-4
-- 目的: ログインは自社の仕組み（ADR-1013）に替わり、アプリはこの列を読まない。人の正本は public.users.id。
-- 列が無いテナントは飛ばす。もう一度流しても結果は同じ。
-- ビューに使われていれば CASCADE しないので失敗して止まる（黙って消さない）。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（値は戻らない。列だけ戻す）:
--   各 tenant_NNN で ALTER TABLE tenant_NNN.staff ADD COLUMN IF NOT EXISTS firebase_uid VARCHAR(128) UNIQUE;
DO $drop_staff_fuid$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.table_schema AS schema_name
        FROM information_schema.columns c
        WHERE c.table_schema ~ '^tenant_[0-9]+$'
          AND c.table_name = 'staff'
          AND c.column_name = 'firebase_uid'
    LOOP
        EXECUTE format('ALTER TABLE %I.staff DROP COLUMN IF EXISTS firebase_uid', r.schema_name);
    END LOOP;
END
$drop_staff_fuid$;
