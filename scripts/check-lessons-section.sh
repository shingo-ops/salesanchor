#!/usr/bin/env bash
# design-partner.md の教訓ゾーン(§6開始〜§7開始の手前)への箇条書き追加を数える。
# 出力: SEC6_START / SEC7_START / SEC6_ADDED
# 用途: .github/workflows/lessons-guard.yml から呼ばれ、直書き検知に使う。
set -uo pipefail
BASE_REF="${1:?base ref required}"
FILE="docs/ai-agents/design-partner.md"

SEC6_START=$(grep -n '^## 6\.' "$FILE" | head -1 | cut -d: -f1)
SEC7_START=$(grep -n '^## 7\.' "$FILE" | head -1 | cut -d: -f1)

if [ -z "${SEC6_START:-}" ]; then
  echo "SEC6_START=NOT_FOUND"
  echo "SEC6_ADDED=0"
  exit 0
fi
if [ -z "${SEC7_START:-}" ]; then
  SEC7_START=$(wc -l < "$FILE")
  SEC7_START=$((SEC7_START + 1))
fi

COUNT=$(git diff --unified=0 "${BASE_REF}...HEAD" -- "$FILE" | awk -v start="$SEC6_START" -v stop="$SEC7_START" '
/^\+\+\+/ { next }
/^@@/ {
  split($3, p, ",")
  ln = p[1]
  sub(/^\+/, "", ln)
  ln = ln + 0
  next
}
/^\+/ {
  if ($0 ~ /^\+- / && ln >= start && ln < stop) n++
  ln++
  next
}
END { print n+0 }
')
echo "SEC6_START=${SEC6_START}"
echo "SEC7_START=${SEC7_START}"
echo "SEC6_ADDED=${COUNT}"
