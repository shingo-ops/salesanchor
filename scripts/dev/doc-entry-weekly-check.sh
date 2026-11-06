#!/usr/bin/env bash
# 入口の文書の週次点検（doc-agenda-nav design §32 D3・ADR-1040）。読むだけ。
# 使い方: bash scripts/dev/doc-entry-weekly-check.sh（RESULT=OK なら rc=0、NG なら rc=1）
set -u

# 合格線の正本は docs/specs/doc-agenda-nav/kgi.md。下の値はその写しで、ずれは scripts/ci/check_kgi_line_copies.py が見つける
K1_LIMIT=210
K9_LIMIT_TOKENS=7500
K12_DAYS=90
PEER_DAYS=7

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${DOC_ENTRY_HOME:-$HOME}"
REPO="${DOC_ENTRY_REPO:-$(cd "$SELF_DIR/../.." && pwd)}"
GH="${DOC_ENTRY_GH:-gh}"
TODAY="${DOC_ENTRY_TODAY:-$(date +%Y-%m-%d)}"
MEMDIR="${DOC_ENTRY_MEMDIR:-$HOME_DIR/.claude/projects/-Users-tanizawashingo-salesanchor/memory}"

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
      add_ng "K9>7.5k"
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
LV_LN="$(lib_val L2_LINE_NG)"
[ "$LV_L2" != "$L2_PASS" ] && add_ng "L2=${LV_L2:-unreadable}"
[ "$LV_UNT" != "$L2_UNTAGGED_PASS" ] && add_ng "L2_UNTAGGED=${LV_UNT:-unreadable}"
case "$LV_L3" in "$L3_MATCH_PASS") ;; *) add_ng "L3_MATCH=no" ;; esac
[ "$LV_BI" != "$BOOKS_IMPORTED_PASS" ] && add_ng "BOOKS_IMPORTED=${LV_BI:-unreadable}"
[ "$LV_LN" != 0 ] && add_ng "L2_LINE_NG=${LV_LN:-unreadable}"

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

# ---- G1・G3・G6・K4（一本化の点検。数と置き場の名前だけ出す。中身は出さない） ----
read -r -d '' PYG <<'PYEOF'
import os, re, subprocess, sys

HOME, REPO, MEMDIR = sys.argv[1], sys.argv[2], sys.argv[3]
WORDS = ["【おすすめ】", "選択肢には", "選択肢を3", "番号付きの選択肢", "結論を最初", "結論から",
         "結論ファースト", "要点→結論", "専門用語", "日常語", "決めることはありません", "1行目", "2行目"]
CANON = ["chat-layout.md", "chat-layout「", "chat-format.md", "chat-format「"]
MEMS = ["report_style", "communication_style", "always_japanese", "agent_description_japanese",
        "po_chat_three_lines", "plain_language_session", "session_rules_comprehensive",
        "plain_explain_template", "cost_in_yen", "numeric_goal_rule"]


def rd(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().split("\n")
    except OSError:
        return None


def section(lines, start_pred, end_pred):
    """始まりの行の次から、終わりの行の前まで。始まりが無ければ None。"""
    if lines is None:
        return None
    for i, l in enumerate(lines):
        if start_pred(l):
            out = []
            for m in lines[i + 1:]:
                if end_pred(m):
                    break
                out.append(m)
            return out
    return None


def count(body):
    if body is None:
        return "unreadable"
    n = 0
    for l in body:
        if any(w in l for w in WORDS) and not any(c in l for c in CANON):
            n += 1
    return n


places = []
places.append(("E1", count(section(rd(os.path.join(HOME, ".claude/CLAUDE.md")),
                                   lambda l: l.rstrip() == "## 報告の型", lambda l: l.startswith("## ")))))
places.append(("E5", count(section(rd(os.path.join(HOME, ".claude/prompts/salesanchor-designer.md")),
                                   lambda l: l.startswith("【POへの説明】"), lambda l: l.startswith("【")))))
e6 = rd(os.path.join(HOME, ".claude/prompts/salesanchor-claude-go.md"))
places.append(("E6", count(None if e6 is None else [l for l in e6 if "POへの説明" in l])))
places.append(("E7", count(section(rd(os.path.join(REPO, "docs/ai-agents/design-partner.md")),
                                   lambda l: l.startswith("## 3. "), lambda l: l.startswith("## ")))))
for name in MEMS:
    lines = rd(os.path.join(MEMDIR, "feedback_" + name + ".md"))
    if lines is None:
        places.append(("M:" + name, "missing"))
        continue
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    body = []
    skip = False
    for l in lines[start:]:
        if l.startswith("**Why:**"):
            skip = True
        if l.startswith("**How to apply:**"):
            skip = False
        if not skip:
            body.append(l)
    places.append(("M:" + name, count(body)))

print("G1_TABLE=" + ",".join("%s:%s" % (k, v) for k, v in places))
core = [v for k, v in places if k in ("E1", "E5", "E6", "E7")]
if any(v == "unreadable" for v in core):
    print("G1_OUTSIDE=unreadable")
else:
    print("G1_OUTSIDE=%d" % sum(1 for k, v in places if isinstance(v, int) and v >= 1))

# G3
cl = rd(os.path.join(HOME, "kb/00-rules/chat-layout.md"))
hm = rd(os.path.join(HOME, ".claude/CLAUDE.md"))
g3 = (cl is not None and hm is not None
      and any(l.strip() == "## 答える前に" for l in cl)
      and any(l.strip() == "@~/kb/00-rules/chat-layout.md" for l in hm))
print("G3_INTENT=" + ("yes" if g3 else "no"))

# G6
led = rd(os.path.join(REPO, "docs/handoff/doc-agenda-nav/library-ledger.md"))
sec = section(led, lambda l: l.rstrip() == "## 話題の重なり表", lambda l: l.startswith("## "))
g6 = "unreadable"
if sec is not None:
    hi = None
    for i, l in enumerate(sec):
        if l.strip().startswith("| 話題 |"):
            hi = i
            break
    if hi is not None:
        n = 0
        for l in sec[hi + 1:]:
            t = l.strip()
            if not t.startswith("|"):
                break
            cells = [x.strip() for x in t.strip("|").split("|")]
            if all(re.match(r"^:?-+:?$", x) for x in cells if x) and any(cells):
                continue
            if len(cells) < 4 or cells[3] == "":
                n += 1
        g6 = str(n)
print("G6_NO_OWNER=" + g6)

# K4
k4 = "unreadable"
try:
    r = subprocess.run(["python3", "-I", os.path.join(REPO, "scripts/ci/check_doc_index.py"), "--root", REPO],
                       capture_output=True, text=True, timeout=300)
    for l in r.stdout.split("\n"):
        if l.startswith("SUMMARY"):
            m = re.search(r"\bunreached=(\d+)", l)
            if m:
                k4 = m.group(1)
            break
except Exception:
    pass
print("K4_WIDE_UNREACHED=" + k4)
PYEOF
G_OUT="$(python3 -I -c "$PYG" "$HOME_DIR" "$REPO" "$MEMDIR" 2>/dev/null)"
printf '%s\n' "$G_OUT"
g_val() { printf '%s\n' "$G_OUT" | sed -n "s/^$1=//p" | head -n 1; }
GV_OUT="$(g_val G1_OUTSIDE)"
[ "$GV_OUT" != 0 ] && add_ng "G1_OUTSIDE=${GV_OUT:-unreadable}"
GV_G3="$(g_val G3_INTENT)"
[ "$GV_G3" != yes ] && add_ng "G3_INTENT=${GV_G3:-unreadable}"
GV_G6="$(g_val G6_NO_OWNER)"
[ "$GV_G6" != 0 ] && add_ng "G6_NO_OWNER=${GV_G6:-unreadable}"
GV_K4="$(g_val K4_WIDE_UNREACHED)"
[ "$GV_K4" != 0 ] && add_ng "K4_WIDE_UNREACHED=${GV_K4:-unreadable}"

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

# ---- LINE_COPY（合格線の写しのずれ。scripts/ci/check_kgi_line_copies.py。C6 は定期実行の指示書） ----
if [ -f "$REPO/docs/specs/doc-agenda-nav/kgi.md" ]; then
  LC_OUT="$(python3 -I "$SELF_DIR/../ci/check_kgi_line_copies.py" --root "$REPO" --routines "${DOC_ENTRY_ROUTINES:-$HOME_DIR/Library/Application Support/agent-console/routines.json}")"
  LC_RC=$?
  printf '%s\n' "$LC_OUT"
  case "$LC_RC" in
    0) echo "LINE_COPY=SAME" ;;
    1) echo "LINE_COPY=DIFF"; add_ng "LINE_COPY=DIFF" ;;
    *) echo "LINE_COPY=error"; add_ng "LINE_COPY=error" ;;
  esac
else
  echo "LINE_COPY=skipped"
fi

if [ -z "$NG" ]; then
  echo "RESULT=OK"; exit 0
else
  echo "RESULT=NG${NG}"; exit 1
fi
