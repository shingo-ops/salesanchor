-- ADR-1024 便3a: AI 用の読み取り専用 DB ユーザー ai_reader（冪等）
-- パスワードはここに書かない。パスワードのないロールは scram で入れない。
-- パスワード設定は便3b で PO が行う。
-- 付けないもの: pg_read_all_data / BYPASSRLS / ai_ro 以外への権限。

DO $$
DECLARE
  r pg_roles%ROWTYPE;
BEGIN
  SELECT * INTO r FROM pg_roles WHERE rolname = 'ai_reader';
  IF NOT FOUND THEN
    CREATE ROLE ai_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;
  ELSIF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
        OR r.rolbypassrls OR NOT r.rolcanlogin OR r.rolconnlimit <> 2 THEN
    -- 同名ロールの属性が違う場合は勝手に ALTER せず止める
    RAISE EXCEPTION 'ai_reader already exists with unexpected attributes; stop and report';
  END IF;
END
$$;

-- 境界として効く唯一の設定: 全文を記録する
ALTER ROLE ai_reader SET log_statement = 'all';

-- 以下は事故防止であり境界ではない（利用者が SET で戻せる）
ALTER ROLE ai_reader SET default_transaction_read_only = on;
ALTER ROLE ai_reader SET statement_timeout = '60s';
ALTER ROLE ai_reader SET idle_in_transaction_session_timeout = '60s';
