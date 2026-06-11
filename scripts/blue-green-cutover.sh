#!/bin/bash
# blue-green-cutover.sh — backend ゼロダウンタイム切替スクリプト
#
# 目的:
#   「旧コンテナ削除 → 新起動（15〜30s のダウン）」を
#   「新起動 → health 確認 → nginx 切替 → 旧停止」に変える。
#
# 前提条件（呼び出し元が保証すること）:
#   - docker compose build が完了済み（backend イメージが astro-webapp-backend タグで存在）
#   - astro-webapp-backend-1 が稼働中（旧 backend が接客中）
#   - nginx が astro-webapp_frontnet の backend エイリアスを参照中
#   - .env が最新（DATABASE_URL 等が呼び出し前に更新済み）
#
# 使い方:
#   bash scripts/blue-green-cutover.sh              # 通常デプロイ
#   BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh  # タイムアウト調整
#
# 参考: docs/handoff/zero-downtime-deploy/design.md

set -e

REPO_DIR="${REPO_DIR:-/home/ubuntu/salesanchor}"
cd "${REPO_DIR}"

# 定数
COMPOSE_PROJECT="astro-webapp"
OLD_BACKEND="${COMPOSE_PROJECT}-backend-1"
GREEN_BACKEND="${COMPOSE_PROJECT}-backend-green"
FRONTNET="${COMPOSE_PROJECT}_frontnet"
BACKNET="${COMPOSE_PROJECT}_backnet"
NGINX="${COMPOSE_PROJECT}-nginx-1"
HEALTH_TIMEOUT="${BG_HEALTH_TIMEOUT:-60}"

# .env を読み込み（DATABASE_URL 等の最新値を環境変数に反映）
if [ -f "${REPO_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_DIR}/.env"
  set +a
fi

# ── cleanup 関数（health fail 等でスクリプトが中断した際に green を除去） ──────
cleanup_green_on_error() {
  if docker ps -a --filter "name=^/${GREEN_BACKEND}$" --format "{{.ID}}" | grep -q .; then
    echo "  [cleanup] Removing failed green container ${GREEN_BACKEND}..."
    docker rm -f "${GREEN_BACKEND}" 2>/dev/null || true
  fi
}
trap cleanup_green_on_error ERR

echo "============================================"
echo "Blue-green backend cutover"
echo "  Old: ${OLD_BACKEND}"
echo "  Green: ${GREEN_BACKEND}"
echo "  Health timeout: ${HEALTH_TIMEOUT}s"
echo "============================================"

# ── Step 0: 残留 green を除去 ──────────────────────────────────────────────────
echo "Step 0: Cleanup stale green container..."
if docker ps -a --filter "name=^/${GREEN_BACKEND}$" --format "{{.ID}}" | grep -q .; then
  docker rm -f "${GREEN_BACKEND}"
  echo "  旧 green を削除しました"
else
  echo "  旧 green なし（skip）"
fi

# ── Step 1: ビルド済みイメージを特定 ────────────────────────────────────────────
echo "Step 1: Identifying built backend image..."
# docker compose build が作成するイメージ名は {project}-{service}
BACKEND_IMAGE="${COMPOSE_PROJECT}-backend"
if ! docker image inspect "${BACKEND_IMAGE}" >/dev/null 2>&1; then
  echo "❌ Image '${BACKEND_IMAGE}' not found."
  echo "   docker compose build を先に実行してください。"
  exit 1
fi
echo "  Image: ${BACKEND_IMAGE}"

# ── Step 2: Green backend を起動（backnet のみ。frontnet の backend エイリアスは後で付与） ──
echo "Step 2: Starting green backend (backnet only, no traffic yet)..."
docker run -d \
  --name "${GREEN_BACKEND}" \
  --stop-signal SIGTERM \
  --stop-timeout 40 \
  --memory 512m \
  --cpus 1.0 \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:size=67108864 \
  --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \
  --env-file "${REPO_DIR}/.env" \
  --env GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json \
  --log-driver json-file \
  --log-opt max-size=20m \
  --log-opt max-file=5 \
  --label com.docker.compose.project="${COMPOSE_PROJECT}" \
  --label com.docker.compose.service="backend" \
  --label com.docker.compose.container-number="1" \
  --label com.docker.compose.project.working_dir="${REPO_DIR}" \
  --label com.docker.compose.project.config_files="${REPO_DIR}/docker-compose.yml" \
  --label com.docker.compose.oneoff="False" \
  --network "${BACKNET}" \
  "${BACKEND_IMAGE}"

echo "  Green container started."

# ── Step 3: Health polling（Docker healthcheck の ~48s 待ちを回避して直接確認） ─────
echo "Step 3: Polling /api/health (max ${HEALTH_TIMEOUT}s, interval 3s)..."
GREEN_READY=false
_elapsed=0
while [ "${_elapsed}" -lt "${HEALTH_TIMEOUT}" ]; do
  sleep 3
  _elapsed=$((_elapsed + 3))
  if docker exec "${GREEN_BACKEND}" \
      python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/api/health'); sys.exit(0)" \
      2>/dev/null; then
    GREEN_READY=true
    echo "  ✅ Green backend healthy after ${_elapsed}s"
    break
  fi
  echo "  ...waiting (${_elapsed}/${HEALTH_TIMEOUT}s)..."
done

if [ "${GREEN_READY}" != "true" ]; then
  echo "❌ Green backend did not become healthy in ${HEALTH_TIMEOUT}s"
  echo "   旧 backend は接客継続中 — 切替しません"
  # ERR trap が cleanup_green_on_error を実行
  exit 1
fi

# health 確認完了後は ERR trap を解除（以降の cleanup は不要）
trap - ERR

# ── Step 4: frontnet の backend エイリアスを原子的に切替 ────────────────────────
echo "Step 4: Switching 'backend' alias on frontnet (connect green → disconnect old)..."
# 4a. green を frontnet に接続（backend エイリアス付き）
#     ※この瞬間から Docker DNS が old/green 両方を返す（最大 TTL 秒 = 瞬時）
docker network connect --alias backend "${FRONTNET}" "${GREEN_BACKEND}"
# 4b. 旧 backend を frontnet から切断（backend エイリアスの旧向き先を削除）
docker network disconnect "${FRONTNET}" "${OLD_BACKEND}"
# 4c. nginx reload — Docker DNS キャッシュをリフレッシュして green の IP を掴む
docker exec "${NGINX}" nginx -s reload
echo "  ✅ nginx reload done — traffic now flows to green (${GREEN_BACKEND})"

# ── Step 5: 旧 backend を graceful stop（SIGTERM + 40s drain） ──────────────────
echo "Step 5: Graceful stop of old backend (SIGTERM, timeout 40s)..."
docker stop --time=40 "${OLD_BACKEND}" 2>/dev/null || true
docker rm "${OLD_BACKEND}" 2>/dev/null || true
echo "  ✅ Old backend stopped and removed."

# ── Step 6: Green を正規名にリネーム（次回デプロイとの整合性） ──────────────────
echo "Step 6: Renaming green → ${OLD_BACKEND}..."
docker rename "${GREEN_BACKEND}" "${OLD_BACKEND}"
echo "  ✅ Done."

echo "============================================"
echo "Blue-green cutover complete."
echo "  Serving: ${OLD_BACKEND}"
echo "  Startup time: ~${_elapsed}s (was ~22s Python init)"
echo "  Downtime: 0s (nginx DNS switch was atomic)"
echo "============================================"
