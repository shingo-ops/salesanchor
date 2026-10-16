#!/usr/bin/env bash
# no-mac-vm-guard.sh の試験（一時 git リポジトリで ①〜⑩）
set -uo pipefail

GUARD="$(cd "$(dirname "$0")/../ci" && pwd)/no-mac-vm-guard.sh"
pass=0; fail=0

# run_case <番号> <期待exit> <パス> <追加する行> [既存行を先に置く]
run_case() {
  local id="$1" want="$2" path="$3" added="$4" existing="${5:-}"
  local d; d=$(mktemp -d)
  (
    cd "$d" || exit 99
    git init -q -b main . && git config user.email t@example.com && git config user.name t
    mkdir -p "$(dirname "$path")"
    if [ -n "$existing" ]; then printf '%s\n' "$existing" > "$path"; else echo base > "$path"; fi
    git add -A && git commit -qm base
    git checkout -q -b feat
    if [ -n "$existing" ]; then echo unrelated >> "$path"; else printf '%s\n' "$added" >> "$path"; fi
    git add -A && git commit -qm change
    bash "$GUARD" main >"$d/out.txt" 2>&1
  )
  local got=$?
  if [ "$got" = "$want" ]; then echo "PASS ${id} (exit=${got})"; pass=$((pass+1))
  else echo "FAIL ${id} want=${want} got=${got}"; cat "$d/out.txt"; fail=$((fail+1)); fi
  rm -rf "$d"
}

run_case 1 1 docs/a.md 'colima start --profile x'
run_case 2 1 docs/a.md 'colima start -p x'
run_case 3 1 docs/a.md 'colima start x'
run_case 4 0 docs/a.md 'colima start'
run_case 5 0 docs/a.md 'colima start -p default'
run_case 6 1 docs/a.md 'limactl start foo'
run_case 7 0 docs/a.md 'colima start --profile x # vm-guard-allow: Mac 実機でしか試せない'
run_case 8 1 docs/a.md 'colima start --profile x # vm-guard-allow:'
run_case 9 0 docs/handoff/vm-test-on-gha/x.md 'colima start --profile x'
run_case 10 0 docs/a.md '' 'colima start --profile x'

echo "pass=${pass} fail=${fail}"
[ "$fail" = 0 ]
