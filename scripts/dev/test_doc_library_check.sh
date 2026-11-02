#!/usr/bin/env bash
# doc-library-check.sh の試験（library-stage0-card.md §4）。偽の HOME・REPO・hook.py・台帳だけを使う。
set -u
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SELF_DIR/doc-library-check.sh"
T="$(mktemp -d)"
trap 'rm -rf "${T:?}"' EXIT

PASS=0; FAIL=0; N=0
check() {
  local name="$1"; shift
  N=$((N+1))
  if "$@"; then PASS=$((PASS+1)); echo "PASS $name"; else FAIL=$((FAIL+1)); echo "FAIL $name"; fi
}
has() { printf '%s\n' "$OUT" | grep -qxF -- "$1"; }
lacks_line() { ! printf '%s\n' "$OUT" | grep -qxF -- "$1"; }
has_re() { printf '%s\n' "$OUT" | grep -qE -- "$1"; }

H="${T:?}/home"; R="${T:?}/repo"
LEDGER_HEAD='| R-nn | 節の名前 | 所在 | 種別 | 移した段 |
|---|---|---|---|---|'

# 偽の家を最初から作り直す。台帳は見出しだけの表。
setup() {
  rm -rf "${T:?}/home" "${T:?}/repo"
  mkdir -p "$H/.claude/rules" "$H/.claude/books" "$H/kb/scripts/hooks/plain-lang" \
    "$R/docs/handoff/doc-agenda-nav"
  echo 'home claude' > "$H/.claude/CLAUDE.md"
  echo 'repo claude' > "$R/CLAUDE.md"
  echo 'repo agents' > "$R/AGENTS.md"
  printf '%s\n' 'CHAT_FORMAT = "~/.claude/chat-format.md"' 'SECTION = "## Sec Title"' \
    > "$H/kb/scripts/hooks/plain-lang/hook.py"
  printf '%s\n' "$LEDGER_HEAD" > "$R/docs/handoff/doc-agenda-nav/library-ledger.md"
}
run() {
  OUT="$(DOC_ENTRY_HOME="$H" DOC_ENTRY_REPO="$R" bash "$SCRIPT")"
  RC=$?
}
files_has() { printf '%s\n' "$OUT" | grep '^K1_DEF_FILES=' | tr ',' '\n' | grep -qxF -- "$1" ; }
files_lacks() { ! printf '%s\n' "$OUT" | grep '^K1_DEF_FILES=' | sed 's/^K1_DEF_FILES=//' | tr ',' '\n' | grep -qxF -- "$1"; }
LEDGER="$R/docs/handoff/doc-agenda-nav/library-ledger.md"

# T1 字下げした @ を数える
setup; echo 'x line' > "$H/kb/x.md"
printf '%s\n' 'a' '  @~/kb/x.md' > "$H/.claude/CLAUDE.md"; run
check "T1 字下げ @ を数える" files_has '~/kb/x.md'
check "T1 rc=0" test "$RC" -eq 0

# T2 行の途中の @
setup; echo 'y line' > "$H/kb/y.md"
echo 'see also @~/kb/y.md here' > "$H/.claude/CLAUDE.md"; run
check "T2 行の途中の @ を数える" files_has '~/kb/y.md'

# T3 バッククォート・囲みの中は数えない
setup; echo z > "$H/kb/z.md"; echo w > "$H/kb/w.md"
printf '%s\n' 'use `@~/kb/z.md` inline' '```' '@~/kb/w.md' '```' > "$H/.claude/CLAUDE.md"; run
check "T3 バッククォートの中は数えない" files_lacks '~/kb/z.md'
check "T3 囲みの中は数えない" files_lacks '~/kb/w.md'

# T4 入れ子。4段まで。5段目は数えない
setup; mkdir -p "$H/kb"
echo '@~/kb/n1.md' > "$H/.claude/CLAUDE.md"
echo '@~/kb/n2.md' > "$H/kb/n1.md"
echo '@~/kb/n3.md' > "$H/kb/n2.md"
echo '@~/kb/n4.md' > "$H/kb/n3.md"
echo '@~/kb/n5.md' > "$H/kb/n4.md"
echo 'end' > "$H/kb/n5.md"; run
check "T4 4段目まで数える" files_has '~/kb/n4.md'
check "T4 5段目は数えない" files_lacks '~/kb/n5.md'

# T5 @AGENTS.md と直接足す AGENTS.md が二重にならない
setup; printf '%s\n' '@AGENTS.md' 'two' > "$R/CLAUDE.md"; run
check "T5 AGENTS.md は1回" test "$(printf '%s\n' "$OUT" | grep '^K1_DEF_FILES=' | tr ',' '\n' | grep -cF "$R/AGENTS.md")" -eq 1
# 行数: home 1 + repo CLAUDE 2 + AGENTS 1 = 4
check "T5 K1_DEF=4" has K1_DEF=4

# T6 同じファイルを2回 @
setup; echo 'once' > "$H/kb/d.md"
printf '%s\n' '@~/kb/d.md' '@~/kb/d.md' > "$H/.claude/CLAUDE.md"; run
check "T6 2回 @ しても1回" test "$(printf '%s\n' "$OUT" | grep '^K1_DEF_FILES=' | tr ',' '\n' | grep -cxF '~/kb/d.md')" -eq 1
check "T6 K1_DEF=5" has K1_DEF=5

# T7 hitoshi@host と x@example は数えない
setup
printf '%s\n' 'user `hitoshi@host` ok' 'mail x@example now' > "$H/.claude/CLAUDE.md"; run
check "T7 K1_DEF_MISSING=none" has K1_DEF_MISSING=none

# T8 L2_CHANNEL
setup; printf '%s\n' 'intro' '## Sec Title' 'body' > "$H/.claude/chat-format.md"
echo '  @~/.claude/chat-format.md' > "$H/.claude/CLAUDE.md"; run
check "T8 L2_CHANNEL=1" has L2_CHANNEL=1
setup; printf '%s\n' 'intro' '## Sec Title' 'body' > "$H/.claude/chat-format.md"; echo 'other' > "$H/kb/o.md"
echo '  @~/kb/o.md' > "$H/.claude/CLAUDE.md"; run
check "T8 取り込み先が別ファイル → 0" has L2_CHANNEL=0

# T9 CHAT_FORMAT の行が2つ
setup; printf '%s\n' 'CHAT_FORMAT = "~/.claude/a.md"' 'CHAT_FORMAT = "~/.claude/b.md"' 'SECTION = "## S"' \
  > "$H/kb/scripts/hooks/plain-lang/hook.py"; run
check "T9 L2_CHANNEL=unreadable" has L2_CHANNEL=unreadable

# T10 台帳の1つの番号に所在2つ
setup
printf '%s\n' "$LEDGER_HEAD" '| R-01 | 例 | ~/.claude/CLAUDE.md:A:1<br>AGENTS.md:B:2 | 目録 | 0 |' > "$LEDGER"; run
check "T10 L2_DUP_LEDGER=1" has L2_DUP_LEDGER=1
setup
printf '%s\n' "$LEDGER_HEAD" '| R-01 | 例 | ~/.claude/CLAUDE.md:A:1; AGENTS.md:B:2 | 目録 | 0 |' '| R-02 | 例2 | AGENTS.md:C:3 | 目録 | 0 |' > "$LEDGER"; run
check "T10 '; ' 区切りでも1（所在1つの番号は数えない）" has L2_DUP_LEDGER=1

# T11 台帳に無い見出し
setup; printf '%s\n' '## Known' '## Missing One' > "$H/.claude/CLAUDE.md"
printf '%s\n' "$LEDGER_HEAD" '| R-01 | 既知 | ~/.claude/CLAUDE.md:Known:1 | 目録 | 0 |' > "$LEDGER"; run
check "T11 L2_UNTAGGED=1" has L2_UNTAGGED=1

# T12 台帳が無い
setup; rm -f "$LEDGER"; run
check "T12 L2=unreadable" has L2=unreadable
check "T12 L2_UNTAGGED=unreadable" has L2_UNTAGGED=unreadable
check "T12 L3_LEDGER=unreadable" has L3_LEDGER=unreadable

# T13 同じ [R-01] が2冊
setup
printf '%s\n' '---' 'book: a' '---' '## One [R-01]' > "$H/.claude/books/a.md"
printf '%s\n' '---' 'book: b' '---' '## Two [R-01]' > "$H/.claude/books/b.md"; run
check "T13 L2_DUP_ID=1" has L2_DUP_ID=1

# T14 同じ20文字以上の行
setup; L='this is a long enough shared line of text'
printf '%s\n' "- $L" > "$H/.claude/CLAUDE.md"; printf '%s\n' "$L" > "$R/AGENTS.md"; run
check "T14 L2_DUP_LINE=1" has L2_DUP_LINE=1
setup; L='this is a long enough shared line of text'
printf '%s\n' "- 本:$L" > "$H/.claude/CLAUDE.md"; printf '%s\n' "- 本:$L" > "$R/AGENTS.md"; run
check "T14 '- 本:' の行だけ同じ → 0" has L2_DUP_LINE=0

# T15 目録の番号と本の番号
setup; printf '%s\n' '---' 'book: gw' '---' '## H1 [R-01]' > "$H/.claude/books/gw.md"
echo '- 本:gw#R-02 場面 → ~/.claude/books/gw.md' > "$H/.claude/CLAUDE.md"; run
check "T15 食い違い → L3_MATCH=no R-01,R-02" has 'L3_MATCH=no R-01,R-02'
setup; printf '%s\n' '---' 'book: gw' '---' '## H1 [R-01]' > "$H/.claude/books/gw.md"
echo '- 本:gw#R-01 場面 → ~/.claude/books/gw.md' > "$H/.claude/CLAUDE.md"
printf '%s\n' "$LEDGER_HEAD" '| R-01 | 一 | ~/.claude/books/gw.md:H1:4 | 本 | 2b |' > "$LEDGER"; run
check "T15 合う → L3_MATCH=yes" has L3_MATCH=yes
check "T15 L3_INDEX=1 L3_BOOKS=1 L3_LEDGER=1" has_re '^L3_INDEX=1$'

# T16 BOOKS_IMPORTED
setup; echo '@~/.claude/books/x.md' > "$H/.claude/CLAUDE.md"; run
check "T16 囲みの外 → 1" has BOOKS_IMPORTED=1
setup; printf '%s\n' '```' '@~/.claude/books/x.md' '```' > "$H/.claude/CLAUDE.md"; run
check "T16 囲みの中 → 0" has BOOKS_IMPORTED=0

# 出力の行の順
setup; run
ORDER="$(printf '%s\n' "$OUT" | cut -d= -f1 | tr '\n' ' ')"
check "出力の順" test "$ORDER" = "K1_DEF K1_DEF_FILES K1_DEF_MISSING L2_CHANNEL L2_DUP_LEDGER L2_DUP_ID L2_DUP_LINE L2 L2_UNTAGGED L3_INDEX L3_BOOKS L3_LEDGER L3_MATCH BOOKS_IMPORTED "

echo "PASS $PASS/$N"
[ "$FAIL" -eq 0 ]
