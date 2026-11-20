#!/usr/bin/env bash
# 毎週の本番反映の止まりの数え（.github/workflows/weekly-deploy-lock-count.yml）の、定時の実行の道でだけ使う小さな台本。
# 設計: docs/handoff/deploy-db-stall/design.md §19-19。
# 定時の実行が遅れても抜けても、数える週を「前の月曜 0:00〜この月曜 0:00 JST」に決め、数え済みかを調べる。
# 標準出力: since= / until= / decision=count|skip / late=0|1 / reason= / api_calls= の6行（この順）。
set -u

NOW=""
RUNS_FILE=""
RUN_ID="${GITHUB_RUN_ID:-}"
RUNS_FILE_SET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --now)
      [ $# -ge 2 ] || { echo "--now needs a value" >&2; exit 1; }
      NOW="$2"; shift 2 ;;
    --runs-file)
      [ $# -ge 2 ] || { echo "--runs-file needs a value" >&2; exit 1; }
      RUNS_FILE="$2"; RUNS_FILE_SET=1; shift 2 ;;
    --run-id)
      [ $# -ge 2 ] || { echo "--run-id needs a value" >&2; exit 1; }
      RUN_ID="$2"; shift 2 ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1 ;;
  esac
done

if [ -z "${NOW}" ]; then
  NOW="$(date +%s)"
fi
case "${NOW}" in
  ''|*[!0-9]*) echo "--now must be UNIX seconds" >&2; exit 1 ;;
esac

# 1. 週を決める（日本時間の日付と曜日。月曜=1）
TODAY="$(TZ=Asia/Tokyo date -d "@${NOW}" +%F)"
DOW="$(TZ=Asia/Tokyo date -d "@${NOW}" +%u)"
UNTIL="$(date -u -d "${TODAY} -$((DOW - 1)) days" +%F)"
SINCE="$(date -u -d "${UNTIL} -7 days" +%F)"
BOUNDARY="$(date -u -d "${UNTIL} 00:00 +0900" +%Y-%m-%dT%H:%M:%SZ)"

# 4. 遅れの印
if [ "${DOW}" = "1" ]; then LATE=0; else LATE=1; fi

# 2・3. 数え済みか調べる（引けなかったときは count に倒す）
DECISION="count"
REASON=""
API_CALLS=0
RESP=""
LOOKUP_OK=1

if [ "${RUNS_FILE_SET}" = "1" ]; then
  if [ -f "${RUNS_FILE}" ]; then
    RESP="$(cat "${RUNS_FILE}")" || LOOKUP_OK=0
  else
    LOOKUP_OK=0
  fi
else
  API_CALLS=1
  REPO="${GITHUB_REPOSITORY:-shingo-ops/salesanchor}"
  RESP="$(gh api "repos/${REPO}/actions/workflows/weekly-deploy-lock-count.yml/runs?event=schedule&status=success&per_page=100&created=%3E%3D${BOUNDARY}" 2>/dev/null)" || LOOKUP_OK=0
fi

if [ "${LOOKUP_OK}" = "1" ]; then
  N="$(printf '%s' "${RESP}" | jq -e --arg b "${BOUNDARY}" --arg me "${RUN_ID}" \
    '[.workflow_runs[] | select(.created_at >= $b) | select((.id | tostring) != $me)] | length' 2>/dev/null)" || LOOKUP_OK=0
  if [ "${LOOKUP_OK}" = "1" ]; then
    case "${N}" in
      ''|*[!0-9]*) LOOKUP_OK=0 ;;
      *) if [ "${N}" -ge 1 ]; then DECISION="skip"; fi ;;
    esac
  fi
fi

if [ "${LOOKUP_OK}" != "1" ]; then
  DECISION="count"
  REASON="runs lookup failed"
fi

echo "since=${SINCE}"
echo "until=${UNTIL}"
echo "decision=${DECISION}"
echo "late=${LATE}"
echo "reason=${REASON}"
echo "api_calls=${API_CALLS}"
exit 0
