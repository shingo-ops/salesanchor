-- ADR-1052 段1: 相談係用の読み取り専用 DB ユーザー ai_reader_cloud（冪等）。ai_reader の写し（名前だけ違う）。
-- パスワードはここに書かない。パスワードのないロールは scram で入れない。
-- パスワード設定は PO が VPS で行う（secrets 変更）。
-- 付けないもの: pg_read_all_data / BYPASSRLS / ai_cloud 以外への権限。
-- ai_cloud への USAGE と SELECT は、ビューを作る 20261024_100300_create_ai_cloud_views.sql が付ける。

DO $$
DECLARE
  r pg_roles%ROWTYPE;
BEGIN
  SELECT * INTO r FROM pg_roles WHERE rolname = 'ai_reader_cloud';
  IF NOT FOUND THEN
    CREATE ROLE ai_reader_cloud LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;
  ELSIF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
        OR r.rolbypassrls OR NOT r.rolcanlogin OR r.rolconnlimit <> 2 THEN
    -- 同名ロールの属性が違う場合は勝手に ALTER せず止める
    RAISE EXCEPTION 'ai_reader_cloud already exists with unexpected attributes; stop and report';
  END IF;
END
$$;

-- 境界として効く唯一の設定: 全文を記録する
ALTER ROLE ai_reader_cloud SET log_statement = 'all';

-- 以下は事故防止であり境界ではない（利用者が SET で戻せる）
ALTER ROLE ai_reader_cloud SET default_transaction_read_only = on;
ALTER ROLE ai_reader_cloud SET statement_timeout = '60s';
ALTER ROLE ai_reader_cloud SET idle_in_transaction_session_timeout = '60s';
