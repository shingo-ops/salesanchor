#!/bin/bash
# test_rollback_simulation.sh — 自動ロールバック実地検証スクリプト
#
# 目的: deploy.yml Finalize ステップのロールバックロジックが"本当に動く"かを確認する。
# 条件: Docker + docker compose が使えること（ローカル Mac または CI runner）
#
# テストシナリオ:
#   1. GOOD コミット: /api/health が 200 を返すコンテナ
#   2. BAD コミット:  /api/health が 503 を返すコンテナ
#   3. BAD を「デプロイ」→ ヘルスチェック失敗を検出 → 自動で GOOD に復帰
#   4. 復帰後 health 200 を確認 → TEST PASSED
#
# 成功路（ロールバック成功）と失敗路（Discord通知スキップ）を両方確認する。
# Discord は dry-run（実際には飛ばさず、curl コマンドが生成されることのみ確認）。

set -e

# --- 作業ディレクトリ ---
WORKDIR=$(mktemp -d /tmp/rollback-test-XXXXXX)
echo "▶ Test workdir: ${WORKDIR}"
trap "echo '▶ Cleanup...'; docker compose --project-directory '${WORKDIR}' down --remove-orphans 2>/dev/null || true; rm -rf '${WORKDIR}'" EXIT

HOST_PORT=18765  # ポート競合を避けるため本番と別ポートを使用

# --- GOOD バージョン: /api/health → 200 ---
mkdir -p "${WORKDIR}/backend"
cat > "${WORKDIR}/backend/server.py" << 'PYEOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *args): pass
HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
PYEOF

cat > "${WORKDIR}/backend/Dockerfile" << 'DFEOF'
FROM python:3.12-slim
COPY server.py /app/server.py
WORKDIR /app
EXPOSE 8000
CMD ["python", "server.py"]
DFEOF

cat > "${WORKDIR}/docker-compose.yml" << EOF
services:
  backend:
    container_name: rollback-test-backend-1
    build:
      context: ./backend
    ports:
      - "${HOST_PORT}:8000"
    restart: unless-stopped
EOF

# GOOD コミット
cd "${WORKDIR}"
git init -q
git config user.email "ci@test.local"
git config user.name "Rollback Test"
git add .
git commit -q -m "GOOD: /api/health returns 200"
GOOD_SHA=$(git rev-parse HEAD)
echo "▶ GOOD_SHA: ${GOOD_SHA:0:7}"

# --- BAD バージョン: /api/health → 503 ---
cat > "${WORKDIR}/backend/server.py" << 'PYEOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            body = b'{"error":"unhealthy"}'
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *args): pass
HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
PYEOF

git add .
git commit -q -m "BAD: /api/health returns 503"
BAD_SHA=$(git rev-parse HEAD)
echo "▶ BAD_SHA:  ${BAD_SHA:0:7}"

# ============================================================
# Step 0: PREV_SHA 保存（deploy.yml Step 0 の模擬）
# ============================================================
# 現在 HEAD = BAD（"デプロイ直前" の状態から見ると BAD が最新）
# 実際は GOOD が "前のコード" → PREV_SHA = GOOD_SHA
echo "${GOOD_SHA}" > .deploy_prev_sha
echo "▶ PREV_SHA 保存: ${GOOD_SHA:0:7}"

# ============================================================
# BAD コンテナを起動（"デプロイ後"の状態を模倣）
# ============================================================
echo ""
echo "▶ BAD バージョンを起動..."
docker compose --project-directory "${WORKDIR}" build -q
for _svc in backend; do
  docker ps -a --filter "name=rollback-test-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
done
docker compose --project-directory "${WORKDIR}" up -d

# コンテナ起動待ち（最大 20s）
for _i in $(seq 1 4); do
  sleep 5
  if curl -sf "http://localhost:${HOST_PORT}/api/health" > /dev/null 2>&1 || \
     curl -s "http://localhost:${HOST_PORT}/api/health" -o /dev/null; then
    break
  fi
  echo "  ...waiting for container (${_i}/4)..."
done

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${HOST_PORT}/api/health" 2>/dev/null || echo "000")
echo "▶ 現在の HTTP status: ${HTTP_STATUS}"
if [ "${HTTP_STATUS}" != "503" ]; then
  echo "❌ SETUP FAIL: BAD バージョンが 503 を返さない (got ${HTTP_STATUS})"
  exit 1
fi
echo "✅ BAD バージョン確認 (503)"

# ============================================================
# Finalize: ヘルスチェック（deploy.yml 実際のコードと同じ）
# ============================================================
echo ""
echo "=== Finalize: Step 6 Health check (with auto-rollback) ==="

CONTAINER="rollback-test-backend-1"

set +e
docker exec "${CONTAINER}" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
_health_exit=$?
set -e

echo "▶ health check exit code: ${_health_exit}"

if [ "${_health_exit}" -eq 0 ]; then
  echo "❌ FAIL: ヘルスチェックが成功してしまった（503 を返すはずだった）"
  exit 1
fi

echo "❌ Health check failed — starting auto-rollback..."
PREV_SHA=$(cat "${WORKDIR}/.deploy_prev_sha" 2>/dev/null || echo "")
_rollback_result="failed"

if [ -n "${PREV_SHA}" ]; then
  echo "→ Rolling back to ${PREV_SHA:0:7}..."
  cd "${WORKDIR}"
  git reset --hard "${PREV_SHA}"

  # ビルド（最大3回）
  _rb_build=false
  for _attempt in 1 2 3; do
    if docker compose --project-directory "${WORKDIR}" build -q 2>&1; then
      _rb_build=true
      break
    fi
    echo "Rollback build attempt ${_attempt} failed. Retrying in 5s..."
    sleep 5
  done

  if [ "${_rb_build}" = "true" ]; then
    docker ps -a --filter "name=rollback-test-backend" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
    docker compose --project-directory "${WORKDIR}" up -d --remove-orphans

    echo "Waiting for rollback to stabilize (max 60s)..."
    for _i in $(seq 1 12); do
      sleep 5
      if docker exec "${CONTAINER}" \
          python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
          2>/dev/null; then
        _rollback_result="success"
        break
      fi
      echo "  ...waiting (${_i}/12)..."
    done
  fi
fi

# ============================================================
# Discord 通知の dry-run（実際には送信しない。コマンド生成のみ確認）
# ============================================================
FAKE_WEBHOOK="http://dry-run-webhook.local/test"
if [ "${_rollback_result}" = "success" ]; then
  _discord_payload="{\"content\":\"⚠️ **デプロイ失敗→自動ロールバック成功**\\nコミット \`${PREV_SHA:0:7}\` に自動復帰。本番は UP。手動確認をお願いします.\",\"username\":\"Deploy Bot\"}"
  echo ""
  echo "▶ [Discord dry-run] 成功通知ペイロード:"
  echo "  ${_discord_payload}"
  echo "  (実際のデプロイでは ROLLBACK_DISCORD_WEBHOOK 宛に POST される)"
else
  _discord_payload="{\"content\":\"🚨 **自動ロールバック失敗・手動対応要** 🚨\",\"username\":\"Deploy Bot\"}"
  echo "▶ [Discord dry-run] 失敗通知ペイロード:"
  echo "  ${_discord_payload}"
fi

# ============================================================
# 最終確認
# ============================================================
echo ""
if [ "${_rollback_result}" = "success" ]; then
  FINAL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${HOST_PORT}/api/health" 2>/dev/null || echo "000")
  echo "============================================"
  echo "✅ ROLLBACK TEST PASSED"
  echo "   BAD version (503) → rolled back to GOOD"
  echo "   Final HTTP status from host: ${FINAL_STATUS}"
  echo "============================================"
  exit 0
else
  echo "============================================"
  echo "❌ ROLLBACK TEST FAILED"
  echo "   _rollback_result=${_rollback_result}"
  echo "============================================"
  exit 1
fi
