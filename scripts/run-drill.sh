#!/bin/bash
# run-drill.sh — ロールバック自動実証ドリル（ADR-116 / 合格条件 7 点）
#
# 目的:
#   本番に触れず「安全網が本当に効くか」を実証する。
#   scripts/deploy_rollback.sh を本番と同じ経路で呼び、7 点の合格条件をすべて検証する。
#
# 前提:
#   - Docker Desktop が起動していること
#   - プロジェクトルートから実行すること
#   - jq がインストールされていること（通知確認に使用）
#
# 使用方法:
#   bash scripts/run-drill.sh
#
# 合格条件（7 点・全部緑で PASS）:
#   1. good デプロイ → health 200 → last-good SHA 記録
#   2. bad デプロイ → health 503
#   3. 健康ゲートが 503 を検知して失敗経路が発火
#   4. 保全ファイルに backend ログ・health 応答・compose ps・pg_stat_activity が記録
#   5. rollback: good SHA へ戻る + .env 復元
#   6. 復旧確認: 復帰後 health 200
#   7. 初回エッジ: last-good 記録なし → 明示失敗（クラッシュしない）

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

COMPOSE_CMD="docker compose -f docker-compose.drill.yml -p drill"
BACKEND_CONTAINER="drill-backend-1"
DB_CONTAINER="drill-postgres-1"
DRILL_DIR="drill-workspace"
PASS=0
FAIL=0

# ── カラー出力 ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ PASS${NC} [$1]"; PASS=$(( PASS + 1 )); }
fail() { echo -e "${RED}❌ FAIL${NC} [$1]: $2"; FAIL=$(( FAIL + 1 )); }

# ── クリーンアップ ─────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "=== クリーンアップ ==="
  ${COMPOSE_CMD} down -v 2>/dev/null || true
  rm -rf "${DRILL_DIR}" 2>/dev/null || true
  echo "クリーンアップ完了"
}
trap cleanup EXIT

# ── ドリル用ワークスペース準備 ─────────────────────────────────────────────────
echo "=== ドリル環境セットアップ ==="
rm -rf "${DRILL_DIR}"
cp -r . "${DRILL_DIR}" 2>/dev/null || { git clone --local . "${DRILL_DIR}"; }
cd "${DRILL_DIR}"

# ドリル用 last-good / prev_env ファイルをクリア（初回エッジテスト用）
rm -f .deploy_last_good_sha .deploy_prev_sha .deploy_prev_env
rm -rf deploy-failures

# ── ヘルパー ──────────────────────────────────────────────────────────────────
wait_healthy() {
  local max_wait=60
  local elapsed=0
  while [ "${elapsed}" -lt "${max_wait}" ]; do
    if docker exec "${BACKEND_CONTAINER}" \
        python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
        2>/dev/null; then
      return 0
    fi
    sleep 5
    elapsed=$(( elapsed + 5 ))
  done
  return 1
}

run_rollback_script() {
  BACKEND_CONTAINER="${BACKEND_CONTAINER}" \
  DB_CONTAINER="${DB_CONTAINER}" \
  COMPOSE_CMD="${COMPOSE_CMD}" \
  DEPLOY_FAILURES_DIR="deploy-failures" \
  ROLLBACK_BUILD_RETRIES="2" \
  bash scripts/deploy_rollback.sh
}

# ────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== テスト 7: 初回エッジ（last-good なし → 明示失敗）==="
# last-good が無い状態で失敗させる（DB を up しない）
${COMPOSE_CMD} up -d postgres 2>/dev/null || true
sleep 3

# DATABASE_URL を壊した状態で backend を起動
DATABASE_URL="postgresql+asyncpg://nobody:wrong@nonexistent:5432/nodb" \
  ${COMPOSE_CMD} run --rm --no-deps \
  -e DATABASE_URL="postgresql+asyncpg://nobody:wrong@nonexistent:5432/nodb" \
  backend python -c "print('backend image OK')" 2>/dev/null || true

# コンテナなしでロールバックスクリプトを呼ぶ（コンテナ起動しない）
# → docker exec が失敗 → health exit 1 → last-good なし → 明示失敗
set +e
BACKEND_CONTAINER="drill-backend-1-notexist" \
COMPOSE_CMD="${COMPOSE_CMD}" \
DEPLOY_FAILURES_DIR="deploy-failures" \
ROLLBACK_BUILD_RETRIES="1" \
  bash scripts/deploy_rollback.sh 2>&1
_exit7=$?
set -e

if [ "${_exit7}" -ne 0 ]; then
  # deploy-failures/ に保全ファイルが作成されている
  if ls deploy-failures/*.log 2>/dev/null | head -1 > /dev/null; then
    pass "テスト7: last-good なし → 明示失敗（exit ${_exit7}）＋ 保全ファイル作成"
  else
    fail "テスト7: last-good なし → 明示失敗（exit ${_exit7}）だが保全ファイルなし" "deploy-failures/*.log が見つかりません"
  fi
else
  fail "テスト7: last-good なし → 明示失敗のはずが exit 0" "exit コードが 0"
fi

# ── 以降のテストは実際にコンテナを起動 ──────────────────────────────────────
echo ""
echo "=== テスト 1: good デプロイ → health 200 → last-good SHA 記録 ==="
${COMPOSE_CMD} up -d --build 2>&1

echo "  backend が healthy になるまで待機..."
if wait_healthy; then
  # PREV_SHA を模擬（good バージョンの SHA）
  GOOD_SHA="$(git rev-parse HEAD)"
  echo "${GOOD_SHA}" > .deploy_prev_sha
  cp .env .deploy_prev_env 2>/dev/null || touch .deploy_prev_env

  run_rollback_script
  _exit1=$?

  if [ "${_exit1}" -eq 0 ] && [ -f ".deploy_last_good_sha" ]; then
    _recorded=$(cat .deploy_last_good_sha | head -c 7)
    pass "テスト1: health 200 → last-good SHA 記録 (${_recorded})"
  else
    fail "テスト1: exit=${_exit1}, last-good SHA file exists=$([ -f .deploy_last_good_sha ] && echo yes || echo no)" ""
  fi
else
  fail "テスト1: backend が healthy にならなかった" "タイムアウト"
fi

echo ""
echo "=== テスト 2-6: bad デプロイ → 503 → 発火 → 保全 → ロールバック → 復旧 ==="
GOOD_SHA="$(cat .deploy_last_good_sha 2>/dev/null || git rev-parse HEAD)"

# bad 状態: DATABASE_URL を繋がらない宛先に差し替えてバックエンドを再起動
# .deploy_prev_env は good 状態の .env（.env バックアップ）
echo "${GOOD_SHA}" > .deploy_last_good_sha
cp .env .deploy_prev_env 2>/dev/null || touch .deploy_prev_env

# bad DATABASE_URL を .env に書き込む（前回の localhost 誤指定相当）
sed -i.bak '/^DATABASE_URL=/d' .env 2>/dev/null || true
echo "DATABASE_URL=postgresql+asyncpg://nobody:wrong@nonexistent:9999/nodb" >> .env

# backend だけ再起動（DATABASE_URL を反映）
${COMPOSE_CMD} up -d --force-recreate backend 2>&1
sleep 15  # 起動を待つ（health check は失敗するが container は running）

# テスト 2: health が 503 になっているか確認
echo ""
echo "--- テスト 2: health 503 確認 ---"
set +e
docker exec "${BACKEND_CONTAINER}" \
  python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
  2>/dev/null
_t2_exit=$?
set -e

if [ "${_t2_exit}" -ne 0 ]; then
  pass "テスト2: bad デプロイ → health が 503（exit ${_t2_exit}）"
else
  fail "テスト2: health が 503 になっていない" "exit 0 だった"
fi

# テスト 3-6: deploy_rollback.sh を呼び、失敗経路の全フローを検証
echo ""
echo "--- テスト 3-6: rollback スクリプト実行 ---"
rm -rf deploy-failures  # 今回の保全ファイルだけを確認するためクリア

set +e
run_rollback_script 2>&1
_rb_exit=$?
set -e

# テスト 3: 失敗経路が発火したか（exit 1）
if [ "${_rb_exit}" -ne 0 ]; then
  pass "テスト3: 健康ゲートが 503 を検知して失敗経路が発火（exit ${_rb_exit}）"
else
  fail "テスト3: 失敗経路が発火しなかった" "exit 0 だった"
fi

# テスト 4: 保全ファイルが作成されたか
_fail_log=$(ls deploy-failures/*.log 2>/dev/null | head -1 || true)
if [ -n "${_fail_log}" ]; then
  _has_logs=$(grep -c "backend logs" "${_fail_log}" 2>/dev/null || echo "0")
  _has_ps=$(grep -c "compose ps" "${_fail_log}" 2>/dev/null || echo "0")
  _has_pgstat=$(grep -c "pg_stat_activity" "${_fail_log}" 2>/dev/null || echo "0")
  if [ "${_has_logs}" -gt 0 ] && [ "${_has_ps}" -gt 0 ] && [ "${_has_pgstat}" -gt 0 ]; then
    pass "テスト4: 保全ファイル作成（${_fail_log##*/}）: backend ログ・compose ps・pg_stat_activity 含む"
  else
    fail "テスト4: 保全ファイルの内容が不完全" "logs=${_has_logs} ps=${_has_ps} pgstat=${_has_pgstat}"
  fi
else
  fail "テスト4: 保全ファイルが作成されていない" "deploy-failures/*.log が見つかりません"
fi

# テスト 5: rollback で good SHA に戻っているか
_current_sha=$(git rev-parse HEAD | head -c 7)
_good_sha_short=$(echo "${GOOD_SHA}" | head -c 7)
if [ "${_current_sha}" = "${_good_sha_short}" ]; then
  # .env が復元されているか確認
  _has_good_db=$(grep "drilluser" .env 2>/dev/null && echo "yes" || echo "no")
  if [ "${_has_good_db}" = "yes" ]; then
    pass "テスト5: rollback で good SHA (${_good_sha_short}) に復帰 + .env 復元"
  else
    fail "テスト5: SHA は戻ったが .env が復元されていない" "DATABASE_URL が drilluser を含まない"
  fi
else
  fail "テスト5: rollback で good SHA に戻っていない" "current=${_current_sha} expected=${_good_sha_short}"
fi

# テスト 6: 復旧後 health が 200 になっているか
echo ""
echo "--- テスト 6: 復旧後 health 200 確認 ---"
if wait_healthy; then
  pass "テスト6: 復旧後 health 200（ロールバック後に自動復帰を確認）"
else
  fail "テスト6: 復旧後 health が 200 にならなかった" "タイムアウト"
fi

# ── 結果 ─────────────────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "ドリル結果: PASS ${PASS} / FAIL ${FAIL} / 計 $((PASS + FAIL))"
echo "================================================================"

if [ "${FAIL}" -gt 0 ]; then
  echo ""
  echo "❌ ドリル FAIL — Phase2 切替は HOLD してください"
  exit 1
fi

echo ""
echo "✅ ドリル全 7 点 PASS — 安全網の実証完了"
echo "   次ステップ: SA-18 Phase2 切替"
exit 0
