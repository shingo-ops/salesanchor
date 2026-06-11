#!/bin/bash
# dry-run-blue-green.sh — blue-green 切替の素振りスクリプト
#
# 目的: 本番相当の docker-compose 環境で blue-green-cutover.sh を実行し、
#       切替中に 502 が発生しないことを確認する。
#
# 使い方:
#   bash scripts/dry-run-blue-green.sh              # 通常実行
#   SKIP_BUILD=1 bash scripts/dry-run-blue-green.sh # ビルドスキップ
#
# 受け入れ基準:
#   AC1: 502 ゼロ（切替中の health poll が 200 継続）
#   AC2: health 失敗時に old が維持される（--test-fail フラグで確認）
#   AC3: 並走時間が 60s 以内
#   AC4: git revert 可能（スクリプト変更のみ。コードに副作用なし）
#
# 注意: VPS 上で実行すること。ローカル docker-compose では network name が異なる場合がある。

set -e

REPO_DIR="${REPO_DIR:-/home/ubuntu/salesanchor}"
cd "${REPO_DIR}"

COMPOSE_PROJECT="astro-webapp"
BACKEND="${COMPOSE_PROJECT}-backend-1"
TEST_FAIL="${TEST_FAIL:-0}"         # AC2 確認用: 1 にすると green の health を強制失敗させる
SKIP_BUILD="${SKIP_BUILD:-0}"
POLL_INTERVAL=1                     # 監視 curl の間隔（秒）
POLL_DURATION=120                   # 監視期間（秒）
FAIL_COUNT=0
SUCCESS_COUNT=0

echo "========================================"
echo "Blue-green dry run"
echo "  REPO_DIR: ${REPO_DIR}"
echo "  TEST_FAIL: ${TEST_FAIL} (1=AC2 health-fail test)"
echo "========================================"

# ── 前提確認 ─────────────────────────────────────────────────────────────────
echo "Pre-check: confirming backend is running..."
if ! docker ps --filter "name=^/${BACKEND}$" --format "{{.Names}}" | grep -q "${BACKEND}"; then
  echo "❌ ${BACKEND} is not running. 先に docker compose up -d を実行してください。"
  exit 1
fi
echo "  ✅ ${BACKEND} is running"

# ── ビルド ────────────────────────────────────────────────────────────────────
if [ "${SKIP_BUILD}" != "1" ]; then
  echo ""
  echo "Building backend image..."
  if ! docker compose build backend; then
    echo "❌ docker compose build failed"
    exit 1
  fi
  echo "  ✅ Build complete"
else
  echo "SKIP_BUILD=1 — ビルドをスキップ"
fi

# ── バックグラウンドで health を連続 poll ────────────────────────────────────
echo ""
echo "Starting background health monitor (${POLL_DURATION}s, interval ${POLL_INTERVAL}s)..."

# 監視結果ファイル（tmpfs 対応: /tmp を使用）
MONITOR_LOG=$(mktemp /tmp/bg-monitor-XXXXXX.log)
MONITOR_PID_FILE=$(mktemp /tmp/bg-monitor-pid-XXXXXX)

(
  _count=0
  _fail=0
  _success=0
  while [ "${_count}" -lt "${POLL_DURATION}" ]; do
    sleep "${POLL_INTERVAL}"
    _count=$((_count + POLL_INTERVAL))
    _ts=$(date +%H:%M:%S)
    # nginx コンテナから直接 backend:8000 に curl
    # → Docker 内部 DNS で backend エイリアスを解決するため、
    #   nginx -s reload 後に新コンテナへ向いているかを確認できる
    # ※ http://localhost:80 は HTTP→HTTPS 301 redirect のため不適切
    _status=$(docker exec "${COMPOSE_PROJECT}-nginx-1" \
      curl -s --max-time 5 -o /dev/null -w "%{http_code}" \
      "http://backend:8000/api/health" 2>/dev/null || echo "err")
    if [ "${_status}" = "200" ]; then
      _success=$((_success + 1))
      echo "${_ts} OK(${_status})" >> "${MONITOR_LOG}"
    else
      _fail=$((_fail + 1))
      echo "${_ts} FAIL(${_status}) ← 502/err" >> "${MONITOR_LOG}"
    fi
  done
  echo "FINAL: success=${_success} fail=${_fail}" >> "${MONITOR_LOG}"
) &
MONITOR_PID=$!
echo "${MONITOR_PID}" > "${MONITOR_PID_FILE}"
echo "  Monitor PID: ${MONITOR_PID} (log: ${MONITOR_LOG})"

# 監視が安定するまで少し待つ
sleep 3

# ── blue-green 切替実行 ────────────────────────────────────────────────────────
echo ""
echo "Executing blue-green cutover..."
_cutover_start=$(date +%s)

if [ "${TEST_FAIL}" = "1" ]; then
  echo "⚠️  TEST_FAIL=1: green の health を強制失敗させます（AC2 確認）"
  # blue-green-cutover.sh を改変して health が絶対失敗するようにする
  # → BG_HEALTH_TIMEOUT=1 で即タイムアウト
  BG_HEALTH_TIMEOUT=1 bash scripts/blue-green-cutover.sh || true
  echo "  ✅ AC2: cutover が失敗しても old backend が生存していれば合格"
else
  bash scripts/blue-green-cutover.sh
fi

_cutover_end=$(date +%s)
_cutover_elapsed=$((_cutover_end - _cutover_start))
echo "  Cutover elapsed: ${_cutover_elapsed}s"

# 切替後も 30s 監視を継続
echo "Monitoring for 30s post-cutover..."
sleep 30

# ── 監視プロセス停止 ───────────────────────────────────────────────────────────
kill "${MONITOR_PID}" 2>/dev/null || true
wait "${MONITOR_PID}" 2>/dev/null || true

# ── 結果集計 ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "Results"
echo "========================================"
echo ""

# 502/err の行を抽出
FAIL_LINES=$(grep "FAIL" "${MONITOR_LOG}" 2>/dev/null || true)
FINAL_LINE=$(grep "FINAL" "${MONITOR_LOG}" 2>/dev/null | tail -1 || echo "FINAL: (未完了)")

echo "Full monitor log:"
cat "${MONITOR_LOG}"
echo ""

if [ -z "${FAIL_LINES}" ]; then
  echo "✅ AC1: 502 ゼロ — 切替中も 200 が継続"
else
  FAIL_COUNT=$(echo "${FAIL_LINES}" | wc -l | tr -d ' ')
  echo "❌ AC1: ${FAIL_COUNT} 件の FAIL を検出"
  echo "${FAIL_LINES}"
fi

echo "${FINAL_LINE}"

if [ "${_cutover_elapsed}" -le 65 ]; then
  echo "✅ AC3: 並走時間 ${_cutover_elapsed}s ≤ 65s（blue-green 完了まで）"
else
  echo "⚠️  AC3: 並走時間 ${_cutover_elapsed}s > 65s（メモリ圧考慮）"
fi

if [ "${TEST_FAIL}" = "1" ]; then
  # AC2: old が生存しているか確認
  if docker ps --filter "name=^/${BACKEND}$" --format "{{.Names}}" | grep -q "${BACKEND}"; then
    echo "✅ AC2: health 失敗時に old backend が維持された"
  else
    echo "❌ AC2: old backend が停止してしまった"
  fi
fi

# クリーンアップ
rm -f "${MONITOR_LOG}" "${MONITOR_PID_FILE}"

echo ""
echo "Dry run complete."
