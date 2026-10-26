#!/bin/bash
# weekly-check.sh — confidential-quote-guard の週の点検 (design.md 維持の仕組み)。
# agent-console の定期実行から流す。出力は件数と日付だけ（語句は出さない）。0 でないものは知らせる。
#   1. 原本 (origin/main の guard.py と fetch_corpus.py) と写したもの (~/.claude/scripts) の diff 行数
#   2. 一般語の表の行数と、その週に足した行数
#   3. 商品名の写しの日付 (7 日より古ければ取り直す)
#   4. 原文の写し (本番から毎日取り直す) の日付 (2 日より古ければ知らせる)
#   5. 原文の写しの件数が前回より減っていないか
set -u
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
KEEP="${CONFID_KEEP_DIR:-$HOME/CC報告ファイル-keep}"
D="${CONFID_GUARD_DIR:-$KEEP/confid-guard}"
REPO="${CONFID_REPO:-$HOME/salesanchor}"
INST="$CLAUDE_DIR/scripts/confidential-quote-guard/guard.py"
REL="scripts/agent-hooks/confidential-quote-guard/guard.py"
bad=0

[ -f "$INST" ] || { echo "0 写しが無い: $INST"; bad=1; }
d1="$(git -C "$REPO" show "origin/main:$REL" 2>/dev/null | diff - "$INST" 2>/dev/null | wc -l | tr -d ' ')"
INSTF="$CLAUDE_DIR/scripts/confidential-quote-guard/fetch_corpus.py"
RELF="scripts/agent-hooks/confidential-quote-guard/fetch_corpus.py"
[ -f "$INSTF" ] || { echo "0 写しが無い: $INSTF"; bad=1; }
d1f="$(git -C "$REPO" show "origin/main:$RELF" 2>/dev/null | diff - "$INSTF" 2>/dev/null | wc -l | tr -d ' ')"
echo "1 原本と写しの差分行数: guard.py $d1 / fetch_corpus.py $d1f"; { [ "$d1" != "0" ] || [ "$d1f" != "0" ]; } && bad=1

n="$(grep -vc '^\s*#\|^\s*$' "$D/confidential-allow.txt" 2>/dev/null || true)"; n="${n:-0}"
w="$(find "$D/confidential-allow.txt" -mtime -7 2>/dev/null | wc -l | tr -d ' ')"
echo "2 一般語の表の行数: $n (今週更新: $([ "$w" = "1" ] && echo あり || echo なし))"

b="$(sed -n 's/^# built: //p' "$D/product-names.txt" 2>/dev/null | head -1)"
if [ -n "$b" ]; then
  age=$(( ( $(date +%s) - $(date -j -f %Y-%m-%d "$b" +%s 2>/dev/null || echo 0) ) / 86400 ))
else age=-1; fi
echo "3 商品名の写しの日付: ${b:-不明} (${age} 日前)"; { [ "$age" -lt 0 ] || [ "$age" -gt 7 ]; } && bad=1

# 4. 原文の写し (本番から毎日取り直す fetch_corpus.py の結果)。日付は 2 日以内、件数は前回より減っていないこと
M="$D/source-messages.meta"
fe="$(sed -n 's/^fetched_epoch=//p' "$M" 2>/dev/null | head -1)"
if [ -n "$fe" ]; then age4=$(( ( $(date +%s) - fe ) / 86400 )); else age4=-1; fi
echo "4 原文の写しの日付: $(sed -n 's/^fetched_at=//p' "$M" 2>/dev/null | head -1) (${age4} 日前)"
{ [ "$age4" -lt 0 ] || [ "$age4" -gt 2 ]; } && bad=1
rows="$(sed -n 's/^rows=//p' "$M" 2>/dev/null | head -1)"; prev="$(sed -n 's/^prev_rows=//p' "$M" 2>/dev/null | head -1)"
chars="$(sed -n 's/^chars=//p' "$M" 2>/dev/null | head -1)"
echo "5 原文の写しの件数: ${rows:-不明} 件 (前回 ${prev:-不明} 件)・文字数 ${chars:-不明}"
if [ -z "$rows" ] || [ -z "$prev" ]; then bad=1
elif [ "$prev" -gt 0 ] && [ "$rows" -lt "$prev" ]; then echo "  前回より減っています"; bad=1; fi
exit $bad
