#!/bin/bash
# weekly-check.sh — confidential-quote-guard の週の点検 (design.md 維持の仕組み)。
# agent-console の定期実行から流す。出力は件数と日付だけ（語句は出さない）。0 でないものは知らせる。
#   1. 原本 (origin/main の guard.py) と写したもの (~/.claude/scripts) の diff 行数
#   2. 一般語の表の行数と、その週に足した行数
#   3. 商品名の写しの日付 (7 日より古ければ取り直す)
#   4. 社外秘フォルダの新しいフォルダのうち、置き場の表に無いもの
set -u
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
KEEP="${CONFID_KEEP_DIR:-$HOME/CC報告ファイル-keep}"
D="${CONFID_GUARD_DIR:-$KEEP/confid-guard}"
REPO="${CONFID_REPO:-$HOME/salesanchor}"
INST="$CLAUDE_DIR/scripts/confidential-quote-guard/guard.py"
REL="scripts/agent-hooks/confidential-quote-guard/guard.py"
bad=0

d1="$(git -C "$REPO" show "origin/main:$REL" 2>/dev/null | diff - "$INST" 2>/dev/null | wc -l | tr -d ' ')"
echo "1 原本と写しの差分行数: $d1"; [ "$d1" != "0" ] && bad=1

n="$(grep -vc '^\s*#\|^\s*$' "$D/confidential-allow.txt" 2>/dev/null || echo 0)"
w="$(find "$D/confidential-allow.txt" -mtime -7 2>/dev/null | wc -l | tr -d ' ')"
echo "2 一般語の表の行数: $n (今週更新: $([ "$w" = "1" ] && echo あり || echo なし))"

b="$(sed -n 's/^# built: //p' "$D/product-names.txt" 2>/dev/null | head -1)"
if [ -n "$b" ]; then
  age=$(( ( $(date +%s) - $(date -j -f %Y-%m-%d "$b" +%s 2>/dev/null || echo 0) ) / 86400 ))
else age=-1; fi
echo "3 商品名の写しの日付: ${b:-不明} (${age} 日前)"; { [ "$age" -lt 0 ] || [ "$age" -gt 7 ]; } && bad=1

miss=0
for dir in "$KEEP"/*/; do
  name="$(basename "$dir")"
  [ "$name" = "confid-guard" ] && continue
  if ! grep -qF "/$name/" "$D/confidential-corpus.conf" 2>/dev/null; then
    # 置き場の表に無いフォルダのうち、7 日以内に作られた新しいもの
    find "$dir" -maxdepth 0 -ctime -7 2>/dev/null | grep -q . && miss=$((miss+1))
  fi
done
echo "4 置き場の表に無い新しいフォルダ数: $miss"; [ "$miss" != "0" ] && bad=1
exit $bad
