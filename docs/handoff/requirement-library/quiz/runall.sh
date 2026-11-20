#!/bin/bash
# 要件の練習問題を流す（クラウドの使い捨て環境で流す。手元の Mac では流さない）。
# usage: runall.sh OUT_DIR COPY_DIR [ROUNDS]
#   ROUNDS: 流す回の番号（既定 "1 2"）。回ごとに別の写しで並べて流してよい
#   OUT_DIR: 生出力の置き場（新しい空のディレクトリ）
#   COPY_DIR: 測る版の detached な写し（ここで AI を起動する）
D="$1"; W="$2"; RS="${3:-1 2}"
[ -n "$D" ] && [ -n "$W" ] || { echo "usage: runall.sh OUT_DIR COPY_DIR" >&2; exit 1; }
P="$(cd "$(dirname "$0")" && pwd)/prompts.tsv"
SUF="計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。"
cd "$W" || exit 1
for k in $RS; do
 while IFS=$'\t' read -r t p; do
  perl -e 'alarm 600; exec @ARGV' claude -p "${p}${SUF}" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 2 --no-session-persistence < /dev/null > "$D/$t-$k.jsonl" 2>"$D/$t-$k.err"
  echo "$t-$k exit=$?" >> "$D/exits.txt"
  s=$(git -C "$W" status --porcelain)
  if [ -n "$s" ]; then echo "DIRTY after $t-$k: $s" >> "$D/DIRTY.txt"; exit 2; fi
 done < "$P"
done
echo "ALLDONE $RS" >> "$D/exits.txt"
