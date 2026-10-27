#!/bin/bash
# usage: diag.sh OUT_DIR COPY_DIR SUFFIX_FILE
#   OUT_DIR: 生出力の置き場（新しい空のディレクトリ）
#   COPY_DIR: 測る版の detached な写し
#   SUFFIX_FILE: 題の後ろに付ける文（1行）
# 各題を1回ずつ解かせる。写しの git status が開始時と同じであることを各回の後に確かめる
D="$1"; W="$2"; S="$3"
[ -n "$D" ] && [ -n "$W" ] && [ -f "$S" ] || { echo "usage: diag.sh OUT_DIR COPY_DIR SUFFIX_FILE" >&2; exit 1; }
P="$(cd "$(dirname "$0")" && pwd)/prompts.tsv"
SUF="$(cat "$S")"
cd "$W" || exit 1
s0=$(git -C "$W" status --porcelain)
while IFS=$'\t' read -r t p; do
 perl -e 'alarm 600; exec @ARGV' claude -p "${p}${SUF}" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none < /dev/null > "$D/$t-1.jsonl" 2>"$D/$t-1.err"
 echo "$t-1 exit=$?" >> "$D/exits.txt"
 s=$(git -C "$W" status --porcelain)
 if [ "$s" != "$s0" ]; then echo "DIRTY after $t-1: $s" >> "$D/DIRTY.txt"; exit 2; fi
done < "$P"
echo ALLDONE >> "$D/exits.txt"
