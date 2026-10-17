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
  n_failed integer := 0;
  failed_list text := '';
  vname text;
  prefix text;
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

    -- ビュー名: 63 バイト以下はそのまま。超える場合は、先頭 54 バイト以内 + '_' + md5 先頭 8 桁
    -- （一意で決定的。PostgreSQL による名前の切り詰めで別の表と衝突するのを防ぐ）
    vname := t.sch || '__' || t.rel;
    IF octet_length(vname) > 63 THEN
      prefix := vname;
      WHILE octet_length(prefix) > 54 LOOP
        prefix := left(prefix, char_length(prefix) - 1);
      END LOOP;
      vname := prefix || '_' || left(md5(t.sch || '.' || t.rel), 8);
    END IF;

    -- ビューは AI が読むための補助。1 本の失敗でデプロイ全体を止めず、その表だけ「読めない」側に倒す
    BEGIN
      EXECUTE format(
        'CREATE VIEW ai_ro.%I AS SELECT %s FROM %I.%I',
        vname, cols, t.sch, t.rel
      );
      n_views := n_views + 1;
    EXCEPTION WHEN others THEN
      n_failed := n_failed + 1;
      failed_list := failed_list || ' ' || t.sch || '.' || t.rel;
    END;
  END LOOP;

  RAISE NOTICE 'ai_ro views created: %, columns excluded: %, failed: % [%]', n_views, n_excluded, n_failed, failed_list;
END
$$;

GRANT USAGE ON SCHEMA ai_ro TO ai_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA ai_ro TO ai_reader;

COMMIT;
