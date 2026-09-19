#!/usr/bin/env bash
# 前日の停止要約を Discord owner ping に流す仲介ラッパー。
# - 既存の stop-log-digest.sh / discord-owner-ping.sh は無変更
# - 失敗しても作業を止めない fail-open

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIGEST_SCRIPT="${REPO_ROOT}/.claude/hooks/stop-log-digest.sh"
DISCORD_PING_SCRIPT="${REPO_ROOT}/scripts/notify/discord-owner-ping.sh"
MAX_BODY_CHARS=1900
ELLIPSIS="…(省略)"

usage() {
    cat <<'EOF'
Usage: stop-log-digest-to-discord.sh [--dry-run]
EOF
}

trim_body() {
    local body="$1"
    if [[ ${#body} -le ${MAX_BODY_CHARS} ]]; then
        printf '%s' "$body"
        return 0
    fi

    local limit=$((MAX_BODY_CHARS - ${#ELLIPSIS}))
    printf '%s%s' "${body:0:limit}" "${ELLIPSIS}"
}

DRY_RUN=0
if [[ $# -gt 1 ]]; then
    usage >&2
    exit 0
fi

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
elif [[ -n "${1:-}" ]]; then
    usage >&2
    exit 0
fi

if [[ ! -x "${DIGEST_SCRIPT}" && ! -f "${DIGEST_SCRIPT}" ]]; then
    exit 0
fi

BODY=""
if ! BODY="$(bash "${DIGEST_SCRIPT}" 2>/dev/null)"; then
    exit 0
fi

if [[ -z "${BODY}" ]]; then
    exit 0
fi

BODY="$(trim_body "${BODY}")"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '送信本文プレビュー:\n%s\n' "${BODY}"
    exit 0
fi

if [[ ! -f "${DISCORD_PING_SCRIPT}" ]]; then
    exit 0
fi

if ! bash "${DISCORD_PING_SCRIPT}" "${BODY}"; then
    exit 0
fi

exit 0
