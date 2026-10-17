-- ADR-1024 便3a: AI 用の読み取り専用ビュー（秘密列を除く）。毎回の実行の最後に作り直す（冪等）。
-- 持ち主は実行ユーザー（run_sql の jarvis）のまま。security_invoker は付けない。
-- 拒否リスト（小文字化した列名）に当たる列はビューに含めない。fail-closed。
-- 既存の表・RLS ポリシー・public への権限には触らない。

BEGIN;

DROP SCHEMA IF EXISTS ai_ro CASCADE;
CREATE SCHEMA ai_ro;

DO $$
DECLARE
  t RECORD;
  cols text;
  n_views integer := 0;
  n_excluded integer := 0;
  n_kept integer;
  n_ex integer;
  deny constant text := '^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential';
BEGIN
  FOR t IN
    SELECT c.oid AS oid, n.nspname AS sch, c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r', 'p')
      AND (n.nspname = 'public' OR n.nspname LIKE 'tenant\_%')
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY n.nspname, c.relname
  LOOP
    SELECT
      string_agg(quote_ident(a.attname), ', ' ORDER BY a.attnum)
        FILTER (WHERE lower(a.attname) !~ deny),
      count(*) FILTER (WHERE lower(a.attname) !~ deny),
      count(*) FILTER (WHERE lower(a.attname) ~ deny)
    INTO cols, n_kept, n_ex
    FROM pg_attribute a
    WHERE a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped;

    n_excluded := n_excluded + n_ex;

    -- 列がすべて除かれた表はビューを作らない
    IF n_kept = 0 OR cols IS NULL THEN
      CONTINUE;
    END IF;

    EXECUTE format(
      'CREATE VIEW ai_ro.%I AS SELECT %s FROM %I.%I',
      t.sch || '__' || t.rel, cols, t.sch, t.rel
    );
    n_views := n_views + 1;
  END LOOP;

  RAISE NOTICE 'ai_ro views created: %, columns excluded: %', n_views, n_excluded;
END
$$;

GRANT USAGE ON SCHEMA ai_ro TO ai_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA ai_ro TO ai_reader;

COMMIT;
