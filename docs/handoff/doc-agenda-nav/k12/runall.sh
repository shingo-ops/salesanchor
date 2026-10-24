#!/bin/bash
# usage: runall.sh OUT_DIR COPY_DIR
#   OUT_DIR: 生出力の置き場（新しい空のディレクトリ）
#   COPY_DIR: 測る版の detached な写し
D="$1"; W="$2"
[ -n "$D" ] && [ -n "$W" ] || { echo "usage: runall.sh OUT_DIR COPY_DIR" >&2; exit 1; }
P="$(cd "$(dirname "$0")" && pwd)/prompts.tsv"
SUF="計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。"
cd "$W" || exit 1
for k in 1 2; do
 while IFS=$'\t' read -r t p; do
  perl -e 'alarm 600; exec @ARGV' claude -p "${p}${SUF}" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none < /dev/null > "$D/$t-$k.jsonl" 2>"$D/$t-$k.err"
  echo "$t-$k exit=$?" >> "$D/exits.txt"
  s=$(git -C "$W" status --porcelain)
  if [ -n "$s" ]; then echo "DIRTY after $t-$k: $s" >> "$D/DIRTY.txt"; exit 2; fi
 done < "$P"
done
echo ALLDONE >> "$D/exits.txt"
