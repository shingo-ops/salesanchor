#!/bin/bash
# test-ledger-helpers.sh — 台帳窓口3本＋単票検証の単体テスト（砂場・本物の台帳に触れない）
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
export ACTIVE_WORK_FILE="${TMP}/active-work.md"
export ACTIVE_WORK_DIR="${TMP}/active-work.d"
mkdir -p "${ACTIVE_WORK_DIR}"
cat > "${ACTIVE_WORK_FILE}" << 'FIX'
## 現在進行中の作業
| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/honbun-a | テストA | 2026-07-05 | IN_PROGRESS | | | |
| release/honbun-b | テストB | 2026-07-05 | DONE | #1 | main | |
## 記入例
FIX
cat > "${ACTIVE_WORK_DIR}/feature-x-y.md" << 'FIX'
branch: feature/x-y
| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| feature/x-y | 分割側テスト | 2026-07-05 | IN_PROGRESS | | | |
FIX
cat > "${ACTIVE_WORK_DIR}/feature-a-b.md" << 'FIX'
branch: feature/a-b
| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| feature/a-b | 衝突テスト | 2026-07-05 | IN_PROGRESS | | | |
FIX
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
ng(){ echo "FAIL: $1"; FAIL=$((FAIL+1)); }
bash "${HERE}/ledger-lookup.sh" release/honbun-a | grep -q "release/honbun-a" && ok "T1 本体側lookup" || ng "T1 本体側lookup"
bash "${HERE}/ledger-lookup.sh" feature/x-y | grep -q "feature/x-y" && ok "T2 分割側lookup" || ng "T2 分割側lookup"
bash "${HERE}/ledger-lookup.sh" nope/nai > /dev/null 2>&1; [ $? -eq 1 ] && ok "T3 未登録=exit1" || ng "T3 未登録=exit1"
bash "${HERE}/ledger-lookup.sh" feature/a/b > /dev/null 2>&1; [ $? -eq 2 ] && ok "T4 衝突ガード=exit2" || ng "T4 衝突ガード=exit2"
bash "${HERE}/ledger-update.sh" feature/x-y --status DONE > /dev/null && grep -q "| DONE |" "${ACTIVE_WORK_DIR}/feature-x-y.md" && ok "T5 分割側の状態更新" || ng "T5 分割側の状態更新"
bash "${HERE}/ledger-update.sh" release/honbun-a --pr "#9999" > /dev/null && grep -q "#9999" "${ACTIVE_WORK_FILE}" && ok "T6 本体側のPR#更新" || ng "T6 本体側のPR#更新"
V="$(bash "${HERE}/ledger-view.sh")"
echo "${V}" | grep -q "release/honbun-b" && echo "${V}" | grep -q "feature/a-b" && [ "$(echo "${V}" | grep -c "ブランチ名")" -eq 1 ] && ok "T7 束ね表示" || ng "T7 束ね表示"
bash "${HERE}/check-active-work-format.sh" --dfile "${ACTIVE_WORK_DIR}/feature-x-y.md" > /dev/null && ok "T8 単票検証=正常" || ng "T8 単票検証=正常"
printf 'branch: feature/broken\n| feature/broken | 6列 | 2026-07-05 | IN_PROGRESS | | |\n' > "${ACTIVE_WORK_DIR}/feature-broken.md"
bash "${HERE}/check-active-work-format.sh" --dfile "${ACTIVE_WORK_DIR}/feature-broken.md" > /dev/null 2>&1; [ $? -eq 1 ] && ok "T9 単票検証=7列違反を検出" || ng "T9 単票検証=7列違反を検出"
echo "結果: PASS=${PASS} FAIL=${FAIL}"
[ "${FAIL}" -eq 0 ] && echo "ALL PASS" || exit 1
