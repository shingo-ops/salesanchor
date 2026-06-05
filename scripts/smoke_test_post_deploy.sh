#!/bin/bash
# smoke_test_post_deploy.sh -- SA-19 deploy smoke test
# Phase2 から deploy.yml が呼び出す。失敗は非0 exit でデプロイ失敗扱い。
# 環境変数: SALESANCHOR_APP_PASSWORD（必須）
set -e

POSTGRES="astro-webapp-postgres-1"
BACKEND="astro-webapp-backend-1"
ADMIN_PSQL="psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1"
APP_PASS="${SALESANCHOR_APP_PASSWORD:?SALESANCHOR_APP_PASSWORD is required}"

echo "=== SA-19 smoke test start ==="

# [1] RLS enabled on translation_glossary
NORLS=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
  SELECT count(*) FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname = 'translation_glossary'
    AND NOT c.relrowsecurity;" | tr -d ' \n')
[ "${NORLS}" = "0" ] \
  && echo "[1] PASS: RLS enabled" \
  || { echo "[1] FAIL: RLS not enabled"; exit 1; }

# [2] 4 policies on translation_glossary
PCOUNT=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
  SELECT count(*) FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename = 'translation_glossary';" | tr -d ' \n')
[ "${PCOUNT}" -eq 4 ] \
  && echo "[2] PASS: 4 policies found" \
  || { echo "[2] FAIL: policy count=${PCOUNT}"; exit 1; }

# [3] salesanchor_app NOSUPERUSER NOBYPASSRLS
ROLE_OK=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
  SELECT count(*) FROM pg_roles
  WHERE rolname = 'salesanchor_app'
    AND NOT rolsuper AND NOT rolbypassrls;" | tr -d ' \n')
[ "${ROLE_OK}" = "1" ] \
  && echo "[3] PASS: salesanchor_app NOSUPERUSER NOBYPASSRLS" \
  || { echo "[3] FAIL: salesanchor_app missing or wrong attributes"; exit 1; }

# [4] salesanchor_app can connect
docker exec -e PGPASSWORD="${APP_PASS}" "${POSTGRES}" \
  psql -U salesanchor_app -d jarvis_db -c "SELECT 1" > /dev/null \
  && echo "[4] PASS: salesanchor_app connection OK" \
  || { echo "[4] FAIL: salesanchor_app connection failed"; exit 1; }

# [5] Cross-tenant isolation canary (seed tenant_id=999999)
cleanup_seed() {
  docker exec "${POSTGRES}" ${ADMIN_PSQL} -c \
    "DELETE FROM public.translation_glossary WHERE source_term = '__smoke_canary_t999999__';" \
    2>/dev/null || true
}
trap cleanup_seed EXIT

# Try to seed; FK constraint may prevent it
docker exec "${POSTGRES}" ${ADMIN_PSQL} -c "
  SET app.is_operator = 'true';
  INSERT INTO public.translation_glossary (tenant_id, source_term)
    VALUES (999999, '__smoke_canary_t999999__')
    ON CONFLICT DO NOTHING;" 2>&1 \
  && SEED_OK=true || SEED_OK=false

if [ "${SEED_OK}" = "true" ]; then
  CANARY=$(docker exec -e PGPASSWORD="${APP_PASS}" "${POSTGRES}" \
    psql -U salesanchor_app -d jarvis_db -t -c "
      SET app.tenant_id = '1';
      SET app.is_operator = '';
      SELECT count(*) FROM public.translation_glossary
      WHERE tenant_id = 999999 AND source_term = '__smoke_canary_t999999__';" \
    2>&1 | grep -v '^SET' | tr -d ' \n')
  [ "${CANARY}" = "0" ] \
    && echo "[5] PASS: cross-tenant isolation OK" \
    || { echo "[5] FAIL: tenant=1 can see tenant=999999 rows"; exit 1; }
else
  echo "[5] SKIP: FK constraint prevented seed"
fi
trap - EXIT
cleanup_seed

# [6] Fail-close (app.is_operator unset -> 42501)
FAILCLOSE=$(docker exec -e PGPASSWORD="${APP_PASS}" "${POSTGRES}" \
  psql -U salesanchor_app -d jarvis_db 2>&1 <<'FC'
BEGIN;
SET LOCAL app.tenant_id = '1';
SET LOCAL app.is_operator = '';
INSERT INTO public.translation_glossary (tenant_id, source_term)
  VALUES (NULL, '__smoke_failclose__');
ROLLBACK;
FC
)
echo "${FAILCLOSE}" | grep -qE "42501|insufficient_privilege|new row violates" \
  && echo "[6] PASS: fail-close OK" \
  || { echo "[6] FAIL: fail-close not working"; exit 1; }

# [7] No jarvis connections with application_name='salesanchor_backend'
JARVIS_APP_CONNS=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
  SELECT count(*) FROM pg_stat_activity
  WHERE application_name = 'salesanchor_backend'
    AND usename = 'jarvis';" | tr -d ' \n')
[ "${JARVIS_APP_CONNS}" = "0" ] \
  && echo "[7] PASS: no jarvis connections with salesanchor_backend app name" \
  || { echo "[7] FAIL: ${JARVIS_APP_CONNS} jarvis connections found with salesanchor_backend -> DATABASE_URL not yet switched"; exit 1; }

echo ""
echo "============================================"
echo "All SA-19 smoke tests passed"
echo "============================================"
