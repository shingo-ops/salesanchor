#!/usr/bin/env bash
# no-mac-vm-guard: 新しく足した行（git diff の追加行）に「Mac で一時的な仮想マシンを作る命令」があれば止める。
#   - colima start|create の profile が default 以外
#   - limactl start|create
# 通す: 同じ行に `vm-guard-allow: <理由>`（理由は空でない）
# 規則の正本: docs/ops/runner-commands.md「仮想マシンが要る試験（GitHub で行う）」
# 使い方: bash scripts/ci/no-mac-vm-guard.sh [比較元 既定 origin/main]
set -uo pipefail

BASE="${1:-origin/main}"
EXCLUDES=(
  "docs/specs/vm-test-on-gha/"
  "docs/handoff/vm-test-on-gha/"
  "scripts/ci/no-mac-vm-guard.sh"
  "scripts/tests/test-no-mac-vm-guard.sh"
)

is_excluded() {
  local f="$1" e
  for e in "${EXCLUDES[@]}"; do
    case "$f" in "$e"*) return 0 ;; esac
  done
  return 1
}

# colima start|create の後ろの引数から profile 名を求める（無ければ default）
colima_profile() {
  local rest="$1" tok prev="" skip=0 profile=""
  rest="${rest%%[;&|\`)#]*}"
  rest="${rest//\"/}"
  rest="${rest//\'/}"
  for tok in $rest; do
    if [ "$skip" = 1 ]; then skip=0; continue; fi
    if [ "$prev" = "p" ]; then profile="$tok"; break; fi
    case "$tok" in
      --profile=*) profile="${tok#--profile=}"; break ;;
      --profile|-p) prev="p"; continue ;;
      -c|--cpu|-m|--memory|-d|--disk|-r|--runtime|-a|--arch|-t|--vm-type|--mount|--mount-type|--network-address|--dns|--dns-host|--env|--kubernetes-version|--ssh-agent|--cpu-type|--hostname|--edit-editor|--activate|--vz-rosetta|--nested-virtualization)
        skip=1; continue ;;
      -*) continue ;;
      *) profile="$tok"; break ;;
    esac
  done
  printf '%s' "${profile:-default}"
}

hits=0
file=""
newline=0
skipfile=0

while IFS= read -r line; do
  case "$line" in
    "+++ b/"*)
      file="${line#+++ b/}"
      if is_excluded "$file"; then skipfile=1; else skipfile=0; fi
      continue ;;
    "+++ "*) file=""; skipfile=1; continue ;;
    "--- "*) continue ;;
    "@@ "*)
      hdr="${line#*+}"; hdr="${hdr%% *}"
      newline="${hdr%%,*}"
      continue ;;
    "+"*)
      content="${line#+}"
      cur=$newline
      newline=$((newline + 1))
      [ "$skipfile" = 1 ] && continue
      ;;
    *) continue ;;
  esac

  hit=""
  if [[ "$content" =~ colima[[:space:]]+(start|create)([[:space:]].*)?$ ]]; then
    p=$(colima_profile "${BASH_REMATCH[2]}")
    [ "$p" != "default" ] && hit="colima profile=${p}"
  fi
  if [ -z "$hit" ] && [[ "$content" =~ limactl[[:space:]]+(start|create) ]]; then
    hit="limactl"
  fi
  [ -z "$hit" ] && continue

  if [[ "$content" =~ vm-guard-allow:[[:space:]]*[^[:space:]] ]]; then
    continue
  fi
  echo "${file}:${cur}: ${content}"
  hits=$((hits + 1))
done < <(git diff --unified=0 --no-color "${BASE}...HEAD")

if [ "$hits" -gt 0 ]; then
  echo "no-mac-vm-guard: ${hits} 件。Mac で一時的な仮想マシンを作らず sandbox-test を使う（docs/ops/runner-commands.md）。Mac 実機でしか試せない場合のみ同じ行に 'vm-guard-allow: 理由' を付ける。"
  exit 1
fi
echo "no-mac-vm-guard: OK"
exit 0
