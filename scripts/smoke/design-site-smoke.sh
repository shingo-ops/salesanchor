#!/usr/bin/env bash
# SA設計図書サイト smoke テスト（ADR-134）
# 実行環境: GitHub Actions Verify deployment ステップ内
#
# smoke①: 認証なし → 401
# smoke②: 認証あり → 200
# smoke③: progress.json → 200 + valid JSON with generated_at
# smoke④: /api/health + /grafana/api/health → 200（既存経路確認）
# smoke⑤: スラッシュなし → 301
#
# 環境変数:
#   DESIGN_SMOKE_CRED  - "user:password" 形式（DESIGN_SITE_SMOKE_CRED Secret から）
#   BASE_URL           - デフォルト: https://app.salesanchor.jp
set -euo pipefail

BASE_URL="${BASE_URL:-https://app.salesanchor.jp}"
PASS=0
FAIL=0

check() {
  local desc="$1"
  local expected="$2"
  local actual="$3"
  if [ "${actual}" = "${expected}" ]; then
    echo "✅ ${desc}: ${actual}"
    PASS=$((PASS + 1))
  else
    echo "❌ ${desc}: expected=${expected} got=${actual}"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== SA設計図書サイト smoke ==="

# smoke①: 認証なし → 401
_code=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 10 "${BASE_URL}/design/" 2>/dev/null || echo "FAIL")
check "smoke① 認証なし=401" "401" "${_code}"

# smoke⑤: 末尾スラッシュなし → 301（SPA catch-all 落下防止確認）
_code=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 10 "${BASE_URL}/design" 2>/dev/null || echo "FAIL")
check "smoke⑤ スラッシュなし=301" "301" "${_code}"

# smoke②③: DESIGN_SMOKE_CRED が設定済みの場合のみ実行
if [ -n "${DESIGN_SMOKE_CRED:-}" ]; then
  # smoke②: 認証あり → 200
  _code=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${DESIGN_SMOKE_CRED}" \
    --max-time 10 "${BASE_URL}/design/" 2>/dev/null || echo "FAIL")
  check "smoke② 認証あり=200" "200" "${_code}"

  # smoke③: progress.json → 200 + valid JSON with generated_at
  _body=$(curl -s -u "${DESIGN_SMOKE_CRED}" \
    --max-time 10 "${BASE_URL}/design/progress.json" 2>/dev/null || echo "FAIL")
  _json_check=$(echo "${_body}" | python3 -c "
import sys, json
try:
  d = json.load(sys.stdin)
  assert 'generated_at' in d, 'missing generated_at'
  assert d.get('item_count', 0) > 0, 'item_count=0'
  print('OK')
except Exception as e:
  print(f'FAIL:{e}')
" 2>/dev/null || echo "FAIL:parse_error")
  check "smoke③ progress.json valid" "OK" "${_json_check}"
else
  echo "⚠️  DESIGN_SMOKE_CRED 未設定 — smoke②③ スキップ"
fi

# smoke④: 既存経路確認（/api/health + /grafana/api/health）
_api=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 10 "${BASE_URL}/api/health" 2>/dev/null || echo "FAIL")
check "smoke④ /api/health=200" "200" "${_api}"

_grafana=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 10 "${BASE_URL}/grafana/api/health" 2>/dev/null || echo "FAIL")
check "smoke④ /grafana/api/health=200" "200" "${_grafana}"

echo "=== 結果: PASS=${PASS} FAIL=${FAIL} ==="
if [ "${FAIL}" -gt 0 ]; then
  exit 1
fi
