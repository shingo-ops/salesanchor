#!/usr/bin/env bash
# 正本ドキュメントの節番号重複検査（並行便の番号衝突を関所で止める）
# 使い方: bash scripts/check-doc-heading-duplicates.sh [file...]
# 引数なしの場合は既定の正本リストを検査する。
set -u
FILES=("$@")
if [ ${#FILES[@]} -eq 0 ]; then
  FILES=(docs/STANDARD-WORKFLOW.md docs/ai-agents/design-partner.md)
fi
rc=0
for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "SKIP(not found): $f"; continue; }
  # 見出し行から番号トークンを抽出（#の数=見出しレベルは不問。1 / 1.5 / 1.7 等）
  dups=$(grep -nE '^#{1,6}[[:space:]]+[0-9]+(\.[0-9]+)*[.)]?([[:space:]]|$)' "$f" \
    | sed -E 's/^([0-9]+):#{1,6}[[:space:]]+([0-9]+(\.[0-9]+)*).*/\2 L\1/' \
    | sort | awk '{n[$1]=n[$1]" "$2; c[$1]++} END{for(k in c) if(c[k]>1) print k":"n[k]}')
  if [ -n "$dups" ]; then
    echo "FAIL: $f に重複する節番号があります:"
    echo "$dups" | sed 's/^/  節番号 /'
    rc=1
  else
    echo "PASS: $f 節番号の重複なし"
  fi
done
exit $rc
