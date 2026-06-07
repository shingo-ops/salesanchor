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

# [6] Fail-close (app.is_operator='' → INSERT with NULL tenant_id must fail)
# Use -c instead of heredoc: docker exec without -i doesn't pass heredoc stdin.
# ON_ERROR_STOP=1: psql exits non-zero on SQL error (locale-independent).
FAILCLOSE_OK=false
docker exec -e PGPASSWORD="${APP_PASS}" "${POSTGRES}" \
  psql -U salesanchor_app -d jarvis_db -v ON_ERROR_STOP=1 \
  -c "BEGIN; SET LOCAL app.tenant_id = '1'; SET LOCAL app.is_operator = ''; INSERT INTO public.translation_glossary (tenant_id, source_term) VALUES (NULL, '__smoke_failclose__'); ROLLBACK;" \
  > /dev/null 2>&1 \
  || FAILCLOSE_OK=true
[ "${FAILCLOSE_OK}" = "true" ] \
  && echo "[6] PASS: fail-close OK" \
  || { echo "[6] FAIL: fail-close not working (INSERT should have been rejected)"; exit 1; }

# [7] アプリ接続ユーザー確認（SA18_PHASE2_ENABLED フラグで Phase2 意図を判定）
# まずヘルスチェックでプールを暖機（接続 0 のまま確認すると偽陽性になる）
docker exec -e PGPASSWORD="${APP_PASS}" "${BACKEND}" \
  python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
  || { echo "[7] FAIL: backend health check failed (app is down)"; exit 1; }
sleep 2  # pool warmup

# SA18_PHASE2_ENABLED=1 が .env に在るかどうかで Phase2 意図を判定する。
# DATABASE_URL を直接見ない理由: Step 2b が URL を黙って revert する可能性があるため
# "フラグが立っているのに jarvis モード" という偽 green を検出できなくなる。
if grep -q '^SA18_PHASE2_ENABLED=1' .env 2>/dev/null; then
  # Phase2 意図フラグが立っている: DATABASE_URL も salesanchor_app であるべき
  if ! grep -q '^DATABASE_URL=.*salesanchor_app' .env 2>/dev/null; then
    echo "[7] FAIL: SA18_PHASE2_ENABLED=1 だが DATABASE_URL が salesanchor_app でない — Phase2 切替が完了していない"
    exit 1
  fi
  # salesanchor_app 接続が在ることを確認（在る側）
  APP_CONNS=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
    SELECT count(*) FROM pg_stat_activity
    WHERE application_name = 'salesanchor_backend'
      AND usename = 'salesanchor_app';" | tr -d ' \n')
  [ "${APP_CONNS}" -gt 0 ] \
    && echo "[7a] PASS: salesanchor_app connections active (${APP_CONNS}件)" \
    || { echo "[7a] FAIL: salesanchor_app connections = 0 (app not using salesanchor_app)"; exit 1; }
  # jarvis 接続が無いことを確認（無い側）
  JARVIS_APP_CONNS=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
    SELECT count(*) FROM pg_stat_activity
    WHERE application_name = 'salesanchor_backend'
      AND usename = 'jarvis';" | tr -d ' \n')
  [ "${JARVIS_APP_CONNS}" = "0" ] \
    && echo "[7b] PASS: no jarvis connections with salesanchor_backend app name" \
    || { echo "[7b] FAIL: ${JARVIS_APP_CONNS} jarvis connections found -> DATABASE_URL not switched"; exit 1; }
else
  echo "[7] INFO: SA18_PHASE2_ENABLED 未設定 — jarvis モード（Phase2 切替前）— アプリ接続確認はスキップ"
fi

echo ""
echo "============================================"
echo "All SA-19 smoke tests passed"
echo "============================================"
