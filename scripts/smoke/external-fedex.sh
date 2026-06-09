#!/usr/bin/env bash
# =============================================================================
# ADR-124: External State Verification — L2 Smoke: FedEx Rates API
#
# 目的:
#   FedEx Rates and Transit Times API の疎通確認（ADR-124 D2 第1段完了条件）。
#   sandbox / live の 2 mode に対応。
#
# Mode:
#   --dry-run    設定だけ表示、API コール不要
#   --sandbox    (default) FedEx サンドボックス API で OAuth + Rates 疎通確認
#   --live       本番バックエンド経由で見積もり1件取得。PO_LIVE_OK=yes 必須
#
# 必須環境変数:
#   --sandbox mode:
#     FEDEX_SANDBOX_CLIENT_ID       FedEx Developer sandbox client_id
#     FEDEX_SANDBOX_CLIENT_SECRET   FedEx Developer sandbox client_secret
#     FEDEX_SANDBOX_ACCOUNT_NUMBER  FedEx sandbox account number
#
#   --live mode:
#     SALESANCHOR_API_URL   本番 API の base URL (例: https://api.salesanchor.jp)
#     SALESANCHOR_API_TOKEN Bearer token（Service Account or test tenant）
#     FEDEX_SMOKE_TENANT_ID テナント ID（FedEx 連携済み）
#     PO_LIVE_OK=yes
#
# 使い方:
#   bash scripts/smoke/external-fedex.sh [--dry-run|--sandbox|--live]
#
# 関連:
#   docs/adr/ADR-124-fedex-rates-stage1.md
#   backend/app/services/fedex_rates.py
#   scripts/smoke_test_post_deploy.sh ([8a],[8b])
# =============================================================================
set -euo pipefail

MODE="${1:---sandbox}"

FEDEX_SANDBOX_TOKEN_URL="https://apis-sandbox.fedex.com/oauth/token"
FEDEX_SANDBOX_RATES_URL="https://apis-sandbox.fedex.com/rate/v1/rates/quotes"

log() {
    echo "[smoke/fedex] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >&2
}

require_env() {
    local var="$1"
    if [[ -z "${!var:-}" ]]; then
        log "ERROR: required env var '${var}' is not set"
        exit 1
    fi
}

case "$MODE" in
  --dry-run)
    log "MODE: dry-run"
    for v in FEDEX_SANDBOX_CLIENT_ID FEDEX_SANDBOX_CLIENT_SECRET FEDEX_SANDBOX_ACCOUNT_NUMBER; do
        if [[ -n "${!v:-}" ]]; then
            log "${v}=(set, length=${#!v})"
        else
            log "${v}=(not set)"
        fi
    done
    log "dry-run: no API calls made"
    echo "PASS: dry-run complete"
    ;;

  --sandbox)
    log "MODE: sandbox"
    require_env FEDEX_SANDBOX_CLIENT_ID
    require_env FEDEX_SANDBOX_CLIENT_SECRET
    require_env FEDEX_SANDBOX_ACCOUNT_NUMBER

    # Step 1: OAuth token 取得
    log "Obtaining FedEx sandbox OAuth token..."
    TOKEN_RESP=$(curl -fsS -X POST "${FEDEX_SANDBOX_TOKEN_URL}" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=client_credentials" \
        -d "client_id=${FEDEX_SANDBOX_CLIENT_ID}" \
        -d "client_secret=${FEDEX_SANDBOX_CLIENT_SECRET}") \
        || { log "ERROR: OAuth token request failed"; exit 1; }

    ACCESS_TOKEN=$(echo "${TOKEN_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) \
        || { log "ERROR: Could not parse access_token from response"; exit 1; }
    TOKEN_TYPE=$(echo "${TOKEN_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token_type','bearer'))" 2>/dev/null || echo "bearer")
    log "OAuth token obtained (type=${TOKEN_TYPE})"

    # Step 2: Rates quotes リクエスト（JP→US, 1kg テスト荷物）
    log "Requesting rates quote JP→US 1.0kg..."
    RATES_RESP=$(curl -fsS -X POST "${FEDEX_SANDBOX_RATES_URL}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "X-locale: en_US" \
        -d "{
          \"accountNumber\": {\"value\": \"${FEDEX_SANDBOX_ACCOUNT_NUMBER}\"},
          \"requestedShipment\": {
            \"shipper\": {
              \"address\": {\"countryCode\": \"JP\", \"postalCode\": \"1000001\", \"residential\": false}
            },
            \"recipient\": {
              \"address\": {\"countryCode\": \"US\", \"postalCode\": \"90210\", \"residential\": false}
            },
            \"pickupType\": \"DROPOFF_AT_FEDEX_LOCATION\",
            \"rateRequestType\": [\"LIST\"],
            \"requestedPackageLineItems\": [{
              \"weight\": {\"units\": \"KG\", \"value\": 1.0}
            }]
          }
        }") \
        || { log "ERROR: Rates API request failed"; exit 1; }

    # Step 3: レスポンス検証
    QUOTE_COUNT=$(echo "${RATES_RESP}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
quotes = d.get('output', {}).get('rateReplyDetails', [])
print(len(quotes))
" 2>/dev/null || echo "0")

    if [[ "${QUOTE_COUNT}" -gt 0 ]]; then
        log "Rates quotes received: ${QUOTE_COUNT} service(s)"
        echo "PASS: sandbox smoke OK (quotes=${QUOTE_COUNT})"
    else
        log "ERROR: No quotes returned from FedEx sandbox API"
        log "Response: $(echo "${RATES_RESP}" | python3 -c 'import sys; print(sys.stdin.read()[:500])' 2>/dev/null || echo '<parse error>')"
        exit 1
    fi
    ;;

  --live)
    if [[ "${PO_LIVE_OK:-}" != "yes" ]]; then
        log "ERROR: live mode requires PO_LIVE_OK=yes"
        exit 1
    fi
    log "MODE: live"
    require_env SALESANCHOR_API_URL
    require_env SALESANCHOR_API_TOKEN

    # バックエンド経由で見積もり取得（FedEx 連携済みテナントが必要）
    log "Calling /shipping/calculate via backend (FedEx live)..."
    CALC_RESP=$(curl -fsS -X POST "${SALESANCHOR_API_URL}/api/shipping/calculate" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${SALESANCHOR_API_TOKEN}" \
        -d "{
          \"country_code\": \"US\",
          \"weight_kg\": 1.0,
          \"carrier\": \"fedex\",
          \"origin_country_code\": \"JP\"
        }") \
        || { log "ERROR: backend /shipping/calculate request failed"; exit 1; }

    SOURCE=$(echo "${CALC_RESP}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
results = d.get('results', [])
live = [r for r in results if r.get('source') == 'fedex_live']
print('live' if live else 'no_live')
" 2>/dev/null || echo "parse_error")

    LIVE_ERROR=$(echo "${CALC_RESP}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('live_error') or '')
" 2>/dev/null || echo "")

    if [[ "${SOURCE}" == "live" ]]; then
        QUOTE_COUNT=$(echo "${CALC_RESP}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len([r for r in d.get('results', []) if r.get('source') == 'fedex_live']))
" 2>/dev/null || echo "0")
        log "FedEx live quotes received: ${QUOTE_COUNT} service(s)"
        echo "PASS: live smoke OK (fedex_live quotes=${QUOTE_COUNT})"
    else
        if [[ -n "${LIVE_ERROR}" ]]; then
            log "ERROR: live_error returned — FedEx API not healthy: ${LIVE_ERROR}"
        else
            log "ERROR: No fedex_live results in response"
        fi
        log "Response snippet: $(echo "${CALC_RESP}" | python3 -c 'import sys; print(sys.stdin.read()[:500])' 2>/dev/null || echo '<parse error>')"
        exit 1
    fi
    ;;

  *)
    log "ERROR: unknown mode '${MODE}'. Use --dry-run, --sandbox, or --live"
    exit 1
    ;;
esac
