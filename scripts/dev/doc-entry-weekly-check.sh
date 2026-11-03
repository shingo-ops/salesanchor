#!/usr/bin/env bash
# 入口の文書の週次点検（doc-agenda-nav design §32 D3・ADR-1040）。読むだけ。
# 使い方: bash scripts/dev/doc-entry-weekly-check.sh（RESULT=OK なら rc=0、NG なら rc=1）
set -u

# 合格線の正本はここ1か所（docs/specs/doc-agenda-nav/kgi.md の写し）
K1_LIMIT=200
K9_LIMIT_TOKENS=6500
K12_DAYS=90
PEER_DAYS=7

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${DOC_ENTRY_HOME:-$HOME}"
REPO="${DOC_ENTRY_REPO:-$(cd "$SELF_DIR/../.." && pwd)}"
GH="${DOC_ENTRY_GH:-gh}"
TODAY="${DOC_ENTRY_TODAY:-$(date +%Y-%m-%d)}"

NG=""
add_ng() { NG="$NG $1"; }

# 日数差 (a - b)。引数は YYYY-MM-DD
days_between() {
  python3 -I -c 'import sys,datetime as d
f=lambda s:d.date.fromisoformat(s)
print((f(sys.argv[1])-f(sys.argv[2])).days)' "$1" "$2"
}

# ---- K1（数え方は doc-library-check.sh の K1_DEF の走査1か所だけ。library-design §4-2・段2a） ----
LIB_OUT="$(DOC_ENTRY_HOME="$HOME_DIR" DOC_ENTRY_REPO="$REPO" bash "$SELF_DIR/doc-library-check.sh")"
lib_val() { printf '%s\n' "$LIB_OUT" | sed -n "s/^$1=//p" | head -n 1; }
K1_TOTAL="$(lib_val K1_DEF)"
case "$K1_TOTAL" in ''|*[!0-9]*) K1_TOTAL=unreadable ;; esac
K1_FILES_V="$(lib_val K1_DEF_FILES)"
K1_MISS_V="$(lib_val K1_DEF_MISSING)"
[ -z "$K1_MISS_V" ] && K1_MISS_V=unreadable
echo "K1=$K1_TOTAL"
echo "K1_FILES=$K1_FILES_V"
echo "K1_MISSING=$K1_MISS_V"
[ "$K1_MISS_V" != none ] && add_ng "K1_MISSING=$K1_MISS_V"
if [ "$K1_TOTAL" = unreadable ]; then add_ng "K1=unreadable"
elif [ "$K1_TOTAL" -gt "$K1_LIMIT" ]; then add_ng "K1>$K1_LIMIT"; fi

# ---- K2 ----
A="$HOME_DIR/.claude/scripts/master-register-rules-guard.py"
B="$REPO/scripts/agent-hooks/master-register-rules-guard.py"
if [ ! -f "$A" ] || [ ! -f "$B" ]; then K2=missing
elif cmp -s "$A" "$B"; then K2=SAME
else K2=DIFF; fi
echo "K2_COPY=$K2"
[ "$K2" != SAME ] && add_ng "K2_COPY=$K2"

# ---- K9 ----
if [ "${DOC_ENTRY_SKIP_K9:-}" = 1 ]; then
  K9=skipped
else
  K9=unreadable
  if command -v claude >/dev/null 2>&1; then
    OUT="$(cd "$REPO" && claude -p "/context" --no-session-persistence 2>/dev/null)"
    if [ $? -eq 0 ]; then
      K9="$(printf '%s\n' "$OUT" | python3 -I -c 'import sys,re
def val(s):
    s=s.strip().replace(",","")
    m=re.match(r"^([0-9.]+)\s*([kK]?)",s)
    if not m: return None
    v=float(m.group(1))
    return v*1000 if m.group(2) else v
mem=None; mm=None; sect=False
for l in sys.stdin:
    if re.match(r"^\s*\|\s*Memory files\s*\|",l):
        mem=val(l.split("|")[2])
    if l.startswith("### Memory Files"): sect=True; continue
    if sect and l.startswith("#"): sect=False
    if sect and l.strip().startswith("|"):
        c=[x.strip() for x in l.strip().strip("|").split("|")]
        if len(c)>=3 and c[1].endswith("/MEMORY.md"):
            mm=val(c[2])
if mem is None or mm is None: print("unreadable")
else: print("%.1fk"%((mem-mm)/1000))')"
    fi
  fi
fi
echo "K9=$K9"
case "$K9" in
  unreadable) add_ng "K9=unreadable" ;;
  skipped) ;;
  *)
    if python3 -I -c 'import sys;sys.exit(0 if float(sys.argv[1].rstrip("k"))*1000>float(sys.argv[2]) else 1)' "$K9" "$K9_LIMIT_TOKENS"; then
      add_ng "K9>6.5k"
    fi ;;
esac

# ---- 図書館の点検（doc-library-check.sh。library-design §4-2） ----
L2_PASS=0
L2_UNTAGGED_PASS=0
L3_MATCH_PASS=yes
BOOKS_IMPORTED_PASS=0
printf '%s\n' "$LIB_OUT"
LV_L2="$(lib_val L2)"
LV_UNT="$(lib_val L2_UNTAGGED)"
LV_L3="$(lib_val L3_MATCH)"
LV_BI="$(lib_val BOOKS_IMPORTED)"
[ "$LV_L2" != "$L2_PASS" ] && add_ng "L2=${LV_L2:-unreadable}"
[ "$LV_UNT" != "$L2_UNTAGGED_PASS" ] && add_ng "L2_UNTAGGED=${LV_UNT:-unreadable}"
case "$LV_L3" in "$L3_MATCH_PASS") ;; *) add_ng "L3_MATCH=no" ;; esac
[ "$LV_BI" != "$BOOKS_IMPORTED_PASS" ] && add_ng "BOOKS_IMPORTED=${LV_BI:-unreadable}"

# BOOKS_IN_CONTEXT: /context の Memory files の表で /.claude/books/ を含む行の数
case "$K9" in
  skipped) BOOKS_CTX=skipped ;;
  unreadable) BOOKS_CTX=unreadable ;;
  *)
    BOOKS_CTX="$(printf '%s\n' "${OUT:-}" | python3 -I -c 'import sys
sect=False; n=0
for l in sys.stdin:
    if l.startswith("### Memory Files"): sect=True; continue
    if sect and l.startswith("#"): sect=False
    if sect and l.strip().startswith("|") and "/.claude/books/" in l: n+=1
print(n)')"
    [ -z "$BOOKS_CTX" ] && BOOKS_CTX=unreadable
    ;;
esac
echo "BOOKS_IN_CONTEXT=$BOOKS_CTX"
case "$BOOKS_CTX" in
  skipped|0) ;;
  unreadable) ;; # K9=unreadable で NG 済み
  *) add_ng "BOOKS_IN_CONTEXT=$BOOKS_CTX" ;;
esac

# ---- DOC_INDEX_CI ----
CI=unreadable
J="$("$GH" run list --workflow doc-index-reachability.yml --branch main -L 1 --json status,conclusion 2>/dev/null)"
if [ $? -eq 0 ]; then
  CI="$(printf '%s' "$J" | python3 -I -c 'import sys,json
try: d=json.load(sys.stdin)
except Exception: print("unreadable"); sys.exit()
if not isinstance(d,list): print("unreadable")
elif not d: print("none")
elif d[0].get("status")!="completed": print("pending")
elif d[0].get("conclusion")=="success": print("success")
else: print("failure")' 2>/dev/null)"
  [ -z "$CI" ] && CI=unreadable
fi
echo "DOC_INDEX_CI=$CI"
case "$CI" in failure|unreadable) add_ng "DOC_INDEX_CI=$CI" ;; esac

# ---- K12 ----
K12_LAST="$(python3 -I -c 'import sys,re
ds=[]
try:
    for l in open(sys.argv[1],encoding="utf-8"):
        m=re.match(r"^## 全条件の測り直し（([0-9]{4}-[0-9]{2}-[0-9]{2})）$",l.rstrip("\n"))
        if m: ds.append(m.group(1))
except OSError: pass
print(max(ds) if ds else "none")' "$REPO/docs/handoff/doc-agenda-nav/baseline.md")"
echo "K12_LAST=$K12_LAST"
if [ "$K12_LAST" = none ] || [ "$(days_between "$TODAY" "$K12_LAST")" -gt "$K12_DAYS" ]; then
  echo "K12_DUE=yes"
else
  echo "K12_DUE=no"
fi

PR=unreadable
J="$("$GH" pr list --state open -L 200 --json headRefName,url 2>/dev/null)"
if [ $? -eq 0 ]; then
  PR="$(printf '%s' "$J" | python3 -I -c 'import sys,json
try: d=json.load(sys.stdin)
except Exception: print("unreadable"); sys.exit()
if not isinstance(d,list): print("unreadable"); sys.exit()
for x in d:
    if str(x.get("headRefName","")).startswith("release/doc-entry-k12-"):
        print(x.get("url","none")); sys.exit()
print("none")' 2>/dev/null)"
  [ -z "$PR" ] && PR=unreadable
fi
echo "K12_OPEN_PR=$PR"

# ---- PEER ----
PEER="$(python3 -I -c 'import sys,os,re
ds=[]
try:
    for n in os.listdir(sys.argv[1]):
        m=re.match(r"^([0-9]{4})([0-9]{2})([0-9]{2})\.txt$",n)
        if m: ds.append("-".join(m.groups()))
except OSError: pass
print(max(ds) if ds else "none")' "$HOME_DIR/CC報告ファイル-keep/consent-weekly")"
echo "PEER_LAST=$PEER"
if [ "$PEER" = none ]; then add_ng "PEER_LAST=none"
elif [ "$(days_between "$TODAY" "$PEER")" -ge "$PEER_DAYS" ]; then add_ng "PEER_LAST=$PEER"; fi

if [ -z "$NG" ]; then
  echo "RESULT=OK"; exit 0
else
  echo "RESULT=NG${NG}"; exit 1
fi
