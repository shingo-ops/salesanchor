#!/usr/bin/env bash
# 監視用サーバー(prod2)に置いた監視設定と main のずれを数え、pushgateway に送る（ADR-1012 段階1 便7）
# 使い方: check_config_drift.sh REPO_ROOT DEPLOY_ROOT（REPO_ROOT は main の作業ツリー、DEPLOY_ROOT は prod2 の配置ルート）
# 環境変数: PUSHGATEWAY_URL（既定 http://127.0.0.1:9091）。DRY_RUN=1 なら送らずに送る本文を出す
# ログには件数とファイル名だけを出す（公開リポジトリの Actions のログに中身と sha256 を残さない）
set -euo pipefail

REPO_ROOT="${1:?usage: check_config_drift.sh REPO_ROOT DEPLOY_ROOT}"
DEPLOY_ROOT="${2:?usage: check_config_drift.sh REPO_ROOT DEPLOY_ROOT}"
PUSHGATEWAY_URL="${PUSHGATEWAY_URL:-http://127.0.0.1:9091}"

# 配置ルートが無い機体（prod2 以外）で動いたら、数えずに失敗で終わる
[ -d "${DEPLOY_ROOT}" ] || { echo "DEPLOY_ROOT not found: ${DEPLOY_ROOT}"; exit 1; }

# 比べる 6 本（prod2 の配置ルートからの相対パスは repo と同じ）。secrets・.env は入れない
FILES=(
  docker-compose.monitoring.yml
  monitoring/prometheus/prometheus.yml
  monitoring/prometheus/alert_rules.yml
  monitoring/loki/loki-config.yaml
  monitoring/loki/rules/jarvis/alerts.yml
  monitoring/alertmanager/alertmanager.yml
)

drift=0
for f in "${FILES[@]}"; do
  if [ ! -r "${REPO_ROOT}/${f}" ] || [ ! -r "${DEPLOY_ROOT}/${f}" ]; then
    echo "DRIFT (missing or unreadable): ${f}"
    drift=$((drift + 1))
    continue
  fi
  repo_sum=$(sha256sum "${REPO_ROOT}/${f}" | cut -d' ' -f1)
  deploy_sum=$(sha256sum "${DEPLOY_ROOT}/${f}" | cut -d' ' -f1)
  if [ "${repo_sum}" != "${deploy_sum}" ]; then
    echo "DRIFT: ${f}"
    drift=$((drift + 1))
  fi
done
echo "checked=${#FILES[@]} drift=${drift}"

body="# TYPE monitoring_config_drift_files gauge
monitoring_config_drift_files ${drift}
# TYPE monitoring_config_drift_last_run_timestamp gauge
monitoring_config_drift_last_run_timestamp $(date +%s)
"

if [ "${DRY_RUN:-0}" = "1" ]; then
  printf '%s' "${body}"
  exit 0
fi

printf '%s' "${body}" | curl -fsS --max-time 10 --data-binary @- \
  "${PUSHGATEWAY_URL}/metrics/job/monitoring_config_drift"
echo "pushed job=monitoring_config_drift"
