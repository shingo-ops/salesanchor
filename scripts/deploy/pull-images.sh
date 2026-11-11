#!/usr/bin/env bash
# build-on-github 便2（docs/handoff/build-on-github/design.md §12 便2 9.・§26）。
# prod1 で .env の必須の 5 つの指紋と、在れば secretary-codex の指紋を倉庫から受け取る。組み立てはしない。箱には触らない。
# 使い方（deploy.yml の Step 3 から）: GHCR_USER と GHCR_PULL_TOKEN を env で渡して bash scripts/deploy/pull-images.sh
set -euo pipefail
cd "${REPO_DIR:-/home/ubuntu/salesanchor}"
docker compose version
# 守り（K1・§26-1 5.）: 本番の compose に build: が 1 つも無いこと
_nb="$(docker compose config --format json | python3 -c 'import json,sys;print(sum(1 for s in json.load(sys.stdin)["services"].values() if "build" in s))')"
if [ "${_nb}" != "0" ]; then
  echo "❌ compose に build: を持つサービスが ${_nb} 個ある（本番では 0 のはず。override が読まれていないか確かめる）"
  exit 1
fi
_refs=()
for _k in BACKEND_IMAGE FRONTEND_IMAGE GEMINI_EGRESS_IMAGE GHA_EXPORTER_IMAGE SECRETARY_AGENT_IMAGE; do
  _v="$(grep -m1 "^${_k}=" .env | cut -d= -f2- || true)"
  if ! [[ "${_v}" =~ ^ghcr\.io/[a-z0-9-]+/salesanchor-[a-z0-9-]+@sha256:[0-9a-f]{64}$ ]]; then
    echo "❌ .env の ${_k} の形が違う"
    exit 1
  fi
  _refs+=("${_v}")
done
if [ -z "${GHCR_PULL_TOKEN:-}" ] || [ -z "${GHCR_USER:-}" ]; then
  echo "❌ GHCR_PULL_TOKEN か GHCR_USER が空（GitHub の secret と Variables を確かめる）"
  exit 1
fi
# 鍵は受け取りの間だけ置く（design.md §23・§26-1 7.）
trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT
printf '%s' "${GHCR_PULL_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin >/dev/null
for _r in "${_refs[@]}"; do
  _ok=false
  for _a in 1 2 3; do
    if docker pull -q "${_r}" >/dev/null; then _ok=true; break; fi
    echo "pull attempt ${_a} failed (${_r##*/}). 15秒後にリトライ..."
    sleep "${PULL_RETRY_SLEEP:-15}"
  done
  if [ "${_ok}" != "true" ]; then
    echo "❌ ${_r##*/} を 3 回受け取れませんでした"
    exit 1
  fi
  echo "pulled ${_r##*/}"
done
echo "pull ok (5 images)"
# secretary-codex（付け足しの機能・design.md §26-8）: 行が在れば受け取る。受け取れなくても本体は止めない。
# 受け取れなかった指紋を .env に残さない（§26-1 3.）: その 1 行だけ控えの行に戻す（控えに無ければ消すだけ）。
_sc="$(grep -m1 '^SECRETARY_CODEX_IMAGE=' .env | cut -d= -f2- || true)"
if [ -n "${_sc}" ]; then
  _sc_ok=false
  if [[ "${_sc}" =~ ^ghcr\.io/[a-z0-9-]+/salesanchor-secretary-codex@sha256:[0-9a-f]{64}$ ]]; then
    for _a in 1 2 3; do
      if docker pull -q "${_sc}" >/dev/null; then _sc_ok=true; break; fi
      echo "pull attempt ${_a} failed (secretary-codex). 15秒後にリトライ..."
      sleep "${PULL_RETRY_SLEEP:-15}"
    done
  fi
  if [ "${_sc_ok}" = "true" ]; then
    echo "pulled ${_sc##*/}"
  else
    echo "::warning::secretary-codex の完成品を受け取れませんでした（本体の反映は続けます。.env のその行は控えに戻します）"
    sed -i '/^SECRETARY_CODEX_IMAGE=/d' .env
    grep '^SECRETARY_CODEX_IMAGE=' .deploy_prev_images.env >> .env 2>/dev/null || true
  fi
fi
exit 0
