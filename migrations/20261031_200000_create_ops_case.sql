-- ADR-1052 段2: 相談係の「件」の部品（スキーマ ops_case）と、値を 1 回だけ返す関数 unmask_fetch（冪等）。
-- 置くもの: 表 6 つ（cases・reports・unmask_requests・unmask_reads・audits・deny_tables）、ロール 2 つ
--           （ai_unmask_owner＝関数の持ち主・ai_unmask＝呼ぶ側）、関数 3 つ
--           （is_denied_source・unmask_fetch・grant_unmask_owner）。
-- 値の列は持たない（unmask_reads も件数と列の名前だけ）。値を返すのは unmask_fetch だけで、1 申請につき 1 回。
-- ai_unmask のパスワードはここに書かない（PO が VPS で設定する。パスワードの無いロールは scram で入れない）。
-- 設計: docs/handoff/cloud-case-ai/design.md §4-A・実装カード docs/handoff/cloud-case-ai/stage2-card.md §4-A。

CREATE SCHEMA IF NOT EXISTS ops_case;
REVOKE ALL ON SCHEMA ops_case FROM PUBLIC;

-- 1. 件ごとの札（札そのものは持たず、sha256 の hex だけ）
CREATE TABLE IF NOT EXISTS ops_case.cases (
    incident_id        uuid        PRIMARY KEY REFERENCES public.ops_incidents(id),
    ticket_hash        text,
    ticket_expires_at  timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT cases_ticket_hash_check CHECK (ticket_hash ~ '^[0-9a-f]{64}$')
);

-- 2. 相談係の報告（1 件につき 1 通。2 回目は一意制約で 409）
CREATE TABLE IF NOT EXISTS ops_case.reports (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id     uuid        NOT NULL UNIQUE REFERENCES ops_case.cases(incident_id),
    status          text        CHECK (status IN ('investigating', 'reported')),
    summary         text,
    cause           text,
    evidence        jsonb,
    proposal        jsonb,
    risk            text,
    needs_decision  text,
    received_at     timestamptz NOT NULL DEFAULT now()
);

-- 3. 値を見たい申請（理由・列・行のキーだけ。値は入らない）
CREATE TABLE IF NOT EXISTS ops_case.unmask_requests (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id      uuid        NOT NULL REFERENCES ops_case.cases(incident_id),
    view_name        text        NOT NULL,
    column_names     text[]      NOT NULL CHECK (cardinality(column_names) BETWEEN 1 AND 5),
    row_keys         text[]      NOT NULL CHECK (cardinality(row_keys) BETWEEN 1 AND 20),
    reason           text        NOT NULL CHECK (char_length(reason) BETWEEN 20 AND 1000),
    status           text        NOT NULL DEFAULT 'pending'
                                 CHECK (status IN ('pending', 'approved', 'denied', 'expired')),
    decided_by       text,
    decision_reason  text,
    approved_minutes integer     CHECK (approved_minutes BETWEEN 1 AND 15),
    expires_at       timestamptz,
    max_reads        integer     NOT NULL DEFAULT 1 CHECK (max_reads = 1),
    read_count       integer     NOT NULL DEFAULT 0 CHECK (read_count >= 0 AND read_count <= max_reads),
    created_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT unmask_requests_approved_check
        CHECK (status <> 'approved' OR (approved_minutes IS NOT NULL AND expires_at IS NOT NULL))
);

-- 4. 読み出しの記録（件数と列の名前だけ。値の列は持たない）
CREATE TABLE IF NOT EXISTS ops_case.unmask_reads (
    id            bigserial   PRIMARY KEY,
    request_id    uuid        NOT NULL REFERENCES ops_case.unmask_requests(id),
    read_at       timestamptz NOT NULL DEFAULT now(),
    row_count     integer     NOT NULL,
    column_names  text[]      NOT NULL
);

-- 5. 週次点検の結果
CREATE TABLE IF NOT EXISTS ops_case.audits (
    id             bigserial   PRIMARY KEY,
    ran_at         timestamptz NOT NULL DEFAULT now(),
    findings       jsonb       NOT NULL,
    finding_count  integer     NOT NULL
);

-- 6. 拒否表（表の名前だけ。スキーマは問わない）。この migration が正本
CREATE TABLE IF NOT EXISTS ops_case.deny_tables (
    table_name  text PRIMARY KEY,
    reason      text NOT NULL
);

COMMENT ON SCHEMA ops_case IS 'ADR-1052 段2: 相談係の件・申請・読み出しの記録。値は持たない';
COMMENT ON TABLE ops_case.cases IS '件ごとの札のハッシュと期限（札そのものは持たない）';
COMMENT ON TABLE ops_case.reports IS '相談係の報告。1 件につき 1 通';
COMMENT ON TABLE ops_case.unmask_requests IS '値を見たい申請。理由・列・行のキーだけで値は無い。max_reads は 1 固定';
COMMENT ON TABLE ops_case.unmask_reads IS '読み出しの記録。件数と列の名前だけ';
COMMENT ON TABLE ops_case.audits IS '週次点検の結果';
COMMENT ON TABLE ops_case.deny_tables IS '値を返さない表の名前。スキーマは問わない（正本はこの migration）';

-- 拒否表は migration が正本。1 つの取引で入れ替える（途中の空の状態を見せない）
DO $deny$
BEGIN
    TRUNCATE ops_case.deny_tables;
    INSERT INTO ops_case.deny_tables (table_name, reason) VALUES
        ('users', '認証情報（パスワードのハッシュ等）'),
        ('viewer_accounts', '閲覧者アカウントの認証情報'),
        ('auth_events', '認証の記録'),
        ('auth_refresh_tokens', 'リフレッシュトークン'),
        ('password_reset_tokens', 'パスワード再設定の札'),
        ('registration_tokens', '登録用の札'),
        ('viewer_login_events', '閲覧者ログインの記録'),
        ('viewer_login_tokens', '閲覧者ログインの札'),
        ('webauthn_credentials', 'パスキーの公開鍵・資格情報'),
        ('tenant_carrier_credentials', '運送会社の資格情報');
END
$deny$;

-- 2. RLS（ops_incidents と同じ形。運用者の旗が立った接続だけ。DELETE のポリシーは作らない）
ALTER TABLE ops_case.cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE ops_case.cases FORCE ROW LEVEL SECURITY;
ALTER TABLE ops_case.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE ops_case.reports FORCE ROW LEVEL SECURITY;
ALTER TABLE ops_case.unmask_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE ops_case.unmask_requests FORCE ROW LEVEL SECURITY;
ALTER TABLE ops_case.unmask_reads ENABLE ROW LEVEL SECURITY;
ALTER TABLE ops_case.unmask_reads FORCE ROW LEVEL SECURITY;
ALTER TABLE ops_case.audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE ops_case.audits FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cases_operator_select ON ops_case.cases;
CREATE POLICY cases_operator_select ON ops_case.cases
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS cases_operator_insert ON ops_case.cases;
CREATE POLICY cases_operator_insert ON ops_case.cases
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS cases_operator_update ON ops_case.cases;
CREATE POLICY cases_operator_update ON ops_case.cases
    FOR UPDATE
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS reports_operator_select ON ops_case.reports;
CREATE POLICY reports_operator_select ON ops_case.reports
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS reports_operator_insert ON ops_case.reports;
CREATE POLICY reports_operator_insert ON ops_case.reports
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS unmask_requests_operator_select ON ops_case.unmask_requests;
CREATE POLICY unmask_requests_operator_select ON ops_case.unmask_requests
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS unmask_requests_operator_insert ON ops_case.unmask_requests;
CREATE POLICY unmask_requests_operator_insert ON ops_case.unmask_requests
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS unmask_requests_operator_update ON ops_case.unmask_requests;
CREATE POLICY unmask_requests_operator_update ON ops_case.unmask_requests
    FOR UPDATE
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS unmask_reads_operator_select ON ops_case.unmask_reads;
CREATE POLICY unmask_reads_operator_select ON ops_case.unmask_reads
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS audits_operator_select ON ops_case.audits;
CREATE POLICY audits_operator_select ON ops_case.audits
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS audits_operator_insert ON ops_case.audits;
CREATE POLICY audits_operator_insert ON ops_case.audits
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');

REVOKE ALL ON ALL TABLES IN SCHEMA ops_case FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA ops_case FROM PUBLIC;

-- 3. ロール（属性が違う同名ロールがあれば勝手に直さず止める）
DO $roles$
DECLARE
    r pg_roles%ROWTYPE;
BEGIN
    SELECT * INTO r FROM pg_roles WHERE rolname = 'ai_unmask_owner';
    IF NOT FOUND THEN
        CREATE ROLE ai_unmask_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS;
    ELSIF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
          OR NOT r.rolbypassrls OR r.rolcanlogin THEN
        RAISE EXCEPTION 'ai_unmask_owner already exists with unexpected attributes; stop and report';
    END IF;

    SELECT * INTO r FROM pg_roles WHERE rolname = 'ai_unmask';
    IF NOT FOUND THEN
        CREATE ROLE ai_unmask LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;
    ELSIF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
          OR r.rolbypassrls OR NOT r.rolcanlogin OR r.rolconnlimit <> 2 THEN
        RAISE EXCEPTION 'ai_unmask already exists with unexpected attributes; stop and report';
    END IF;
END
$roles$;

-- ai_unmask: 文を DB の記録に一切残さない（呼び出しの文に件の札が入るため）。
-- 断った回（エラー）も log_min_error_statement=panic で文を出さない。返した値はどの設定でも記録に出ない。
ALTER ROLE ai_unmask SET log_statement = 'none';
ALTER ROLE ai_unmask SET log_min_error_statement = 'panic';
ALTER ROLE ai_unmask SET log_min_duration_statement = -1;
ALTER ROLE ai_unmask SET statement_timeout = '10s';
ALTER ROLE ai_unmask SET idle_in_transaction_session_timeout = '30s';
-- default_transaction_read_only は付けない（読み出しの記録を書く取引が要る）

-- 4. 関数
-- 4-1. 値を返してはいけない元の表か（backend の申請の受付・unmask_fetch・権限の付け直しの 3 か所がこの関数だけを呼ぶ）
CREATE OR REPLACE FUNCTION ops_case.is_denied_source(p_source text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
STABLE
SET search_path = pg_catalog, pg_temp
AS $fn$
DECLARE
    v_n   integer;
    v_rel text;
BEGIN
    IF p_source IS NULL THEN
        RETURN true;
    END IF;
    -- 文字を割らず、「スキーマ.表」が 1 つの表に解けるかを見る（解けない・2 つ以上なら断る側）
    SELECT count(*), min(c.relname::text)
      INTO v_n, v_rel
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname || '.' || c.relname = p_source
       AND c.relkind IN ('r', 'p');
    IF v_n <> 1 THEN
        RETURN true;
    END IF;
    RETURN EXISTS (SELECT 1 FROM ops_case.deny_tables d WHERE d.table_name = v_rel)
        OR EXISTS (SELECT 1 FROM ai_cloud_meta.build_columns b WHERE b.source = p_source AND b.mode = 'excluded');
END
$fn$;

-- 4-2. 許可された申請の値を 1 回だけ返す（持ち主 ai_unmask_owner が元の表を読む）
CREATE OR REPLACE FUNCTION ops_case.unmask_fetch(p_request_id uuid, p_ticket text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
SET lock_timeout = '2s'
AS $fn$
DECLARE
    v         record;
    v_source  text;
    v_n       integer;
    v_oid     oid;
    v_nsp     text;
    v_rel     text;
    v_pk      text;
    v_pktype  text;
    v_cols    text;
    v_ncols   integer;
    v_sql     text;
    v_rows    jsonb;
    v_count   integer;
BEGIN
    -- 1. 申請を取り、同時に来た読み出しを待たせる（印は理由の短い名前だけ。値・名前・札は入れない）
    SELECT r.id, r.status, r.expires_at, r.read_count, r.max_reads, r.view_name,
           r.column_names, r.row_keys, c.ticket_hash, c.ticket_expires_at
      INTO v
      FROM ops_case.unmask_requests r
      JOIN ops_case.cases c ON c.incident_id = r.incident_id
     WHERE r.id = p_request_id
       FOR UPDATE OF r;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'not_found';
    END IF;

    -- 2. 申請の件の札だけが通る
    IF p_ticket IS NULL OR v.ticket_hash IS NULL OR v.ticket_expires_at IS NULL
       OR encode(sha256(convert_to(p_ticket, 'UTF8')), 'hex') <> v.ticket_hash
       OR now() >= v.ticket_expires_at THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'ticket';
    END IF;

    -- 3〜5. 許可の状態・期限・回数
    IF v.status <> 'approved' THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'status';
    END IF;
    IF v.expires_at IS NULL OR now() >= v.expires_at THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'expired';
    END IF;
    IF v.read_count >= v.max_reads THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'used';
    END IF;

    -- 6. ビューが ai_cloud に実在する
    IF NOT EXISTS (
        SELECT 1
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'ai_cloud' AND c.relname = v.view_name AND c.relkind = 'v'
    ) THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'view';
    END IF;

    -- 7. 元の表を 1 つに決め、拒否表・秘密列を持つ表でないこと
    SELECT count(DISTINCT b.source), min(b.source)
      INTO v_n, v_source
      FROM ai_cloud_meta.build_columns b
     WHERE b.view_name = v.view_name;
    IF v_n <> 1 THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'source';
    END IF;
    SELECT count(*)
      INTO v_n
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname || '.' || c.relname = v_source AND c.relkind IN ('r', 'p');
    IF v_n <> 1 THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'source';
    END IF;
    SELECT c.oid, n.nspname::text, c.relname::text
      INTO v_oid, v_nsp, v_rel
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname || '.' || c.relname = v_source AND c.relkind IN ('r', 'p');
    IF ops_case.is_denied_source(v_source) THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'source';
    END IF;

    -- 8. 列は全部そのビューの列で、秘密列として外された列でない
    IF EXISTS (
        SELECT 1
          FROM unnest(v.column_names) AS u(cn)
         WHERE NOT EXISTS (
             SELECT 1
               FROM ai_cloud_meta.build_columns b
              WHERE b.view_name = v.view_name AND b.column_name = u.cn AND b.mode <> 'excluded'
         )
    ) THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'column';
    END IF;

    -- 9. 主キーが 1 列で、型が 6 種のどれか
    SELECT a.attname::text, pg_catalog.format_type(a.atttypid, NULL)
      INTO v_pk, v_pktype
      FROM pg_catalog.pg_index i
      JOIN pg_catalog.pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
     WHERE i.indrelid = v_oid AND i.indisprimary AND i.indnatts = 1
       AND a.atttypid IN ('int2'::regtype, 'int4'::regtype, 'int8'::regtype, 'uuid'::regtype,
                          'text'::regtype, 'varchar'::regtype);
    IF v_pk IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'key';
    END IF;

    -- 列の名前は元の表のカタログの名前（%I）で組み立てる
    SELECT string_agg(pg_catalog.format('%I', a.attname), ', ' ORDER BY a.attnum), count(*)
      INTO v_cols, v_ncols
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_oid AND a.attnum > 0 AND NOT a.attisdropped
       AND a.attname::text = ANY (v.column_names);
    IF v_cols IS NULL OR v_ncols <> (SELECT count(DISTINCT u.cn) FROM unnest(v.column_names) AS u(cn)) THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'column';
    END IF;

    v_sql := pg_catalog.format(
        'SELECT coalesce(jsonb_agg(s.j), ''[]''::jsonb) FROM '
        '(SELECT to_jsonb(t) AS j FROM (SELECT %I AS __key, %s FROM %I.%I WHERE %I = ANY ($1::%s[])) t) s',
        v_pk, v_cols, v_nsp, v_rel, v_pk, v_pktype);

    -- 読み出し。失敗は全部 read_failed に変える（型の変換・ロック待ちの時間切れを含め、元の文や値を外に出さない）
    -- 57014（statement_timeout）は OTHERS で捕まらずそのまま外に出る
    BEGIN
        EXECUTE v_sql INTO v_rows USING v.row_keys;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'read_failed';
    END;

    v_count := jsonb_array_length(v_rows);

    UPDATE ops_case.unmask_requests SET read_count = read_count + 1 WHERE id = p_request_id;
    INSERT INTO ops_case.unmask_reads (request_id, row_count, column_names)
    VALUES (p_request_id, v_count, v.column_names);

    RETURN jsonb_build_object('request_id', p_request_id, 'rows', v_rows, 'row_count', v_count);
END
$fn$;

-- 4-3. 持ち主 ai_unmask_owner の権限を、今の ai_cloud の元の表に合わせて付け直す（違う表だけ変える）
--      呼ぶのは deploy の最後の jarvis だけ。戻り値は付けた表の数と外した表の数の合計
CREATE OR REPLACE FUNCTION ops_case.grant_unmask_owner()
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, pg_temp
SET lock_timeout = '2s'
AS $fn$
DECLARE
    v_owner    oid;
    v_want     oid[];
    t          record;
    v_changed  integer := 0;
BEGIN
    SELECT o.oid INTO v_owner FROM pg_catalog.pg_roles o WHERE o.rolname = 'ai_unmask_owner';
    IF v_owner IS NULL THEN
        RAISE EXCEPTION 'ai_unmask_owner not found';
    END IF;

    -- 1. 付けるべき表: build_columns の source のうち、拒否に当たらないもの
    SELECT coalesce(array_agg(DISTINCT c.oid), '{}'::oid[])
      INTO v_want
      FROM (SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b) s
      JOIN pg_catalog.pg_namespace n ON true
      JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
     WHERE n.nspname || '.' || c.relname = s.source
       AND c.relkind IN ('r', 'p')
       AND NOT ops_case.is_denied_source(s.source);

    -- 2・3. 今付いている表（PUBLIC への付与は数えない）のうち、付けるべきでない表だけ REVOKE
    FOR t IN
        SELECT DISTINCT c.oid AS oid, n.nspname::text AS sch, c.relname::text AS rel
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         CROSS JOIN LATERAL pg_catalog.aclexplode(c.relacl) a
         WHERE c.relkind IN ('r', 'p')
           AND (n.nspname = 'public' OR n.nspname LIKE 'tenant\_%')
           AND a.grantee = v_owner AND a.privilege_type = 'SELECT'
           AND NOT (c.oid = ANY (v_want))
    LOOP
        EXECUTE pg_catalog.format('REVOKE SELECT ON TABLE %I.%I FROM ai_unmask_owner', t.sch, t.rel);
        v_changed := v_changed + 1;
    END LOOP;

    -- 付けるべき表のうち、まだ付いていない表だけ GRANT
    FOR t IN
        SELECT c.oid AS oid, n.nspname::text AS sch, c.relname::text AS rel
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE c.oid = ANY (v_want)
           AND NOT EXISTS (
               SELECT 1 FROM pg_catalog.aclexplode(c.relacl) a
                WHERE a.grantee = v_owner AND a.privilege_type = 'SELECT'
           )
    LOOP
        EXECUTE pg_catalog.format('GRANT SELECT ON TABLE %I.%I TO ai_unmask_owner', t.sch, t.rel);
        v_changed := v_changed + 1;
    END LOOP;

    -- 付けるべき表のスキーマの USAGE（無いときだけ）
    FOR t IN
        SELECT DISTINCT n.nspname::text AS sch
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE c.oid = ANY (v_want)
           AND NOT pg_catalog.has_schema_privilege(v_owner, n.oid, 'USAGE')
    LOOP
        EXECUTE pg_catalog.format('GRANT USAGE ON SCHEMA %I TO ai_unmask_owner', t.sch);
    END LOOP;

    -- 4. 関数の中で使う部品への権限（無いときだけ）
    IF NOT pg_catalog.has_schema_privilege(v_owner, 'ai_cloud_meta', 'USAGE') THEN
        GRANT USAGE ON SCHEMA ai_cloud_meta TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_table_privilege(v_owner, 'ai_cloud_meta.build_columns', 'SELECT') THEN
        GRANT SELECT ON ai_cloud_meta.build_columns TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_schema_privilege(v_owner, 'ops_case', 'USAGE') THEN
        GRANT USAGE ON SCHEMA ops_case TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_table_privilege(v_owner, 'ops_case.deny_tables', 'SELECT') THEN
        GRANT SELECT ON ops_case.deny_tables TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_table_privilege(v_owner, 'ops_case.cases', 'SELECT') THEN
        GRANT SELECT ON ops_case.cases TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_table_privilege(v_owner, 'ops_case.unmask_requests', 'SELECT') THEN
        GRANT SELECT ON ops_case.unmask_requests TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_column_privilege(v_owner, 'ops_case.unmask_requests', 'read_count', 'UPDATE') THEN
        GRANT UPDATE (read_count) ON ops_case.unmask_requests TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_table_privilege(v_owner, 'ops_case.unmask_reads', 'INSERT') THEN
        GRANT INSERT ON ops_case.unmask_reads TO ai_unmask_owner;
    END IF;
    IF NOT pg_catalog.has_sequence_privilege(v_owner, 'ops_case.unmask_reads_id_seq', 'USAGE') THEN
        GRANT USAGE ON SEQUENCE ops_case.unmask_reads_id_seq TO ai_unmask_owner;
    END IF;

    RETURN v_changed;
END
$fn$;

-- 5. 関数の持ち主と実行権限
ALTER FUNCTION ops_case.unmask_fetch(uuid, text) OWNER TO ai_unmask_owner;

REVOKE ALL ON FUNCTION ops_case.is_denied_source(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops_case.unmask_fetch(uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops_case.grant_unmask_owner() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION ops_case.is_denied_source(text) TO ai_unmask_owner;
GRANT EXECUTE ON FUNCTION ops_case.unmask_fetch(uuid, text) TO ai_unmask;
-- ai_unmask には ops_case の USAGE と unmask_fetch の EXECUTE だけ（表には何も付けない）
GRANT USAGE ON SCHEMA ops_case TO ai_unmask;

-- 6. backend（salesanchor_app）の権限。DELETE・TRUNCATE は付けない
DO $app$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT USAGE ON SCHEMA ops_case TO salesanchor_app;
        GRANT SELECT, INSERT, UPDATE ON ops_case.cases TO salesanchor_app;
        GRANT SELECT, INSERT ON ops_case.reports TO salesanchor_app;
        GRANT SELECT, INSERT ON ops_case.unmask_requests TO salesanchor_app;
        GRANT UPDATE (status, decided_by, decision_reason, approved_minutes, expires_at)
            ON ops_case.unmask_requests TO salesanchor_app;
        GRANT SELECT ON ops_case.unmask_reads TO salesanchor_app;
        GRANT SELECT, INSERT ON ops_case.audits TO salesanchor_app;
        GRANT USAGE ON SEQUENCE ops_case.audits_id_seq TO salesanchor_app;
        GRANT SELECT ON ops_case.deny_tables TO salesanchor_app;
        REVOKE DELETE, TRUNCATE ON ALL TABLES IN SCHEMA ops_case FROM salesanchor_app;
        -- 申請の受付で列を確かめる（中身は名前だけで値は無い）
        GRANT USAGE ON SCHEMA ai_cloud_meta TO salesanchor_app;
        GRANT SELECT ON ai_cloud_meta.build_columns TO salesanchor_app;
        -- 【要確認】カード §4-A に無い追加: GET /ops/case/audit-inputs が build_log の件数を読むため（件数と失敗の種類だけで値は無い）
        GRANT SELECT ON ai_cloud_meta.build_log TO salesanchor_app;
        GRANT EXECUTE ON FUNCTION ops_case.is_denied_source(text) TO salesanchor_app;
    ELSE
        RAISE NOTICE 'salesanchor_app が無いため backend の権限は付けない';
    END IF;
END
$app$;

-- 初回のデプロイでも効くように 1 回呼ぶ（build_columns は前のデプロイのまま残っている前提。
-- 毎回のデプロイでは run_all_migrations.sh の最後の trap が付け直す）
SELECT ops_case.grant_unmask_owner();
