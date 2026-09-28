#!/bin/bash
# test-merge-safe-guard.sh — gh-pr-merge-safe.sh の鍵ファイル（.pr-number）ガードのペアテスト
#
# 検証項目:
#   [欠落版] .pr-number が無い worktree では中断する（exit≠0）
#   [空版]   .pr-number が空の場合も中断する（exit≠0）
#   [helper拒否版] helper非0ではcleanupを呼ばない
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

run_wrapper() {
  ( cd "${SANDBOX}" && bash "${WRAPPER}" --merge 2>&1 )
}

rm -f "${SANDBOX}/.pr-number"
OUT_MISSING="$(run_wrapper)"; RC_MISSING=$?
if [ "${RC_MISSING}" -ne 0 ] && echo "${OUT_MISSING}" | grep -q "見つかりません"; then
  ok "欠落版: .pr-number 無しで中断する"
else
  ng "欠落版: 中断しなかった rc=${RC_MISSING}"
fi

OUT_CI="$(cd "${SANDBOX}" && GITHUB_ACTIONS=true bash "${WRAPPER}" --merge 2>&1)"; RC_CI=$?
if [ "${RC_CI}" -ne 0 ] && echo "${OUT_CI}" | grep -q "見つかりません"; then
  ok "CI環境名あり: 成功skipせず鍵欠落で中断する"
else
  ng "CI環境名あり: 鍵検査をskipした rc=${RC_CI}"
fi

: > "${SANDBOX}/.pr-number"
OUT_EMPTY="$(run_wrapper)"; RC_EMPTY=$?
if [ "${RC_EMPTY}" -ne 0 ] && echo "${OUT_EMPTY}" | grep -q "空です"; then
  ok "空版: .pr-number が空で中断する"
else
  ng "空版: 中断しなかった rc=${RC_EMPTY}"
fi

echo "9999" > "${SANDBOX}/.pr-number"
mkdir -p "${SANDBOX}/scripts"
cat > "${SANDBOX}/scripts/cleanup-worktree.sh" <<EOF
#!/bin/sh
echo cleanup >> "${TMP}/cleanup.log"
EOF
chmod +x "${SANDBOX}/scripts/cleanup-worktree.sh"
OUT_HELPER="$(run_wrapper)"; RC_HELPER=$?
if [ "${RC_HELPER}" -ne 0 ] && echo "${OUT_HELPER}" | grep -q "PR所有権確認"; then
  ok "helper拒否版: 所有権確認後に非0で停止する"
else
  ng "helper拒否版: 期待した停止にならない rc=${RC_HELPER}"
fi
if [ ! -e "${TMP}/cleanup.log" ]; then
  ok "helper拒否版: cleanup呼出0"
else
  ng "helper拒否版: cleanupが呼ばれた"
fi

echo ""
echo "結果: PASS=${PASS} FAIL=${FAIL}"
if [ "${FAIL}" -eq 0 ]; then echo "ALL PASS"; exit 0; else exit 1; fi
