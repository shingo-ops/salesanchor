#!/usr/bin/env bash
# build-on-github 便2（docs/handoff/build-on-github/design.md §9-2「手動」・§26）。
# 手で流す戻し: .env の必須の 5 つの指紋を 1 つ前（.deploy_prev_images.env）に戻して、組み立てずに起こし直す。
# 完成品が prod1 に無いときは、GHCR_PULL_TOKEN と GHCR_USER を渡して scripts/deploy/pull-images.sh を先に流す。
# secretary-codex（付け足しの機能・§26-8）は数えず、.env のその行も変えず、起こし直さない（戻しの速さ K6 に入れない）。
set -euo pipefail
cd "${REPO_DIR:-/home/ubuntu/salesanchor}"
_t0="$(date +%s)"
_re='^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE='
_keys="BACKEND_IMAGE FRONTEND_IMAGE GEMINI_EGRESS_IMAGE GHA_EXPORTER_IMAGE SECRETARY_AGENT_IMAGE"

# (1) 控えが必須の 5 行そろっていること
_n="$(grep -cE "${_re}" .deploy_prev_images.env 2>/dev/null || true)"
if [ "${_n:-0}" != "5" ]; then
  echo "❌ .deploy_prev_images.env に必須の 5 行がありません（${_n:-0} 行）。戻せません"
  exit 1
fi

# (4 の先読み) 5 つの指紋がローカルに在ること。無ければ .env に触る前に止まる
for _k in ${_keys}; do
  _v="$(grep -m1 "^${_k}=" .deploy_prev_images.env | cut -d= -f2-)"
  if ! docker image inspect "${_v}" >/dev/null 2>&1; then
    echo "❌ ${_k} の完成品がこの機械にありません。GHCR_PULL_TOKEN と GHCR_USER を渡して scripts/deploy/pull-images.sh を流してから、もう一度流してください"
    exit 1
  fi
done

# (2) 今の 5 行を写す（戻した後でやっぱり進めたいとき用）
grep -E "${_re}" .env > .deploy_rollback_from.env 2>/dev/null || : > .deploy_rollback_from.env

# (3) .env の 5 行を控えで置き換える
for _k in ${_keys}; do
  sed -i "/^${_k}=/d" .env
  grep -m1 "^${_k}=" .deploy_prev_images.env >> .env
done
echo "rollback: .env の 5 行を控えに戻しました"

# (5) backend の無停止の切替（試験で偽に差し替えるため CUTOVER_SCRIPT）
bash "${CUTOVER_SCRIPT:-scripts/blue-green-cutover.sh}"

# (6) deploy.yml の Step 3c と同じ順（celery-worker は実行中の仕事を終えさせてから。discord-gateway の二重起動を防ぐため先に消す）
docker compose stop -t 60 celery-worker 2>/dev/null || true
for _svc in frontend celery-beat discord-gateway celery-worker; do
  docker ps -a --filter "name=astro-webapp-${_svc}" --filter "label=com.docker.compose.oneoff=False" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
done
docker compose up -d --no-build --no-deps frontend celery-worker celery-beat discord-gateway gemini-egress gha-exporter

# (7) 秘書（deploy.yml の Start secretary-agent と同じ形。落ちても (8) へ進む）
if [ ! -r "${SECRETARY_ENV_FILE:-/home/ubuntu/.config/salesanchor/secretary-agent.env}" ]; then
  echo "::warning::secretary-agent.env が読めないため secretary-agent を起こしません"
else
  docker compose -p astro-webapp-secretary -f docker-compose.secretary-agent.yml up -d --force-recreate --no-build \
    || echo "::warning::secretary-agent を起こせませんでした"
fi

# (8) 健康確認（if の形にして、set -e の下で 1 回目の失敗で止まらないようにする）
_ok=false
for _i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if docker exec astro-webapp-backend-1 python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"; then
    _ok=true
    break
  fi
  echo "health attempt ${_i} failed"
  sleep "${ROLLBACK_HC_SLEEP:-5}"
done
if [ "${_ok}" != "true" ]; then
  echo "❌ 戻した後の健康確認が 12 回とも落ちました"
  exit 1
fi

# (9) 所要秒（K6）
_t1="$(date +%s)"
echo "rollback done in $((_t1 - _t0)) s"
