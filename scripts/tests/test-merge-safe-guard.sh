#!/bin/bash
# test-merge-safe-guard.sh — gh-pr-merge-safe.sh の鍵ファイル（.pr-number）ガードのペアテスト
#
# 検証項目:
#   [欠落版] .pr-number が無い worktree では中断する（exit≠0）
#   [空版]   .pr-number が空の場合も中断する（exit≠0）
#   [充足版] .pr-number が在る場合はガードを通過し後続処理へ進む
#
# 実行方法: bash scripts/tests/test-merge-safe-guard.sh
# 終了コード: 0=全PASS / 1=FAILあり
set -u

HERE="$(cd "$(dirname "$0")/.." && pwd)"
WRAPPER="${HERE}/gh-pr-merge-safe.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT

PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
ng(){ echo "FAIL: $1"; FAIL=$((FAIL+1)); }

SANDBOX="${TMP}/sandbox"
mkdir -p "${SANDBOX}"
git init "${SANDBOX}" -q
git -C "${SANDBOX}" config user.email "test@example.com"
git -C "${SANDBOX}" config user.name "test"
echo "x" > "${SANDBOX}/a.txt"
git -C "${SANDBOX}" add a.txt
git -C "${SANDBOX}" commit -q -m "init"

MOCK_BIN="${TMP}/mock-bin"
mkdir -p "${MOCK_BIN}"
cat > "${MOCK_BIN}/gh" << 'GHEOF'
#!/bin/bash
if [[ "$*" == *"pr merge"* ]]; then
  echo "MOCK_GH_MERGE_CALLED"
  exit 0
fi
echo ""
exit 0
GHEOF
chmod +x "${MOCK_BIN}/gh"

run_wrapper() {
  ( cd "${SANDBOX}" && PATH="${MOCK_BIN}:${PATH}" bash "${WRAPPER}" --merge 2>&1 )
}

rm -f "${SANDBOX}/.pr-number"
OUT_MISSING="$(run_wrapper)"; RC_MISSING=$?
if [ "${RC_MISSING}" -ne 0 ] && echo "${OUT_MISSING}" | grep -q "見つかりません"; then
  ok "欠落版: .pr-number 無しで中断する"
else
  ng "欠落版: 中断しなかった rc=${RC_MISSING}"
fi

: > "${SANDBOX}/.pr-number"
OUT_EMPTY="$(run_wrapper)"; RC_EMPTY=$?
if [ "${RC_EMPTY}" -ne 0 ] && echo "${OUT_EMPTY}" | grep -q "空です"; then
  ok "空版: .pr-number が空で中断する"
else
  ng "空版: 中断しなかった rc=${RC_EMPTY}"
fi

echo "9999" > "${SANDBOX}/.pr-number"
OUT_OK="$(run_wrapper)"
if echo "${OUT_OK}" | grep -q "PR所有権確認"; then
  ok "充足版: ガードを通過して後続へ進む"
else
  ng "充足版: 通過しなかった"
fi

# ── BEHIND検出テスト: RULE_WAITに入っても待機せず追従へ戻る ──────────────
BEHIND_MOCK="${TMP}/mock-behind"
mkdir -p "${BEHIND_MOCK}"
cat > "${BEHIND_MOCK}/gh" << 'GHEOF'
#!/bin/bash
if [[ "$*" == *"pr merge"* ]]; then
  echo "X Pull request is not mergeable: rule violations found"
  exit 1
fi
if [[ "$*" == *"mergeStateStatus"* ]]; then
  echo "BEHIND"
  exit 0
fi
echo ""
exit 0
GHEOF
chmod +x "${BEHIND_MOCK}/gh"
echo "9999" > "${SANDBOX}/.pr-number"
OUT_BEHIND="$( cd "${SANDBOX}" && PATH="${BEHIND_MOCK}:${PATH}" bash "${WRAPPER}" --merge 2>&1 )"
if echo "${OUT_BEHIND}" | grep -q "BEHIND を検出"; then
  ok "BEHIND検出: 待機せず追従フローへ戻る"
else
  ng "BEHIND検出: 専用メッセージ無し"
fi

echo ""
echo "結果: PASS=${PASS} FAIL=${FAIL}"
if [ "${FAIL}" -eq 0 ]; then echo "ALL PASS"; exit 0; else exit 1; fi
