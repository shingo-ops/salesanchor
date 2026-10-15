#!/usr/bin/env bash
# check_config_drift.sh の試験（ADR-1012 段階1 便7）
# repo の作業ツリーの監視設定 6 本を一時ディレクトリの「repo 役」と「本番役」に写し、DRY_RUN=1 で呼ぶ
# 実行: bash monitoring/scripts/tests/test_check_config_drift.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_ROOT="$(cd "${HERE}/../../.." && pwd)"
SCRIPT="${REAL_ROOT}/monitoring/scripts/check_config_drift.sh"

FILES=(
  docker-compose.monitoring.yml
  monitoring/prometheus/prometheus.yml
  monitoring/prometheus/alert_rules.yml
  monitoring/loki/loki-config.yaml
  monitoring/loki/rules/jarvis/alerts.yml
  monitoring/alertmanager/alertmanager.yml
)

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

# 6 本を 1 か所に写す
copy_files() {
  local dest="$1" f
  for f in "${FILES[@]}"; do
    mkdir -p "${dest}/$(dirname "${f}")"
    cp "${REAL_ROOT}/${f}" "${dest}/${f}"
  done
}

# 新しい repo 役と本番役を作る
fresh() {
  rm -rf "${TMP}/repo" "${TMP}/deploy"
  copy_files "${TMP}/repo"
  copy_files "${TMP}/deploy"
}

# 出力に固定文字列があるか
has() { printf '%s\n' "$1" | grep -qF -- "$2"; }
# 出力の中の DRIFT の行数
count_drift_lines() { printf '%s\n' "$1" | grep -c '^DRIFT' || true; }
# 出力の中の 64 桁の 16 進の行数
count_sha() { printf '%s\n' "$1" | grep -cE '[0-9a-f]{64}' || true; }

ALL_OUT=""

# 1. 同じ
fresh
out1="$(DRY_RUN=1 bash "${SCRIPT}" "${TMP}/repo" "${TMP}/deploy")"
ALL_OUT+="${out1}"$'\n'
if has "${out1}" "checked=6 drift=0" && has "${out1}" "monitoring_config_drift_files 0" && [ "$(count_drift_lines "${out1}")" = "0" ]; then
  pass "1a 同じ: drift=0"
else
  fail "1a 同じ: drift=0"
fi
ts="$(printf '%s\n' "${out1}" | sed -n 's/^monitoring_config_drift_last_run_timestamp //p')"
now="$(date +%s)"
diff_s=$(( now - ts ))
[ "${diff_s}" -lt 0 ] && diff_s=$(( -diff_s ))
if [ -n "${ts}" ] && [ "${diff_s}" -le 5 ]; then
  pass "1b 送る時刻が今と 5 秒以内"
else
  fail "1b 送る時刻が今と 5 秒以内 (ts=${ts} now=${now})"
fi

# 2. 1 本ずれ
fresh
echo "# drift test" >> "${TMP}/deploy/monitoring/prometheus/alert_rules.yml"
out2="$(DRY_RUN=1 bash "${SCRIPT}" "${TMP}/repo" "${TMP}/deploy")"
ALL_OUT+="${out2}"$'\n'
if has "${out2}" "DRIFT: monitoring/prometheus/alert_rules.yml" && [ "$(count_drift_lines "${out2}")" = "1" ] \
   && has "${out2}" "checked=6 drift=1" && has "${out2}" "monitoring_config_drift_files 1"; then
  pass "2 1 本ずれ: 1 件を名前つきで数える"
else
  fail "2 1 本ずれ: 1 件を名前つきで数える"
fi

# 3. 1 本無い
fresh
rm "${TMP}/deploy/monitoring/loki/rules/jarvis/alerts.yml"
out3="$(DRY_RUN=1 bash "${SCRIPT}" "${TMP}/repo" "${TMP}/deploy")"
ALL_OUT+="${out3}"$'\n'
if has "${out3}" "DRIFT (missing or unreadable): monitoring/loki/rules/jarvis/alerts.yml" && has "${out3}" "drift=1"; then
  pass "3 1 本無い: ずれに数える"
else
  fail "3 1 本無い: ずれに数える"
fi

# 4. ログに sha256 が出ない
if [ "$(count_sha "${ALL_OUT}")" = "0" ]; then
  pass "4 ログに 64 桁の 16 進が出ない"
else
  fail "4 ログに 64 桁の 16 進が出ない"
fi

# 5. 送れないときは失敗で終わる
fresh
rc=0
PUSHGATEWAY_URL=http://127.0.0.1:9 bash "${SCRIPT}" "${TMP}/repo" "${TMP}/deploy" >/dev/null 2>&1 || rc=$?
if [ "${rc}" -ne 0 ]; then
  pass "5 送れないとき終了コードが 0 でない (rc=${rc})"
else
  fail "5 送れないとき終了コードが 0 でない"
fi

# 6. 引数が無いときは失敗で終わる
rc=0
bash "${SCRIPT}" >/dev/null 2>&1 || rc=$?
if [ "${rc}" -ne 0 ]; then
  pass "6 引数なしで終了コードが 0 でない (rc=${rc})"
else
  fail "6 引数なしで終了コードが 0 でない"
fi

# 7. 配置ルートが無いときは失敗で終わる
fresh
rc=0
out7="$(DRY_RUN=1 bash "${SCRIPT}" "${TMP}/repo" "${TMP}/no-such-dir" 2>&1)" || rc=$?
if [ "${rc}" -ne 0 ] && has "${out7}" "DEPLOY_ROOT not found" && ! has "${out7}" "monitoring_config_drift_files"; then
  pass "7 配置ルートが無いとき失敗し、値を出さない (rc=${rc})"
else
  fail "7 配置ルートが無いとき失敗し、値を出さない"
fi

if [ "${FAIL}" -ne 0 ]; then
  echo "RESULT: FAIL"
  exit 1
fi
echo "RESULT: ALL PASS"
