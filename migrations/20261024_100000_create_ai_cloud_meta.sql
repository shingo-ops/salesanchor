-- ADR-1052 段1: 相談係用の伏せたビュー ai_cloud の「部品」を置くスキーマ ai_cloud_meta（冪等）。
-- 置くもの: 分類表 column_class・作成の記録 build_log・列ごとの出し方の記録 build_columns・生成関数 build_views()。
-- ai_cloud を DROP SCHEMA CASCADE しても消えないよう、ai_cloud の外に置く。
-- 中身は表と列の名前・件数だけで、値は入らない。
-- 権限: PUBLIC から全部外す。ai_reader にだけ USAGE と 3 表の SELECT。ai_reader_cloud には何も付けない。
--       関数 build_views() の EXECUTE はだれにも付けない（呼ぶのは持ち主の jarvis だけ）。
-- ビューの作成そのものは 20261024_100300_create_ai_cloud_views.sql（一覧に載せず EXIT trap から流す）。

CREATE SCHEMA IF NOT EXISTS ai_cloud_meta;

CREATE TABLE IF NOT EXISTS ai_cloud_meta.column_class (
  schema_pattern text NOT NULL CHECK (schema_pattern IN ('public', 'tenant_*')),
  table_name text NOT NULL,
  column_name text NOT NULL,
  class text NOT NULL CHECK (class IN ('allow', 'mask', 'mask_bare')),
  reason text NOT NULL DEFAULT '',
  PRIMARY KEY (schema_pattern, table_name, column_name),
  CHECK (class <> 'allow' OR reason <> '')
);

CREATE TABLE IF NOT EXISTS ai_cloud_meta.build_log (
  built_at timestamptz NOT NULL DEFAULT now(),
  ok boolean NOT NULL,
  view_count integer,
  failed_count integer,
  error_class text
);

CREATE TABLE IF NOT EXISTS ai_cloud_meta.build_columns (
  view_name text NOT NULL,
  column_name text NOT NULL,
  source text NOT NULL,
  source_type text NOT NULL,
  class text,
  mode text NOT NULL CHECK (mode IN ('pass', 'mask', 'mask_bare', 'excluded'))
);

COMMENT ON TABLE ai_cloud_meta.column_class IS 'ai_cloud の列の分類（allow=そのまま・mask=形だけ・mask_bare=masked だけ）。tenant_* は型紙の表の名前で 1 行。';
COMMENT ON COLUMN ai_cloud_meta.column_class.schema_pattern IS 'public、またはテナントのスキーマすべてを表す tenant_*';
COMMENT ON COLUMN ai_cloud_meta.column_class.table_name IS '元の表の名前';
COMMENT ON COLUMN ai_cloud_meta.column_class.column_name IS '元の列の名前';
COMMENT ON COLUMN ai_cloud_meta.column_class.class IS 'allow / mask / mask_bare';
COMMENT ON COLUMN ai_cloud_meta.column_class.reason IS 'allow の根拠（空は不可）。mask 系は空でよい';
COMMENT ON TABLE ai_cloud_meta.build_log IS 'ai_cloud を作るたびの結果の記録（件数と失敗の種類だけ。値は入らない）';
COMMENT ON COLUMN ai_cloud_meta.build_log.built_at IS '記録した時刻';
COMMENT ON COLUMN ai_cloud_meta.build_log.ok IS '失敗した表が 0 なら true';
COMMENT ON COLUMN ai_cloud_meta.build_log.view_count IS '作ったビューの数';
COMMENT ON COLUMN ai_cloud_meta.build_log.failed_count IS '作成に失敗した表の数';
COMMENT ON COLUMN ai_cloud_meta.build_log.error_class IS '全体が失敗したときの種類（例 psql_failed）';
COMMENT ON TABLE ai_cloud_meta.build_columns IS 'ai_cloud のビューの列ごとの出し方（受入と点検用。作るたびに書き直す）';
COMMENT ON COLUMN ai_cloud_meta.build_columns.view_name IS 'ai_cloud のビュー名';
COMMENT ON COLUMN ai_cloud_meta.build_columns.column_name IS '列の名前';
COMMENT ON COLUMN ai_cloud_meta.build_columns.source IS '元の表（スキーマ.表）';
COMMENT ON COLUMN ai_cloud_meta.build_columns.source_type IS '元の列の型';
COMMENT ON COLUMN ai_cloud_meta.build_columns.class IS '分類表の class（無ければ NULL）';
COMMENT ON COLUMN ai_cloud_meta.build_columns.mode IS 'pass=そのまま / mask / mask_bare / excluded=秘密列で外した';

CREATE OR REPLACE FUNCTION ai_cloud_meta.build_views()
RETURNS TABLE(view_count integer, failed_count integer)
LANGUAGE plpgsql
SECURITY INVOKER
AS $fn$
DECLARE
  t RECORD;
  c RECORD;
  select_list text;
  expr text;
  v_mode text;
  n_pass integer;
  n_views integer := 0;
  n_failed integer := 0;
  vname text;
  prefix text;
  rows_json jsonb;
  deny constant text := '^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential';
BEGIN
  TRUNCATE ai_cloud_meta.build_columns;

  FOR t IN
    SELECT cl.oid AS oid, n.nspname AS sch, cl.relname AS rel
    FROM pg_class cl
    JOIN pg_namespace n ON n.oid = cl.relnamespace
    WHERE cl.relkind IN ('r', 'p')
      AND (n.nspname = 'public' OR n.nspname LIKE 'tenant\_%')
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND NOT (n.nspname = 'public' AND cl.relname LIKE '\_\_backup%')
      AND cl.relname !~ '(_bak_|_backup|baseline_)'
    ORDER BY n.nspname, cl.relname
  LOOP
    select_list := NULL;
    n_pass := 0;
    rows_json := '[]'::jsonb;

    FOR c IN
      SELECT a.attname AS col,
             format_type(a.atttypid, a.atttypmod) AS typ_text,
             ty.typname AS typname,
             ty.typtype AS typtype,
             ty.typcategory AS typcat,
             cc.class AS cls
      FROM pg_attribute a
      JOIN pg_type ty ON ty.oid = a.atttypid
      LEFT JOIN ai_cloud_meta.column_class cc
        ON cc.schema_pattern = CASE WHEN t.sch = 'public' THEN 'public' ELSE 'tenant_*' END
       AND cc.table_name = t.rel
       AND cc.column_name = a.attname
      WHERE a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped
      ORDER BY a.attnum
    LOOP
      IF lower(c.col) ~ deny THEN
        v_mode := 'excluded';
        expr := NULL;
      ELSIF c.cls = 'mask_bare' THEN
        v_mode := 'mask_bare';
        expr := format($f$CASE WHEN %1$I IS NULL THEN NULL ELSE 'masked' END$f$, c.col);
      ELSIF c.cls = 'mask' THEN
        v_mode := 'mask';
      ELSIF c.cls = 'allow' THEN
        v_mode := 'pass';
        expr := quote_ident(c.col);
      ELSIF (c.typtype = 'b' AND c.typcat <> 'A'
             AND c.typname IN ('int2', 'int4', 'int8', 'numeric', 'float4', 'float8', 'bool', 'date',
                               'time', 'timetz', 'timestamp', 'timestamptz', 'interval', 'uuid'))
            OR c.typtype = 'e' THEN
        v_mode := 'pass';
        expr := quote_ident(c.col);
      ELSE
        v_mode := 'mask';
      END IF;

      IF v_mode = 'mask' THEN
        IF c.typcat = 'A' THEN
          expr := format($f$CASE WHEN %1$I IS NULL THEN NULL ELSE 'masked:array:n=' || coalesce(cardinality(%1$I), 0) END$f$, c.col);
        ELSIF c.typname IN ('json', 'jsonb') THEN
          expr := format($f$CASE WHEN %1$I IS NULL THEN NULL ELSE 'masked:json:len=' || char_length(%1$I::text) || ':keys=' || CASE WHEN jsonb_typeof(%1$I::jsonb) = 'object' THEN (SELECT count(*) FROM jsonb_object_keys(%1$I::jsonb))::text ELSE '0' END END$f$, c.col);
        ELSE
          expr := format($f$CASE WHEN %1$I IS NULL THEN NULL WHEN %1$I::text = '' THEN '' ELSE 'masked:len=' || char_length(%1$I::text) || ':' || CASE WHEN %1$I::text ~ '^[0-9]+$' THEN 'digits' WHEN %1$I::text ~ '^[\x01-\x7f]+$' THEN 'ascii' WHEN %1$I::text !~ '[\x01-\x7f]' THEN 'multibyte' ELSE 'mixed' END END$f$, c.col);
        END IF;
      END IF;

      rows_json := rows_json || jsonb_build_array(jsonb_build_array(c.col, c.typ_text, c.cls, v_mode));
      IF v_mode <> 'excluded' THEN
        select_list := coalesce(select_list || ', ', '') || expr || ' AS ' || quote_ident(c.col);
        IF v_mode = 'pass' THEN
          n_pass := n_pass + 1;
        END IF;
      END IF;
    END LOOP;

    -- 列がすべて除かれた表はビューを作らない
    IF select_list IS NULL THEN
      CONTINUE;
    END IF;

    -- ビュー名: 63 バイト以下はそのまま。超える場合は、先頭 54 バイト以内 + '_' + md5 先頭 8 桁
    vname := t.sch || '__' || t.rel;
    IF octet_length(vname) > 63 THEN
      prefix := vname;
      WHILE octet_length(prefix) > 54 LOOP
        prefix := left(prefix, char_length(prefix) - 1);
      END LOOP;
      vname := prefix || '_' || left(md5(t.sch || '.' || t.rel), 8);
    END IF;

    -- 1 本の失敗でデプロイ全体を止めず、その表だけ「読めない」側に倒す（失敗は failed_count に数える）
    BEGIN
      EXECUTE format('CREATE VIEW ai_cloud.%I AS SELECT %s FROM %I.%I', vname, select_list, t.sch, t.rel);
      INSERT INTO ai_cloud_meta.build_columns (view_name, column_name, source, source_type, class, mode)
      SELECT vname, r.e ->> 0, t.sch || '.' || t.rel, r.e ->> 1, r.e ->> 2, r.e ->> 3
      FROM jsonb_array_elements(rows_json) AS r(e);
      n_views := n_views + 1;
    EXCEPTION WHEN others THEN
      n_failed := n_failed + 1;
    END;
  END LOOP;

  view_count := n_views;
  failed_count := n_failed;
  RETURN NEXT;
END
$fn$;

REVOKE ALL ON SCHEMA ai_cloud_meta FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA ai_cloud_meta FROM PUBLIC;
REVOKE ALL ON FUNCTION ai_cloud_meta.build_views() FROM PUBLIC;

GRANT USAGE ON SCHEMA ai_cloud_meta TO ai_reader;
GRANT SELECT ON ai_cloud_meta.column_class, ai_cloud_meta.build_log, ai_cloud_meta.build_columns TO ai_reader;
