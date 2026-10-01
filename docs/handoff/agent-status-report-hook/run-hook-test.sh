#!/usr/bin/env bash
# 見張りフックの実地テスト（POが1行で実行）。変更するのは /tmp/CC報告ファイル/ だけ。
# 3ケースをそれぞれ新しい claude -p で実行し、フックのログと結果を表示する。
# 実行: [CASES=b] bash docs/handoff/agent-status-report-hook/run-hook-test.sh
set -u
WT="/Users/tanizawashingo/worktrees/salesanchor/release-agent-status-report-hook"
OUT="/tmp/CC報告ファイル"
mkdir -p "$OUT"; cd "$WT" || exit 1
# CASES=b のように指定すると、そのケースだけ実行（既定: abc）
CASES="${CASES:-abc}"
rm -f "$OUT"/hook-test.log "$OUT"/hook-count-*
# macOS には timeout が無い。gtimeout があれば使い、無ければ時間制限なし（--max-budget-usd に頼る）
TMO=""; command -v timeout >/dev/null && TMO="timeout 300"; [ -z "$TMO" ] && command -v gtimeout >/dev/null && TMO="gtimeout 300"
if ! claude auth status 2>/dev/null | grep -q '"loggedIn": true'; then
  echo "claude にログインしていません。先に実行: claude auth login （通常のターミナルで）"; exit 1
fi
run() { # $1=ケース名 $2=指示
  echo "===== CASE $1 ====="
  echo "--- log行数(前): $( [ -f "$OUT/hook-test.log" ] && wc -l < "$OUT/hook-test.log" || echo 0 )"
  $TMO claude -p "$2" --permission-mode default --allowedTools "Agent" \
    --max-budget-usd 1 --output-format json > "$OUT/hook-test-$1.json" 2> "$OUT/hook-test-$1.err"
  echo "exit=$?"; cat "$OUT/hook-test-$1.json" | head -c 2500; echo
  echo "--- stderr:"; head -c 800 "$OUT/hook-test-$1.err"; echo
}
[[ "$CASES" == *a* ]] && run a "Agentツールで名前なしのサブエージェントを1つ起動し、その指示は『Waiting for CI. とだけ返答せよ』とする。サブエージェントが最終的に返した文面をそのまま報告せよ。"
[[ "$CASES" == *b* ]] && run b "Agentツールで名前なしのサブエージェントを1つ起動し、その指示は『次の1行をそのまま返答せよ: DONE: ok』とする。サブエージェントが最終的に返した文面をそのまま報告せよ。"
[[ "$CASES" == *c* ]] && run c "Agentツールで name パラメータに named-test を付けたサブエージェントを1つ起動し、その指示は『Waiting for CI. とだけ返答せよ』とする。サブエージェントが最終的に返した文面をそのまま報告せよ。"
echo "===== フックのログ全文 ($OUT/hook-test.log) ====="
cat "$OUT/hook-test.log" 2>/dev/null || echo "(ログなし = フックが一度も呼ばれていない)"
