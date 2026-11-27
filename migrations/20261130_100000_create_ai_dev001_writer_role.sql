-- ADR-1093 便2: AI 用「試験用テナント tenant_001 だけに書き込める」DB ロール ai_dev001_writer（冪等）
-- 設計: docs/handoff/dev-tenant001-writer/design.md §3-1・§3-2。パスワードはここに書かない（設定は便3で PO が行う）。
-- 付けないもの: public への権限・tenant_meta_config・秘密の列・DDL・TRUNCATE・tenant_001 以外のスキーマ。

-- (1) ロール。既にあって属性が違えば止める（勝手に ALTER しない）
DO $$
DECLARE
  r pg_roles%ROWTYPE;
BEGIN
  SELECT * INTO r FROM pg_roles WHERE rolname = 'ai_dev001_writer';
  IF NOT FOUND THEN
    CREATE ROLE ai_dev001_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;
  ELSIF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
        OR r.rolbypassrls OR NOT r.rolcanlogin OR r.rolconnlimit <> 2 THEN
    RAISE EXCEPTION 'ai_dev001_writer already exists with unexpected attributes; stop and report';
  END IF;
END
$$;

ALTER ROLE ai_dev001_writer SET log_statement = 'all';
ALTER ROLE ai_dev001_writer SET statement_timeout = '60s';
ALTER ROLE ai_dev001_writer SET lock_timeout = '1s';
ALTER ROLE ai_dev001_writer SET idle_in_transaction_session_timeout = '60s';

-- (2) 権限。規則 A0（スキーマ USAGE）・A（表）・B（秘密の列は列ごと）・C（連番）・D（無い物は飛ばす）を pg_catalog から組み立てる。
-- 表の名前は手で並べない。tenant_meta_config には付けない。public には何も付けない。
DO $dev001_grants$
DECLARE
  deny constant text := '^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$';
  tbl RECORD;
  safe_cols text;
BEGIN
  -- 規則 D: tenant_001 が無い DB（CI・試験用）では何もしない
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'tenant_001') THEN
    RETURN;
  END IF;

  -- 規則 A0: スキーマの USAGE だけ（CREATE は付けない）
  GRANT USAGE ON SCHEMA tenant_001 TO ai_dev001_writer;

  FOR tbl IN
    SELECT c.oid, c.relname
    FROM pg_class c
    WHERE c.relnamespace = 'tenant_001'::regnamespace
      AND c.relkind IN ('r', 'p')
      AND c.relname <> 'tenant_meta_config'
    ORDER BY c.relname
  LOOP
    IF EXISTS (
      SELECT 1 FROM pg_attribute a
      WHERE a.attrelid = tbl.oid AND a.attnum > 0 AND NOT a.attisdropped
        AND lower(a.attname) ~ deny
    ) THEN
      -- 規則 B: 秘密の列を持つ表は、秘密でない列だけに SELECT・INSERT・UPDATE、DELETE は表に付ける
      SELECT string_agg(format('%I', a.attname), ', ' ORDER BY a.attnum) INTO safe_cols
      FROM pg_attribute a
      WHERE a.attrelid = tbl.oid AND a.attnum > 0 AND NOT a.attisdropped
        AND NOT (lower(a.attname) ~ deny);
      IF safe_cols IS NOT NULL THEN
        EXECUTE format(
          'GRANT SELECT (%1$s), INSERT (%1$s), UPDATE (%1$s) ON tenant_001.%2$I TO ai_dev001_writer',
          safe_cols, tbl.relname);
      END IF;
      EXECUTE format('GRANT DELETE ON tenant_001.%I TO ai_dev001_writer', tbl.relname);
    ELSE
      -- 規則 A: 表ごと
      EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_001.%I TO ai_dev001_writer', tbl.relname);
    END IF;
  END LOOP;

  -- 規則 C: 連番は USAGE だけ（番号を進めるだけ。行は書けず setval もできない）
  GRANT USAGE ON ALL SEQUENCES IN SCHEMA tenant_001 TO ai_dev001_writer;
END
$dev001_grants$;
