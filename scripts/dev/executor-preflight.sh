#!/usr/bin/env bash
# scripts/dev/executor-preflight.sh
# 実行役(Claude Code / Codex / 将来のエージェント)が作業開始前に必ず1回叩く preflight。
# 目的: 「gh無効」系で深い所で詰まる前に、ネット / gh認証 / git identity を数秒で切り分ける。
# 使い方(リポジトリ root で):
#   ./scripts/dev/executor-preflight.sh           # 確認＋安全な範囲で自動修復
#   ./scripts/dev/executor-preflight.sh --check    # 確認のみ(修復しない)
# タスク先頭で `./scripts/dev/executor-preflight.sh || exit 1` とすればゲートに使える。
# 終了コード: 全OK=0 / 失敗あり=1

set -uo pipefail

EXPECTED_USER="shingo-cc"
MODE="fix"; [ "${1:-}" = "--check" ] && MODE="check"

fail=0
ok()   { printf '  [OK]   %s\n' "$1"; }
warn() { printf '  [warn] %s\n' "$1"; }
bad()  { printf '  [FAIL] %s\n' "$1"; fail=1; }

echo "== executor preflight (identity=${EXPECTED_USER}, mode=${MODE}) =="

# 1) ネット到達(実行役サンドボックスの通信遮断を検知)
echo "[1/3] network -> api.github.com"
if curl -sf --max-time 8 -I https://api.github.com >/dev/null 2>&1; then
  ok "GitHub API 到達"
else
  bad "GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。"
  echo "       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)"
fi

# 2) gh 認証 = shingo-cc
echo "[2/3] gh auth = ${EXPECTED_USER}"
if gh auth status --active 2>&1 | grep -qF "account ${EXPECTED_USER}"; then
  ok "gh は ${EXPECTED_USER}"
elif [ "$MODE" = "fix" ]; then
  warn "gh の active account が ${EXPECTED_USER} でない。gh auth switch で切り替え試行..."
  if gh auth switch --hostname github.com --user "${EXPECTED_USER}" >/dev/null 2>&1; then
    if gh auth status --active 2>&1 | grep -qF "account ${EXPECTED_USER}"; then
      ok "gh auth switch 成功: gh は ${EXPECTED_USER}"
    else
      bad "gh auth switch 後も active account が ${EXPECTED_USER} にならず。gh auth status --active を確認。"
    fi
  else
    bad "gh auth switch --hostname github.com --user ${EXPECTED_USER} に失敗。gh auth status --active で現状を確認。"
  fi
else
  bad "gh が ${EXPECTED_USER} でない。対策: gh auth switch --hostname github.com --user ${EXPECTED_USER}"
fi

# 3) git identity = shingo-cc
echo "[3/3] git config user.name = ${EXPECTED_USER}"
git_user="$(git config user.name 2>/dev/null || true)"
if [ "$git_user" = "$EXPECTED_USER" ]; then
  ok "git user.name は ${EXPECTED_USER}"
elif [ "$MODE" = "fix" ]; then
  if git config user.name "$EXPECTED_USER" 2>/dev/null; then
    ok "git user.name を ${EXPECTED_USER} に設定"
  else
    bad "git user.name を設定できず(リポジトリ内で実行しているか確認)。"
  fi
else
  bad "git user.name が ${EXPECTED_USER} でない(現在: ${git_user:-未設定})。"
fi
[ -z "$(git config user.email 2>/dev/null || true)" ] && warn "git user.email 未設定。shingo-cc 対応アドレスを設定推奨。"

# 4) 長命ブランチ(main)の存在確認
echo "[4/4] long-lived branch -> origin/main"
remote_heads="$(git ls-remote --heads origin main 2>/dev/null || true)"
if printf '%s\n' "$remote_heads" | grep -q $'\trefs/heads/main'; then
  ok "origin/main は存在"
else
  bad "origin/main が欠落。main は消失させない運用に戻してから再実行。"
fi

echo "=============================================="
if [ "$fail" -eq 0 ]; then
  echo "PREFLIGHT OK — 作業続行可"
  exit 0
else
  echo "PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)"
  exit 1
fi
