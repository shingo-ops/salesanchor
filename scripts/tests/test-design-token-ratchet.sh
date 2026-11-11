#!/usr/bin/env bash
# check-design-token-ratchet.sh の試験（ADR-1074 の Google 色の例外を含む）
set -euo pipefail

GUARD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/check-design-token-ratchet.sh"
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT

NAMES=(surface surface-lowest surface-container surface-filled on-surface on-surface-variant outline-variant gridline primary on-primary secondary-container on-secondary-container now)

cd "${WORK}"
git init -q
git config user.email t@example.com
git config user.name t
mkdir -p frontend/src/pages
cat > frontend/src/index.css <<'CSS'
:root {
  --base-color: #111111;
}
:root.force-dark {
  --base-color: #eeeeee;
}
CSS
echo '.a { color: var(--base-color); }' > frontend/src/pages/a.css
git add -A
git commit -q -m base
BASE=$(git rev-parse HEAD)

fail=0

# 26 行（13 名前 x 明るい・暗い）を index.css に足す
add_palette() {
  {
    echo ':root {'
    for n in "${NAMES[@]}"; do echo "  --gcal-${n}: #a1b2c3;"; done
    echo '}'
    echo ':root.force-dark {'
    for n in "${NAMES[@]}"; do echo "  --gcal-${n}: #a1b2c3;"; done
    echo '}'
  } >> frontend/src/index.css
}

run_case() {
  local num="$1" expected="$2" head rc
  head=$(git rev-parse HEAD)
  rc=0
  BASE_SHA="${BASE}" HEAD_SHA="${head}" bash "${GUARD}" >/dev/null 2>&1 || rc=$?
  if [ "${rc}" = "${expected}" ]; then
    echo "ok 場合${num}"
  else
    echo "NG 場合${num} 期待${expected} 実際${rc}"
    fail=1
  fi
}

new_case() {
  git checkout -q -B "case$1" "${BASE}"
}

commit_case() {
  git add -A
  git commit -q -m "case"
}

# 場合1
new_case 1
add_palette
commit_case
run_case 1 0

# 場合2
new_case 2
printf ':root {\n  --gcal-extra: #123456;\n}\n' >> frontend/src/index.css
commit_case
run_case 2 1

# 場合3
new_case 3
printf ':root {\n  --gcal-surface: #ffffff; --x: #000000;\n}\n' >> frontend/src/index.css
commit_case
run_case 3 1

# 場合4
new_case 4
printf ':root {\n  --other-color: #222222;\n}\n' >> frontend/src/index.css
commit_case
run_case 4 1

# 場合5
new_case 5
echo '  --gcal-surface: #ffffff;' >> frontend/src/pages/a.css
commit_case
run_case 5 1

# 場合6
new_case 6
echo '.b { color: var(--base-color); }' >> frontend/src/pages/a.css
commit_case
run_case 6 0

# 場合7
new_case 7
add_palette
printf '.x {\n  --gcal-primary: #ff0000;\n}\n' >> frontend/src/index.css
commit_case
run_case 7 1

# 場合8
new_case 8
printf ':root {\n  --gcal-surface: #010101;\n  --gcal-surface: #020202;\n  --gcal-surface: #030303;\n}\n' >> frontend/src/index.css
commit_case
run_case 8 1

exit "${fail}"
