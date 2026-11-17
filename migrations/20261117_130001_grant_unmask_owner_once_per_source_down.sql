-- ADR-1052 段2 の手直しの戻し（手動実行のみ・本番デプロイでは実行しない）。関数を 20261031_210000_create_ops_case.sql の元の形へ戻す。
-- 戻すと本番反映の最後の付け直しがまた約 16 秒以上かかる（設計 docs/handoff/cloud-case-ai/grant-speed-design.md §2）。
BEGIN;
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
COMMIT;
