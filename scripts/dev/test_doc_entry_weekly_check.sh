#!/usr/bin/env bash
# doc-entry-weekly-check.sh の試験（design §32 D3・ADR-1040）。偽の HOME・REPO・gh だけを使う。
set -u
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SELF_DIR/doc-entry-weekly-check.sh"
T="$(mktemp -d)"
trap 'rm -rf "${T:?}"' EXIT

PASS=0; FAIL=0
check() {
  local name="$1"; shift
  if "$@"; then PASS=$((PASS+1)); echo "PASS $name"; else FAIL=$((FAIL+1)); echo "FAIL $name"; fi
}
has() { printf '%s\n' "$OUT" | grep -qxF -- "$1"; }
has_re() { printf '%s\n' "$OUT" | grep -qE -- "$1"; }
lacks() { ! printf '%s\n' "$OUT" | grep -qF -- "$1"; }
rc_is() { [ "$RC" -eq "$1" ]; }

cat > "${T:?}/gh" <<'EOS'
#!/usr/bin/env bash
if [ -n "${FAKE_GH_RC:-}" ] && [ "$FAKE_GH_RC" != 0 ]; then exit "$FAKE_GH_RC"; fi
case "$1" in
  run) printf '%s\n' "$FAKE_RUN_JSON" ;;
  pr) printf '%s\n' "$FAKE_PR_JSON" ;;
esac
exit 0
EOS
chmod +x "${T:?}/gh"

lines() { local n="$1" i; for ((i=1;i<=n;i++)); do echo "l$i"; done; }

setup() {
  rm -rf "${T:?}/home" "${T:?}/repo"
  local H="${T:?}/home" R="${T:?}/repo"
  mkdir -p "$H/.claude/rules/common" "$H/.claude/scripts" "$H/kb" "$H/CC報告ファイル-keep/consent-weekly" \
    "$R/scripts/agent-hooks" "$R/docs/handoff/doc-agenda-nav" "$H/kb/scripts/hooks/plain-lang"
  { lines 9; echo '@~/kb/AGENTS.md'; } > "$H/.claude/CLAUDE.md"
  lines 5 > "$H/kb/AGENTS.md"
  lines 3 > "$H/.claude/rules/common/a.md"
  { echo '---'; echo 'paths:'; echo '  - "**/*.py"'; echo '---'; lines 16; } > "$H/.claude/rules/common/b.md"
  echo x > "$H/.claude/scripts/master-register-rules-guard.py"
  : > "$H/CC報告ファイル-keep/consent-weekly/20270131.txt"
  lines 2 > "$R/CLAUDE.md"
  lines 4 > "$R/AGENTS.md"
  echo x > "$R/scripts/agent-hooks/master-register-rules-guard.py"
  echo '## 全条件の測り直し（2027-01-01）' > "$R/docs/handoff/doc-agenda-nav/baseline.md"
  # 図書館の点検が通る偽の hook.py と台帳（L2=0・L3_MATCH=yes になる）
  printf '%s\n' 'CHAT_FORMAT = "~/.claude/chat-format.md"' 'SECTION = "## Sec Title"' > "$H/kb/scripts/hooks/plain-lang/hook.py"
  printf '%s\n' '| R-nn | 節の名前 | 所在 | 種別 | 移した段 |' '|---|---|---|---|---|' > "$R/docs/handoff/doc-agenda-nav/library-ledger.md"
  export FAKE_RUN_JSON='[{"status":"completed","conclusion":"success"}]'
  export FAKE_PR_JSON='[]'
  unset FAKE_GH_RC
}
run() {
  OUT="$(DOC_ENTRY_HOME="$T/home" DOC_ENTRY_REPO="$T/repo" DOC_ENTRY_GH="$T/gh" \
    DOC_ENTRY_TODAY=2027-01-31 DOC_ENTRY_SKIP_K9=1 bash "$SCRIPT")"
  RC=$?
}
BL() { echo "$1" > "$T/repo/docs/handoff/doc-agenda-nav/baseline.md"; }
PEERS() { rm -f "${T:?}/home/CC報告ファイル-keep/consent-weekly/"*; local f; for f in "$@"; do : > "$T/home/CC報告ファイル-keep/consent-weekly/$f"; done; }

setup; run
check "T1 K1=24" has K1=24
check "T1 b.md を数えない" lacks b.md
check "T1 K2_COPY=SAME" has K2_COPY=SAME
check "T1 K9=skipped" has K9=skipped
check "T1 DOC_INDEX_CI=success" has DOC_INDEX_CI=success
check "T1 K12_LAST" has K12_LAST=2027-01-01
check "T1 K12_DUE=no" has K12_DUE=no
check "T1 K12_OPEN_PR=none" has K12_OPEN_PR=none
check "T1 PEER_LAST" has PEER_LAST=2027-01-31
check "T1 RESULT=OK" has RESULT=OK
check "T1 rc=0" rc_is 0

setup; { lines 199; echo '@~/kb/AGENTS.md'; } > "$T/home/.claude/CLAUDE.md"; run
check "T2 K1=214" has K1=214
check "T2 RESULT=NG K1>200" has_re '^RESULT=NG.*K1>200'
check "T2 rc=1" rc_is 1

setup; echo y > "$T/home/.claude/scripts/master-register-rules-guard.py"; run
check "T3 K2_COPY=DIFF" has K2_COPY=DIFF
check "T3 RESULT=NG" has_re '^RESULT=NG'

setup; BL '## 全条件の測り直し（2026-11-01）'; run
check "T4 K12_DUE=yes" has K12_DUE=yes
check "T4 RESULT=OK" has RESULT=OK

setup; printf '%s\n' '## 全条件の測り直し（2026-11-01）' '## 段8 の後の測り直し（2027-01-30）' > "$T/repo/docs/handoff/doc-agenda-nav/baseline.md"; run
check "T5 K12_LAST=2026-11-01" has K12_LAST=2026-11-01
check "T5 K12_DUE=yes" has K12_DUE=yes

setup; BL '## 全条件の測り直し（2026-11-02）'; run
check "T6 K12_DUE=no" has K12_DUE=no

setup; FAKE_RUN_JSON='[{"status":"completed","conclusion":"failure"}]'; run
check "T7 DOC_INDEX_CI=failure" has DOC_INDEX_CI=failure
check "T7 RESULT=NG" has_re '^RESULT=NG'

setup; FAKE_RUN_JSON='[{"status":"in_progress","conclusion":""}]'; run
check "T8 DOC_INDEX_CI=pending" has DOC_INDEX_CI=pending
check "T8 RESULT=OK" has RESULT=OK

setup; PEERS 20270124.txt; run
check "T9 PEER_LAST=2027-01-24" has PEER_LAST=2027-01-24
check "T9 RESULT=NG" has_re '^RESULT=NG'

setup; PEERS 20270125.txt; run
check "T10 RESULT=OK" has RESULT=OK

setup; PEERS 20270124.txt 20270131-guard-blocked-analysis.md; run
check "T11 PEER_LAST=2027-01-24" has PEER_LAST=2027-01-24
check "T11 RESULT=NG" has_re '^RESULT=NG'

setup; FAKE_PR_JSON='[{"headRefName":"release/doc-entry-k12-20270101","url":"https://example.invalid/pull/1"}]'; run
check "T12 K12_OPEN_PR=URL" has K12_OPEN_PR=https://example.invalid/pull/1
check "T12 RESULT=OK" has RESULT=OK

setup; FAKE_PR_JSON='[{"headRefName":"release/other","url":"https://example.invalid/pull/2"}]'; run
check "T13 K12_OPEN_PR=none" has K12_OPEN_PR=none

setup; rm "$T/home/kb/AGENTS.md"; run
check "T14 K1_MISSING" has "K1_MISSING=~/kb/AGENTS.md"
check "T14 RESULT=NG" has_re '^RESULT=NG'

setup; FAKE_GH_RC=1; export FAKE_GH_RC; run
check "T15 DOC_INDEX_CI=unreadable" has DOC_INDEX_CI=unreadable
check "T15 K12_OPEN_PR=unreadable" has K12_OPEN_PR=unreadable
check "T15 RESULT=NG" has_re '^RESULT=NG'

# 図書館の点検の結線
setup; run
check "T16 BOOKS_IN_CONTEXT=skipped" has BOOKS_IN_CONTEXT=skipped
check "T16 skipped だけでは NG にならない" has RESULT=OK
check "T16 L2=0" has L2=0
check "T16 L3_MATCH=yes" has L3_MATCH=yes

setup; rm -f "$T/repo/docs/handoff/doc-agenda-nav/library-ledger.md"; run
check "T17 L2=unreadable" has L2=unreadable
check "T17 RESULT=NG に L2= が入る" has_re '^RESULT=NG.*L2=unreadable'
check "T17 rc=1" rc_is 1

# 段2a: K1 の数え方（doc-library-check.sh の走査）
once() { printf '%s\n' "$OUT" | grep '^K1_FILES=' | grep -o -- "$1" | wc -l | tr -d ' '; }
HB="$T/home"; RP="$T/repo"

setup; printf '  @~/kb/x.md\n' >> "$HB/.claude/CLAUDE.md"; lines 3 > "$HB/kb/x.md"; run
check "T18 K1=28" has K1=28
check "T18 K1_FILES に ~/kb/x.md" has_re '^K1_FILES=.*~/kb/x\.md'

setup; printf '見る @~/kb/y.md を読む\n' >> "$HB/.claude/CLAUDE.md"; lines 2 > "$HB/kb/y.md"; run
check "T19 K1=27" has K1=27

setup; printf '%s\n' '```' '@~/kb/z.md' '```' '`@~/kb/w.md`' >> "$HB/.claude/CLAUDE.md"; lines 5 > "$HB/kb/z.md"; lines 5 > "$HB/kb/w.md"; run
check "T20 K1=28" has K1=28
check "T20 z.md が無い" lacks z.md
check "T20 w.md が無い" lacks w.md
check "T20 K1_MISSING=none" has K1_MISSING=none

setup; printf '@./n1.md\n' >> "$HB/kb/AGENTS.md"; lines 2 > "$HB/kb/n1.md"; run
check "T21 K1=27" has K1=27
check "T21 K1_FILES に ~/kb/n1.md" has_re '^K1_FILES=.*~/kb/n1\.md'

setup; printf '@AGENTS.md\n' >> "$RP/CLAUDE.md"; run
check "T22 K1=25" has K1=25
check "T22 repo/AGENTS.md が1回" [ "$(once 'repo/AGENTS.md')" = 1 ]

setup; printf '@~/kb/AGENTS.md\n' >> "$HB/.claude/CLAUDE.md"; run
check "T23 K1=25" has K1=25
check "T23 ~/kb/AGENTS.md が1回" [ "$(once '~/kb/AGENTS.md')" = 1 ]

setup; printf '%s\n' '連絡 x@example と `hitoshi@host`' >> "$HB/.claude/CLAUDE.md"; run
check "T24 K1=25" has K1=25
check "T24 K1_MISSING=none" has K1_MISSING=none
check "T24 RESULT=OK" has RESULT=OK

echo "PASS $PASS / FAIL $FAIL"
[ "$FAIL" -eq 0 ]
