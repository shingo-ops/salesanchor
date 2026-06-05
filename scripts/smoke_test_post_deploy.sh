#!/bin/bash
# smoke_test_post_deploy.sh — SA-19 デプロイ後スモークテスト
# Phase2 から deploy.yml が呼び出す。失敗は非0 exit でデプロイ失敗扱い。
# 環境変数: SALESANCHOR_APP_PASSWORD（必須）
set -e

POSTGRES="astro-webapp-postgres-1"
BACKEND="astro-webapp-backend-1"
ADMIN_PSQL="psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1"
APP_PASS="${SALESANCHOR_APP_PASSWORD:?SALESANCHOR_APP_PASSWORD is required}"

echo "=== SA-19 スモークテスト開始 ==="

# [1] RLS 有効確認（public.translation_glossary）
NORLS=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
  SELECT count(*) FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname = 'translation_glossary'
    AND NOT c.relrowsecurity;" | tr -d ' \n')
[ "${NORLS}" = "0" ] \
  && echo "✅ [1] RLS 有効" \
  || (echo "❌ [1] RLS 無効" && exit 1)

# [2] ポリシー4本確認（public スキーマ限定）
PCOUNT=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
  SELECT count(*) FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename = 'translation_glossary';" | tr -d ' \n')
[ "${PCOUNT}" -eq 4 ] \
  && echo "✅ [2] ポリシー4本" \
  || (echo "❌ [2] ポリシー数=${PCOUNT}" && exit 1)

# [3] salesanchor_app: NOSUPERUSER NOBYPASSRLS
ROLE_OK=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
  SELECT count(*) FROM pg_roles
  WHERE rolname = 'salesanchor_app'
    AND NOT rolsuper AND NOT rolbypassrls;" | tr -d ' \n')
[ "${ROLE_OK}" = "1" ] \
  && echo "✅ [3] salesanchor_app NOSUPERUSER NOBYPASSRLS" \
  || (echo "❌ [3] salesanchor_app 未作成 or 属性不正" && exit 1)

# [4] salesanchor_app 実接続
docker exec -e PGPASSWORD="${APP_PASS}" "${POSTGRES}" \
  psql -U salesanchor_app -d jarvis_db -c "SELECT 1" > /dev/null \
  && echo "✅ [4] salesanchor_app 接続成立" \
  || (echo "❌ [4] salesanchor_app 接続失敗（パスワード未設定 or 誤り）" && exit 1)

# [5] クロステナント遮断カナリア
# trap で必ず種行を削除（set -e で中断しても残さない）
cleanup_seed() {
  docker exec "${POSTGRES}" ${ADMIN_PSQL} -c \
    "DELETE FROM public.translation_glossary WHERE source_term = '__smoke_canary_t2__';" \
    2>/dev/null || true
}
trap cleanup_seed EXIT

docker exec "${POSTGRES}" ${ADMIN_PSQL} <<'SEED'
SET app.is_operator = 'true';
INSERT INTO public.translation_glossary (tenant_id, source_term)
  VALUES (2, '__smoke_canary_t2__')
  ON CONFLICT DO NOTHING;
SEED

CANARY=$(docker exec -e PGPASSWORD="${APP_PASS}" "${POSTGRES}" \
  psql -U salesanchor_app -d jarvis_db -t -c "
    SET app.tenant_id = '1';
    SET app.is_operator = '';
    SELECT count(*) FROM public.translation_glossary
    WHERE tenant_id = 2 AND source_term = '__smoke_canary_t2__';" \
  2>&1 | tr -d ' \n')
[ "${CANARY}" = "0" ] \
  && echo "✅ [5] クロステナント遮断 OK" \
  || (echo "❌ [5] クロステナント遮断 FAIL: tenant=1 が tenant=2 行を見た" && exit 1)

trap - EXIT
cleanup_seed

# [6] フェイルクローズ（is_operator 未設定 → 42501）
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
  && echo "✅ [6] フェイルクローズ OK" \
  || (echo "❌ [6] フェイルクローズ FAIL" && exit 1)

# [7] アプリ実接続ユーザ確認
# backend コンテナの IP でフィルタし、jarvis(superuser) 接続が0件であることを確認
# （Phase2 以降: application_name='salesanchor_backend' に絞って精緻化予定）
BACKEND_IP=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
  "${BACKEND}" 2>/dev/null || echo "")
if [ -n "${BACKEND_IP}" ]; then
  JARVIS_CONNS=$(docker exec "${POSTGRES}" ${ADMIN_PSQL} -t -c "
    SELECT count(*) FROM pg_stat_activity
    WHERE client_addr = '${BACKEND_IP}'::inet
      AND usename = 'jarvis';" | tr -d ' \n')
  [ "${JARVIS_CONNS}" = "0" ] \
    && echo "✅ [7] アプリは jarvis(superuser) で接続していない" \
    || (echo "❌ [7] app backend から jarvis 接続が ${JARVIS_CONNS} 本検出 → DATABASE_URL 切替未完了" && exit 1)
else
  echo "⚠️  [7] backend IP 取得失敗 → スキップ（Phase2 で再確認）"
fi

echo ""
echo "============================================"
echo "✅ 全スモークテスト通過（SA-19）"
echo "============================================"
