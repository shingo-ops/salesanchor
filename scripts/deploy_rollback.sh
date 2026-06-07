#!/bin/bash
# deploy_rollback.sh — 健康ゲート・失敗理由の保全・自動ロールバック（ADR-116）
#
# 本番 deploy.yml の Finalize ステップとドリル runner の両方から呼ばれる共有ロジック。
# 「ドリルで通った＝本番でも同じ動き」を保証するため、ロジックをここに一本化する。
#
# 動作:
#   - ヘルスチェック通過 → last-good SHA を記録して exit 0
#   - ヘルスチェック失敗 → 保全 → LAST_GOOD_SHA へ自動ロールバック → 復旧確認 → exit 1
#
# 設定（環境変数でオーバーライド可・すべて省略可・本番はデフォルト値を使用）:
#   BACKEND_CONTAINER    backend コンテナ名        (default: astro-webapp-backend-1)
#   DB_CONTAINER         postgres コンテナ名        (default: astro-webapp-postgres-1)
#   ROLLBACK_WEBHOOK_URL Discord webhook URL        (default: .env の ADMIN_NOTIFICATION_DISCORD_WEBHOOK)
#   LAST_GOOD_SHA_FILE   last-good SHA ファイルパス (default: .deploy_last_good_sha)
#   PREV_ENV_FILE        .env バックアップパス       (default: .deploy_prev_env)
#   DEPLOY_FAILURES_DIR  保全ログ出力先ディレクトリ  (default: deploy-failures)
#   COMPOSE_CMD          docker compose コマンド    (default: docker compose)
#   ROLLBACK_BUILD_RETRIES ビルドリトライ回数        (default: 3)
#
# 使用例:
#   # 本番（deploy.yml Finalize より）
#   ROLLBACK_WEBHOOK_URL="$(grep '^ADMIN_NOTIFICATION_DISCORD_WEBHOOK=' .env | cut -d= -f2-)" \
#     bash scripts/deploy_rollback.sh
#
#   # ドリル（run-drill.sh より）
#   BACKEND_CONTAINER=salesanchor-drill-backend-1 \
#   DB_CONTAINER=salesanchor-drill-postgres-1 \
#   COMPOSE_CMD="docker compose -f docker-compose.drill.yml -p drill" \
#     bash scripts/deploy_rollback.sh

set -euo pipefail

# ── 設定 ──────────────────────────────────────────────────────────────────────
BACKEND_CONTAINER="${BACKEND_CONTAINER:-astro-webapp-backend-1}"
DB_CONTAINER="${DB_CONTAINER:-astro-webapp-postgres-1}"
LAST_GOOD_SHA_FILE="${LAST_GOOD_SHA_FILE:-.deploy_last_good_sha}"
PREV_ENV_FILE="${PREV_ENV_FILE:-.deploy_prev_env}"
DEPLOY_FAILURES_DIR="${DEPLOY_FAILURES_DIR:-deploy-failures}"
COMPOSE_CMD="${COMPOSE_CMD:-docker compose}"
ROLLBACK_BUILD_RETRIES="${ROLLBACK_BUILD_RETRIES:-3}"

# Discord webhook: 環境変数 → .env フォールバック
if [ -z "${ROLLBACK_WEBHOOK_URL:-}" ]; then
  ROLLBACK_WEBHOOK_URL="$(grep '^ADMIN_NOTIFICATION_DISCORD_WEBHOOK=' .env 2>/dev/null | cut -d= -f2- || true)"
fi

# ── ヘルパー関数 ──────────────────────────────────────────────────────────────
_notify_discord() {
  local msg="$1"
  if [ -n "${ROLLBACK_WEBHOOK_URL:-}" ]; then
    curl -s -X POST "${ROLLBACK_WEBHOOK_URL}" \
      -H "Content-Type: application/json" \
      -d "{\"content\":\"${msg}\",\"username\":\"Deploy Bot\"}" \
      || true
  fi
}

_run_health_check() {
  docker exec "${BACKEND_CONTAINER}" \
    python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
    2>/dev/null
}

# ── ヘルスチェック実行 ─────────────────────────────────────────────────────────
set +e
_run_health_check
_health_exit=$?
set -e

# ── ヘルスチェック通過 → last-good SHA を記録して終了 ──────────────────────────
if [ "${_health_exit}" -eq 0 ]; then
  echo "✅ Health check passed"
  git rev-parse HEAD > "${LAST_GOOD_SHA_FILE}"
  echo "  last-good SHA 記録: $(head -c 7 "${LAST_GOOD_SHA_FILE}")"
  exit 0
fi

# ── ヘルスチェック失敗 ─────────────────────────────────────────────────────────
echo "❌ Health check failed — starting failure preservation + auto-rollback..."

_bad_sha=$(git rev-parse HEAD 2>/dev/null | head -c 7 || echo "unknown")
_good_sha=$(cat "${LAST_GOOD_SHA_FILE}" 2>/dev/null || cat .deploy_prev_sha 2>/dev/null || echo "")
_rollback_result="failed"

# ── 失敗理由の保全（ロールバック前・非交渉）──────────────────────────────────
mkdir -p "${DEPLOY_FAILURES_DIR}"
_fail_ts=$(date -u '+%Y%m%dT%H%M%S')
_fail_log="${DEPLOY_FAILURES_DIR}/${_fail_ts}-${_bad_sha}.log"

{
  echo "=== DEPLOY FAILURE REPORT: ${_fail_ts} ==="
  echo "BAD_SHA:  ${_bad_sha}"
  echo "GOOD_SHA: ${_good_sha:-NONE}"
  echo ""
  echo "--- /api/health response ---"
  # HTTPError(503) も含めてレスポンス本文を取得（stderr に exception が出るため 2>&1）
  docker exec "${BACKEND_CONTAINER}" python3 -c \
    "import urllib.request,urllib.error; \
exec(\"try:\\n r=urllib.request.urlopen('http://localhost:8000/api/health')\\n print('STATUS:',r.status)\\nexcept urllib.error.HTTPError as e: print('STATUS:',e.code,'BODY:',e.read(200).decode('utf-8','replace'))\\nexcept Exception as e: print('ERROR:',e)\")" \
    2>&1 || echo "(health endpoint unreachable)"
  echo ""
  echo "--- docker compose ps ---"
  ${COMPOSE_CMD} ps 2>/dev/null || echo "(docker compose ps 失敗)"
  echo ""
  echo "--- backend logs (last 200 lines) ---"
  docker logs "${BACKEND_CONTAINER}" --tail 200 2>&1 || echo "(backend ログ取得失敗)"
  echo ""
  echo "--- DB connection diagnosis (pg_stat_activity) ---"
  docker exec "${DB_CONTAINER}" \
    psql -U "${POSTGRES_USER:-jarvis}" -d "${POSTGRES_DB:-jarvis_db}" -t -c \
    "SELECT usename, application_name, client_addr, state FROM pg_stat_activity WHERE application_name NOT IN ('psql','') ORDER BY usename;" \
    2>/dev/null || echo "(pg_stat_activity 取得失敗)"
} > "${_fail_log}" 2>&1
echo "  保全ファイル: ${_fail_log}"

# ── last-good SHA がない場合は明示失敗（初回デプロイ）────────────────────────
if [ -z "${_good_sha}" ]; then
  _notify_discord \
    "🚨 **デプロイ失敗・ロールバック先不明** 🚨\\nBAD: \`${_bad_sha}\`\\n初回デプロイのため last-good SHA がありません。手動対応が必要です。\\n保全: \`${_fail_log}\`"
  echo "❌ ロールバック先不明（初回デプロイ）— 手動対応が必要"
  exit 1
fi

# ── 自動ロールバック ───────────────────────────────────────────────────────────
echo "→ Rolling back to ${_good_sha:0:7}..."
git reset --hard "${_good_sha}"

# .env を ロールバック前の状態に復元（DATABASE_URL 等を元の値へ）
if [ -f "${PREV_ENV_FILE}" ] && [ -s "${PREV_ENV_FILE}" ]; then
  cp "${PREV_ENV_FILE}" .env
  echo "  .env を ${PREV_ENV_FILE} から復元しました"
fi

# 旧コードでビルド（最大 N 回リトライ）
_rb_build=false
for _attempt in $(seq 1 "${ROLLBACK_BUILD_RETRIES}"); do
  if ${COMPOSE_CMD} build 2>&1; then
    _rb_build=true
    break
  fi
  echo "Rollback build attempt ${_attempt} failed. 15秒後にリトライ..."
  sleep 15
done

if [ "${_rb_build}" = "true" ]; then
  # コンテナ差し替え
  for _svc in backend frontend celery-worker celery-beat discord-gateway; do
    docker ps -a --filter "name=${BACKEND_CONTAINER%%-*}-${_svc}" --format "{{.ID}}" \
      | xargs -r docker rm -f 2>/dev/null || true
  done
  ${COMPOSE_CMD} up -d --remove-orphans

  # 復旧確認（最大 60s ポーリング）
  echo "Waiting for rollback to stabilize (max 60s)..."
  for _i in $(seq 1 12); do
    sleep 5
    if _run_health_check; then
      _rollback_result="success"
      break
    fi
    echo "  ...waiting (${_i}/12)..."
  done
fi

# Discord 通知
if [ "${_rollback_result}" = "success" ]; then
  _notify_discord \
    "⚠️ **デプロイ失敗→自動ロールバック成功**\\nBAD: \`${_bad_sha}\`  GOOD: \`${_good_sha:0:7}\`\\n本番は UP。手動確認をお願いします。\\n保全: \`${_fail_log}\`"
  echo "✅ 自動ロールバック成功: ${_good_sha:0:7} に復帰（deploy job は失敗扱い）"
else
  _notify_discord \
    "🚨 **自動ロールバック失敗・手動対応要** 🚨\\nデプロイも復帰も失敗しました。本番が DOWN の可能性があります。即時確認をお願いします。\\n保全: \`${_fail_log}\`"
  echo "❌ 自動ロールバック失敗 — 手動対応が必要"
fi

# ロールバック成功・失敗どちらも非0 exit（本番の問題を可視化）
exit 1
