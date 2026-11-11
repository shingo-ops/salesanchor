#!/usr/bin/env bash
# build-on-github 便2（design.md §9-1）: 倉庫から受け取った完成品のうち、今（.env）と 1 つ前（.deploy_prev_images.env）の指紋以外を消す。
# docker image prune は呼ばない（指紋だけの完成品が消えるかは未確認 U30）。使用中の完成品は docker が消さない（-f を付けない）。
set -uo pipefail
cd "${REPO_DIR:-/home/ubuntu/salesanchor}"
_keep="$(cat .env .deploy_prev_images.env 2>/dev/null | grep -E '^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT|SECRETARY_CODEX)_IMAGE=' | cut -d= -f2- | sort -u)"
if [ -z "${_keep}" ]; then
  echo "prune: 残す指紋が読めないので何も消さない"
  exit 0
fi
docker images --digests --format '{{.Repository}}@{{.Digest}}' | sort -u | while read -r _ref; do
  case "${_ref}" in ghcr.io/*/salesanchor-*@sha256:*) ;; *) continue ;; esac
  if printf '%s\n' "${_keep}" | grep -qxF "${_ref}"; then continue; fi
  if docker image rm "${_ref}" >/dev/null 2>&1; then echo "prune: removed ${_ref##*/}"; else echo "prune: kept (in use) ${_ref##*/}"; fi
done
exit 0
