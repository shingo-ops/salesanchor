#!/bin/bash
# usage: runall.sh  (T1-1 already done)
D=/tmp/CC報告ファイル/an-stage1/k12/run
W=/Users/tanizawashingo/worktrees/salesanchor/k12-measure
SUF="計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。"
cd /Users/tanizawashingo/worktrees/salesanchor/k12-measure || exit 1
for k in 1 2; do
 while IFS=$'\t' read -r t p; do
  [ "$t" = T1 ] && [ $k = 1 ] && continue
  perl -e 'alarm 600; exec @ARGV' claude -p "${p}${SUF}" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none > $D/$t-$k.jsonl 2>$D/$t-$k.err
  echo "$t-$k exit=$?" >> $D/exits.txt
  s=$(git -C $W status --porcelain)
  if [ -n "$s" ]; then echo "DIRTY after $t-$k: $s" >> $D/DIRTY.txt; exit 2; fi
 done < $D/prompts.tsv
done
echo ALLDONE >> $D/exits.txt
