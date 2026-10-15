#!/bin/bash
# test-claude-archive.sh — scripts/claude-archive.sh の試験（K2・K4・K5・K7・K9・K10・K11 と入れ物の開閉）
#
# すべて mktemp -d で作った一時ディレクトリの中だけで動く。hdiutil・security・osascript は偽物
# （CA_*_CMD で差し替え）、入れ物の中身は $T/fakevol。実 HDD・実キーチェーン・実 dataDir・実 ~/.claude には触れない。
# rsync は本物の /usr/bin/rsync を、呼び方を記録し必要なら失敗させる包みを通して使う。
#
# 実行方法: bash scripts/tests/test-claude-archive.sh
# 終了コード: 0=ng が 0 件 / 1=ng あり

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CA="${SCRIPT_DIR}/../claude-archive.sh"
OK=0
NG=0

ok() { echo "ok: $1"; OK=$(( OK + 1 )); }
ng() { echo "ng: $1"; NG=$(( NG + 1 )); }
check() { # check <説明> <コマンド...>（成功なら ok）
  local desc="$1"; shift
  if "$@"; then ok "${desc}"; else ng "${desc}"; fi
}
exists() { [ -e "$1" ] || [ -L "$1" ]; }
gone() { ! exists "$1"; }
lacks() { ! grep -q -- "$1" "$2" 2>/dev/null; }

T_RAW="$(mktemp -d "${TMPDIR:-/tmp}/claude-archive-test.XXXXXX")" || { echo "mktemp 失敗"; exit 1; }
T="$(cd -P "${T_RAW}" && pwd -P)"
case "${T}" in */claude-archive-test.*) ;; *) echo "一時ディレクトリの名前が想定外"; exit 1 ;; esac

wipe() { # 一時ディレクトリの下だけを消す（シンボリックリンクはリンク自身だけ）
  case "$1" in "${T}"/*) [ -e "$1" ] || [ -L "$1" ] && find -P "$1" -depth -delete 2>/dev/null ;; esac
  return 0
}
cleanup() { find -P "${T}" -depth -delete 2>/dev/null; return 0; }
trap cleanup EXIT

# ── 一時ディレクトリの中だけを指す設定（K9）──────────────────────────────────
BIN="${T}/bin"; SRC="${T}/src"; VOL="${T}/fakevol"; HDD="${T}/hdd"; MNT="${T}/mnt"
DD="${T}/datadir"; SESS="${T}/sessions"; LOGD="${T}/logs"
mkdir -p "${BIN}" "${LOGD}"
export STUB_CALLS="${T}/calls.txt" STUB_VOL="${VOL}" STUB_INFO_PLIST="${T}/info.plist" STUB_SECRET="SECRETMARKER-4f9a1c0d77e2"

cat > "${BIN}/security" <<'EOF'
#!/bin/bash
echo "security $*" >> "${STUB_CALLS}"
printf '%s\n' "${STUB_SECRET}"
EOF
cat > "${BIN}/hdiutil" <<'EOF'
#!/bin/bash
echo "hdiutil $1" >> "${STUB_CALLS}"
case "$1" in
  info)
    if [ -f "${STUB_INFO_PLIST}" ]; then cat "${STUB_INFO_PLIST}"
    else printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict><key>images</key><array/></dict></plist>'; fi ;;
  attach)
    [ -n "${STUB_ATTACH_FAIL:-}" ] && { echo "attach failed" >&2; exit 1; }
    [ -n "${STUB_ATTACH_SLEEP:-}" ] && sleep "${STUB_ATTACH_SLEEP}"
    mp=""; prev=""
    for a in "$@"; do [ "${prev}" = "-mountpoint" ] && mp="${a}"; prev="${a}"; done
    in="$(cat)"
    if [ "${in}" = "${STUB_SECRET}" ]; then echo "attach stdin==secret(no newline)" >> "${STUB_CALLS}"; else echo "attach stdin MISMATCH" >> "${STUB_CALLS}"; fi
    echo "attach mountpoint=${mp}" >> "${STUB_CALLS}"
    rmdir "${mp}" && ln -s "${STUB_VOL}" "${mp}" ;;
  detach)
    [ -n "${STUB_DETACH_FAIL:-}" ] && exit 1
    rm "$2" && mkdir "$2" ;;
esac
exit 0
EOF
cat > "${BIN}/osascript" <<'EOF'
#!/bin/bash
echo "osascript" >> "${STUB_CALLS}"
EOF
cat > "${BIN}/rsync" <<'EOF'
#!/bin/bash
echo "rsync $*" >> "${STUB_CALLS}"
if [ -n "${STUB_RSYNC_FAIL:-}" ]; then case "$*" in *"${STUB_RSYNC_FAIL}"*) exit 23 ;; esac; fi
/usr/bin/rsync "$@"; rc=$?
if [ -n "${STUB_RSYNC_CORRUPT:-}" ] && [ -f "${STUB_RSYNC_CORRUPT}" ]; then echo extra >> "${STUB_RSYNC_CORRUPT}"; fi
exit ${rc}
EOF
chmod +x "${BIN}"/*

export CA_HDD_MOUNT="${HDD}" CA_IMAGE="${HDD}/claude-archive.sparsebundle" \
       CA_SECURITY_CMD="${BIN}/security" CA_HDIUTIL_CMD="${BIN}/hdiutil" CA_RSYNC_CMD="${BIN}/rsync" \
       CA_OSASCRIPT_CMD="${BIN}/osascript" CA_LOG_FILE="${LOGD}/ca.log" CA_LAST_OK="${LOGD}/ca.last-ok" \
       CA_LOCK_DIR="${T}/lock.d" CA_MNT_PARENT="${MNT}" \
       CA_SRC_PROJECTS="${SRC}/projects" CA_SRC_HISTORY="${SRC}/history.jsonl" CA_SRC_PLANS="${SRC}/plans" \
       CA_SRC_KEEP="${SRC}/keep" CA_SRC_TMPMD="${SRC}/tmpmd" CA_SRC_CLAUDE_TMP="${SRC}/claudetmp" \
       CA_DATADIR="${DD}" CA_SESSIONS_DIR="${SESS}" \
       CA_MOVE_DAYS=7 CA_POLL_SEC=0.05 CA_DETACH_RETRY_SEC=0 CA_TIMEOUT_ATTACH=20 CA_TIMEOUT_DETACH=20 CA_TIMEOUT_RSYNC=60
NOW="$(date +%s)"
export CA_NOW="${NOW}"

# K9: 差し替え対象は全て一時ディレクトリの下（実機の security・hdiutil・HDD・osascript・dataDir を呼ばない）
env_all_under_T() {
  local v val bad=0
  for v in CA_HDD_MOUNT CA_IMAGE CA_SECURITY_CMD CA_HDIUTIL_CMD CA_RSYNC_CMD CA_OSASCRIPT_CMD CA_LOG_FILE CA_LAST_OK \
           CA_LOCK_DIR CA_MNT_PARENT CA_SRC_PROJECTS CA_SRC_HISTORY CA_SRC_PLANS CA_SRC_KEEP CA_SRC_TMPMD CA_SRC_CLAUDE_TMP \
           CA_DATADIR CA_SESSIONS_DIR STUB_CALLS STUB_VOL; do
    val="${!v:-}"
    case "${val}" in "${T}"/*) ;; *) echo "  T の外: ${v}=${val}"; bad=1 ;; esac
  done
  return ${bad}
}
if ! env_all_under_T; then ng "K9 試験の設定が一時ディレクトリの外を指している。中止"; exit 1; fi
ok "K9 全ての CA_* がスタブまたは一時ディレクトリの下"

# ── 部品 ────────────────────────────────────────────────────────────────────
SLUG="-Users-t-proj"
UA="aaaaaaaa-0000-4000-8000-000000000001"   # open-sessions にある
UB="bbbbbbbb-0000-4000-8000-000000000002"   # sessions/ にある
UC="cccccccc-0000-4000-8000-000000000003"   # どちらにも無い
UD="dddddddd-0000-4000-8000-000000000004"   # 写しと不一致にする
UE="eeeeeeee-0000-4000-8000-000000000005"   # 1日前
D8=$(( NOW - 8 * 86400 )); D1=$(( NOW - 86400 ))

touch_at() { local ts; ts="$(date -r "$1" +%Y%m%d%H%M.%S)"; shift; touch -h -t "${ts}" "$@"; }
mk_session() { # mk_session <uuid> <epoch>
  local d="${SRC}/projects/${SLUG}"
  mkdir -p "${d}/$1/subagents" "${d}/$1/tool-results"
  echo line > "${d}/$1.jsonl"; echo sub > "${d}/$1/subagents/a.jsonl"; echo res > "${d}/$1/tool-results/r.txt"
  touch_at "$2" "${d}/$1.jsonl" "${d}/$1/subagents/a.jsonl" "${d}/$1/tool-results/r.txt"
}
fresh_env() { # 元・入れ物・ログ・呼び出し記録を作り直す
  wipe "${SRC}"; wipe "${VOL}"; wipe "${MNT}"; wipe "${HDD}"; wipe "${DD}"; wipe "${SESS}"; wipe "${T}/lock.d"; wipe "${STUB_INFO_PLIST}"
  rm -f -- "${CA_LAST_OK}"
  mkdir -p "${VOL}" "${MNT}" "${HDD}/claude-archive.sparsebundle" "${DD}/boards" "${SESS}" \
           "${SRC}/projects/${SLUG}/memory" "${SRC}/projects/${SLUG}/notuuid" "${SRC}/plans" "${SRC}/keep" "${SRC}/tmpmd/sub" \
           "${SRC}/claudetmp/slugA/${UA}/images" "${SRC}/claudetmp/slugA/${UC}/images" "${SRC}/claudetmp/slugA/${UC}/scratchpad/images"
  mk_session "${UA}" "${D8}"; mk_session "${UB}" "${D8}"; mk_session "${UC}" "${D8}"; mk_session "${UD}" "${D8}"; mk_session "${UE}" "${D1}"
  echo mem > "${SRC}/projects/${SLUG}/memory/MEMORY.md"; echo x > "${SRC}/projects/${SLUG}/notuuid/x.txt"
  echo y > "${SRC}/projects/${SLUG}/notuuid.jsonl"
  touch_at "${D8}" "${SRC}/projects/${SLUG}/memory/MEMORY.md" "${SRC}/projects/${SLUG}/notuuid/x.txt" "${SRC}/projects/${SLUG}/notuuid.jsonl"
  echo h > "${SRC}/history.jsonl"; touch_at "${D8}" "${SRC}/history.jsonl"
  echo old > "${SRC}/plans/old.md"; echo new > "${SRC}/plans/new.md"; ln -s old.md "${SRC}/plans/linkold.md"
  touch_at "${D8}" "${SRC}/plans/old.md" "${SRC}/plans/linkold.md"; touch_at "${D1}" "${SRC}/plans/new.md"
  echo k > "${SRC}/keep/doc.txt"; touch_at "${D8}" "${SRC}/keep/doc.txt"
  echo o > "${SRC}/tmpmd/sub/old.md"; echo n > "${SRC}/tmpmd/sub/new.md"; echo t > "${SRC}/tmpmd/sub/x.txt"
  touch_at "${D8}" "${SRC}/tmpmd/sub/old.md" "${SRC}/tmpmd/sub/x.txt"; touch_at "${D1}" "${SRC}/tmpmd/sub/new.md"
  echo p > "${SRC}/claudetmp/slugA/${UA}/images/pic.png"; echo p > "${SRC}/claudetmp/slugA/${UC}/images/old.png"
  echo p > "${SRC}/claudetmp/slugA/${UC}/images/new.png"; echo p > "${SRC}/claudetmp/slugA/${UC}/scratchpad/images/ex.png"
  touch_at "${D8}" "${SRC}/claudetmp/slugA/${UA}/images/pic.png" "${SRC}/claudetmp/slugA/${UC}/images/old.png" "${SRC}/claudetmp/slugA/${UC}/scratchpad/images/ex.png"
  touch_at "${D1}" "${SRC}/claudetmp/slugA/${UC}/images/new.png"
  # 実機の slug は "-Users-..." のように "-" で始まる。相対パスが rsync のオプション扱いにならないことの回帰試験
  mkdir -p "${SRC}/claudetmp/-dashslug/${UC}/images"; echo p > "${SRC}/claudetmp/-dashslug/${UC}/images/dash.png"
  touch_at "${D1}" "${SRC}/claudetmp/-dashslug/${UC}/images/dash.png"
  echo '{}' > "${DD}/boards/b.json"; echo '{}' > "${DD}/routine-audit.jsonl"
  printf '{"version":1,"items":[{"id":"1","roleId":"r","name":"n","cwd":"/x","claudeSessionId":"%s"}]}\n' "${UA}" > "${DD}/open-sessions.json"
  printf '{"pid":123,"sessionId":"%s","cwd":"/x"}\n' "${UB}" > "${SESS}/123.json"
  : > "${STUB_CALLS}"; : > "${CA_LOG_FILE}"
}
src_snapshot() { find -P "${SRC}" "${DD}" "${SESS}" -exec stat -f '%N %z %m' {} + 2>/dev/null | sort; }
n_calls() { grep -c -- "$1" "${STUB_CALLS}" 2>/dev/null || true; }
run_ca() { bash "${CA}" "$@" >"${T}/out.txt" 2>"${T}/err.txt"; RC=$?; }
hdd_ls() { ls -A "${HDD}" | sort; }
VMOVELOG() { echo "${VOL}/move-log/$(date -r "${NOW}" +%Y%m%d).txt"; }

# ── 1. K2: HDD が無いと何も書かず「HDD なし」で exit 0、last-ok は変わらない ──────────
fresh_env
CA_HDD_MOUNT="${T}/nohdd" CA_IMAGE="${T}/nohdd/claude-archive.sparsebundle" run_ca --execute
check "K2 HDD なし: exit 0" [ "${RC}" -eq 0 ]
check "K2 HDD なし: ログに「HDD なし」" grep -q "HDD なし" "${CA_LOG_FILE}"
check "K2 HDD なし: last-ok を作らない" gone "${CA_LAST_OK}"
check "K2 HDD なし: hdiutil・security・rsync を呼ばない" bash -c '! grep -Eq "^(hdiutil|security|rsync)" "$1"' _ "${STUB_CALLS}"
check "K2 HDD なし: 入れ物（fakevol）に何も書かない" [ -z "$(ls -A "${VOL}")" ]
check "K2 HDD なし: 元が消えない" exists "${SRC}/plans/old.md"

# ── 2. K4: 通知 ───────────────────────────────────────────────────────────────
check "K4 last-ok が無い: 通知が呼ばれる（K2 の実行）" [ "$(n_calls '^osascript')" -eq 1 ]
: > "${STUB_CALLS}"; echo $(( NOW - 3600 )) > "${CA_LAST_OK}"
CA_HDD_MOUNT="${T}/nohdd" CA_IMAGE="${T}/nohdd/x" run_ca
check "K4 last-ok が新しい（1時間前）: 通知が呼ばれない" [ "$(n_calls '^osascript')" -eq 0 ]
echo $(( NOW - 4 * 86400 )) > "${CA_LAST_OK}"
CA_HDD_MOUNT="${T}/nohdd" CA_IMAGE="${T}/nohdd/x" run_ca
check "K4 last-ok が4日前: 通知が呼ばれる" [ "$(n_calls '^osascript')" -eq 1 ]
echo $(( NOW - 4 * 86400 )) > "${CA_LAST_OK}"
check "K2 HDD なし: last-ok は変わらない（4日前のまま）" [ "$(tr -dc 0-9 < "${CA_LAST_OK}")" = "$(( NOW - 4 * 86400 ))" ]

# ── 3. 通常の1回（dry-run）: K1 相当・K5・K11④ ───────────────────────────────────
fresh_env
HDD_BEFORE="$(hdd_ls)"
SNAP_BEFORE="$(src_snapshot)"
run_ca
echo "=== dry-run ログ ==="; cat "${CA_LOG_FILE}"; echo "=== ここまで ==="
check "dry-run: exit 0" [ "${RC}" -eq 0 ]
check "dry-run: 合言葉の取得 1 回" [ "$(n_calls '^security find-generic-password -s claude-archive-hdd -a archive -w')" -eq 1 ]
check "dry-run: attach の標準入力が合言葉（末尾改行なし）" grep -q "attach stdin==secret(no newline)" "${STUB_CALLS}"
check "dry-run: attach 1 回・detach 1 回" bash -c '[ "$(grep -c "^hdiutil attach" "$1")" -eq 1 ] && [ "$(grep -c "^hdiutil detach" "$1")" -eq 1 ]' _ "${STUB_CALLS}"
check "dry-run: 開く場所は mktemp -d（CA_MNT_PARENT の下）" grep -q "attach mountpoint=${MNT}/claude-archive-mnt\." "${STUB_CALLS}"
check "dry-run: 閉じたあと開く場所が残らない" [ -z "$(ls -A "${MNT}")" ]
check "dry-run: last-ok に CA_NOW" [ "$(tr -dc 0-9 < "${CA_LAST_OK}")" = "${NOW}" ]
check "dry-run: 元が変わらない（前後の一覧が同一）" [ "${SNAP_BEFORE}" = "$(src_snapshot)" ]
check "dry-run: 片付けの一覧のみ（消す予定の記録）" grep -q "片付け セッション: .*消す予定 2" "${CA_LOG_FILE}"
check "dry-run: move-log を作らない" gone "${VOL}/move-log"
check "写し: projects（jsonl と subagents）" bash -c '[ -f "$1/claude/projects/$2/$3.jsonl" ] && [ -f "$1/claude/projects/$2/$3/subagents/a.jsonl" ]' _ "${VOL}" "${SLUG}" "${UC}"
check "写し: memory" exists "${VOL}/claude/projects/${SLUG}/memory/MEMORY.md"
check "写し: history・plans・keep" bash -c '[ -f "$1/claude/history.jsonl" ] && [ -f "$1/claude/plans/old.md" ] && [ -f "$1/CC報告ファイル-keep/doc.txt" ]' _ "${VOL}"
check "写し: tmpmd は .md だけ" bash -c '[ -f "$1/tmp-CC報告ファイル-md/sub/old.md" ] && [ ! -e "$1/tmp-CC報告ファイル-md/sub/x.txt" ]' _ "${VOL}"
check "写し: images は構造を保つ（scratchpad の下は写さない）" bash -c '[ -f "$1/claude-tmp-images/slugA/$2/images/old.png" ] && [ ! -e "$1/claude-tmp-images/slugA/$3/scratchpad" ]' _ "${VOL}" "${UC}" "${UC}"
check "写し: dataDir の boards・routine-audit" bash -c '[ -f "$1/agent-console/boards/b.json" ] && [ -f "$1/agent-console/routine-audit.jsonl" ]' _ "${VOL}"
check "K5 入れ物の外（HDD 直下）に書かない" [ "${HDD_BEFORE}" = "$(hdd_ls)" ]
check "写し: slug が - で始まる images も写る（rsync の -- 回帰）" exists "${VOL}/claude-tmp-images/-dashslug/${UC}/images/dash.png"
check "K5 入れ物の直下は決めた名前だけ" bash -c '[ "$(ls -A "$1" | LC_ALL=C sort | tr "\n" " ")" = "$(printf "%s\n" CC報告ファイル-keep agent-console claude claude-tmp-images tmp-CC報告ファイル-md | LC_ALL=C sort | tr "\n" " ")" ]' _ "${VOL}"
check "K5 ログに合言葉が出ない" lacks "${STUB_SECRET}" "${CA_LOG_FILE}"
check "K5 標準出力に合言葉が出ない" lacks "${STUB_SECRET}" "${T}/out.txt"
check "K5 標準エラーに合言葉が出ない" lacks "${STUB_SECRET}" "${T}/err.txt"
check "K5 呼び出し記録（引数）に合言葉が出ない" lacks "${STUB_SECRET}" "${STUB_CALLS}"
check "rsync に --delete を渡さない" lacks "--delete" "${STUB_CALLS}"

# ── 4. K11 ①⑤: --execute ───────────────────────────────────────────────────
fresh_env
run_ca --execute
echo "=== execute ログ ==="; cat "${CA_LOG_FILE}"; echo "=== ここまで ==="
P="${SRC}/projects/${SLUG}"
check "execute: exit 0" [ "${RC}" -eq 0 ]
check "K11① open-sessions にあるセッションは残る（jsonl と配下）" bash -c '[ -f "$1/$2.jsonl" ] && [ -f "$1/$2/subagents/a.jsonl" ]' _ "${P}" "${UA}"
check "K11① sessions/ にあるセッションは残る" bash -c '[ -f "$1/$2.jsonl" ] && [ -f "$1/$2/tool-results/r.txt" ]' _ "${P}" "${UB}"
check "K11① どちらにも無いセッションだけ消える（jsonl）" gone "${P}/${UC}.jsonl"
check "K11① どちらにも無いセッションだけ消える（配下とディレクトリ）" gone "${P}/${UC}"
check "K11⑤ 7日以内のセッションは残る" exists "${P}/${UE}.jsonl"
check "K11⑤ memory/ は 8日前でも残る" exists "${P}/memory/MEMORY.md"
check "K11 UUID でない物は残る（ディレクトリ・jsonl）" bash -c '[ -f "$1/notuuid/x.txt" ] && [ -f "$1/notuuid.jsonl" ]' _ "${P}"
check "K11 消した物は入れ物の中に在る" exists "${VOL}/claude/projects/${SLUG}/${UC}.jsonl"
check "K12 move-log に消したセッションの名前が載る" grep -q "${UC}.jsonl" "$(VMOVELOG)"
check "K12 move-log に残した（開いている）セッションの名前は載らない" lacks "${UA}" "$(VMOVELOG)"
check "K11 計画: 8日前は消え、新しい物は残る" bash -c '[ ! -e "$1/plans/old.md" ] && [ -f "$1/plans/new.md" ]' _ "${SRC}"
check "K11 計画: シンボリックリンクは消さない" exists "${SRC}/plans/linkold.md"
check "K11 文書: 古い .md は消え、新しい物と .md でない物は残る" bash -c '[ ! -e "$1/tmpmd/sub/old.md" ] && [ -f "$1/tmpmd/sub/new.md" ] && [ -f "$1/tmpmd/sub/x.txt" ]' _ "${SRC}"
check "K11 画像: 開いているセッションの images は残る" exists "${SRC}/claudetmp/slugA/${UA}/images/pic.png"
check "K11 画像: 古い画像は消え、新しい画像は残る" bash -c '[ ! -e "$1/claudetmp/slugA/$2/images/old.png" ] && [ -f "$1/claudetmp/slugA/$2/images/new.png" ]' _ "${SRC}" "${UC}"
check "K11 画像: scratchpad の下の images は触らない" exists "${SRC}/claudetmp/slugA/${UC}/scratchpad/images/ex.png"
check "K11 keep・history・dataDir は消さない" bash -c '[ -f "$1/keep/doc.txt" ] && [ -f "$1/history.jsonl" ] && [ -f "$2/boards/b.json" ] && [ -f "$2/open-sessions.json" ]' _ "${SRC}" "${DD}"
check "execute: ログに単位ごとの行" bash -c 'grep -q "片付け 計画:" "$1" && grep -q "片付け 文書:" "$1" && grep -q "片付け 画像:" "$1" && grep -q "片付け セッション:" "$1"' _ "${CA_LOG_FILE}"
check "execute: rm -rf を使っていない（スクリプト内に無い）" bash -c '! grep -Eq "^[^#]*rm +-[a-zA-Z]*r" "$1"' _ "${CA}"

# ── 5. K11②: 写し先の1ファイルの大きさが違うセッションは丸ごと残る ─────────────────────
fresh_env
STUB_RSYNC_CORRUPT="${VOL}/claude/projects/${SLUG}/${UD}/subagents/a.jsonl" run_ca --execute
check "K11② exit 0" [ "${RC}" -eq 0 ]
check "K11② 不一致のセッションは丸ごと残る（jsonl と配下の全ファイル）" bash -c '[ -f "$1/$2.jsonl" ] && [ -f "$1/$2/subagents/a.jsonl" ] && [ -f "$1/$2/tool-results/r.txt" ]' _ "${P}" "${UD}"
check "K11② ログに残した理由" grep -q "写しと不一致のため丸ごと残す" "${CA_LOG_FILE}"
check "K11② 一致する別セッション(UC)は消える" gone "${P}/${UC}.jsonl"

# ── 6. K11③: version:2 でセッション単位が全見送り（計画・文書・画像は続く）──────────────
fresh_env
printf '{"version":2,"items":[]}\n' > "${DD}/open-sessions.json"
run_ca --execute
check "K11③ exit 0" [ "${RC}" -eq 0 ]
check "K11③ どのセッションも消えない（UC も残る）" bash -c '[ -f "$1/$2.jsonl" ] && [ -f "$1/$3.jsonl" ] && [ -f "$1/$4.jsonl" ] && [ -f "$1/$5.jsonl" ]' _ "${P}" "${UA}" "${UB}" "${UC}" "${UD}"
check "K11③ ログに「セッション単位の片付けを全部見送り」" grep -q "セッション単位の片付けを全部見送り" "${CA_LOG_FILE}"
check "K11③ 計画は続く" gone "${SRC}/plans/old.md"
check "K11③ 文書は続く" gone "${SRC}/tmpmd/sub/old.md"
check "K11③ 画像は続く" gone "${SRC}/claudetmp/slugA/${UC}/images/old.png"
# sessions/ の json が読めない場合も全見送り
fresh_env
echo 'not json' > "${SESS}/999.json"
run_ca --execute
check "K11③' sessions/ に読めない json: セッションを消さない" exists "${P}/${UC}.jsonl"
# open-sessions.json が無い場合も全見送り
fresh_env
rm -f -- "${DD}/open-sessions.json"
run_ca --execute
check "K11③'' open-sessions.json が無い: セッションを消さない" exists "${P}/${UC}.jsonl"
# 退避側（tmux-held）に claudeSessionId があれば守る
fresh_env
printf '{"version":1,"items":[{"id":"2","roleId":"r","name":"n","cwd":"/x","claudeSessionId":"%s"}]}\n' "${UC}" > "${DD}/open-sessions.tmux-held.json"
run_ca --execute
check "K11 退避側 open-sessions.tmux-held.json のセッションも守る" exists "${P}/${UC}.jsonl"

# ── 7. K7: 1項目が失敗しても残りを写し、last-ok を更新せず exit 1 ──────────────────────
fresh_env
STUB_RSYNC_FAIL="/tmpmd/" run_ca --execute
check "K7 exit 1" [ "${RC}" -eq 1 ]
check "K7 失敗項目より後ろの項目も写す（history・dataDir）" bash -c '[ -f "$1/claude/history.jsonl" ] && [ -f "$1/agent-console/boards/b.json" ]' _ "${VOL}"
check "K7 last-ok を更新しない" gone "${CA_LAST_OK}"
check "K7 ログに失敗項目 NG" grep -q "item=tmpmd rc=23 .* NG" "${CA_LOG_FILE}"
check "K7 片付け見送り（何も消えない）" bash -c '[ -f "$1/$2.jsonl" ] && [ -f "$3/plans/old.md" ]' _ "${P}" "${UC}" "${SRC}"
check "K7 ログに「片付け見送り」" grep -q "片付け見送り" "${CA_LOG_FILE}"
check "K7 閉じる（detach 1 回）" [ "$(n_calls '^hdiutil detach')" -eq 1 ]

# ── 8. K10: detach が失敗しても写しが全て成功していれば last-ok は書かれ、exit 1 ────────
fresh_env
STUB_DETACH_FAIL=1 run_ca --execute
check "K10 exit 1" [ "${RC}" -eq 1 ]
check "K10 last-ok は書かれる" [ "$(tr -dc 0-9 < "${CA_LAST_OK}")" = "${NOW}" ]
check "K10 ログに「detach 失敗」" grep -q "detach 失敗" "${CA_LOG_FILE}"
check "K10 detach を 3 回試す（trap で増えない）" [ "$(n_calls '^hdiutil detach')" -eq 3 ]
check "K10 片付けは detach の前に済んでいる（UC が消えている）" gone "${P}/${UC}.jsonl"

# ── 9. 既に開いている入れ物（C3）: attach も detach もしない ─────────────────────────
fresh_env
cat > "${STUB_INFO_PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict><key>images</key><array>
<dict><key>image-path</key><string>${T}/hdd/other.sparsebundle</string><key>system-entities</key><array><dict><key>mount-point</key><string>${T}/not-this</string></dict></array></dict>
<dict><key>image-path</key><string>${CA_IMAGE}</string><key>system-entities</key><array><dict><key>dev-entry</key><string>/dev/disk9</string></dict><dict><key>mount-point</key><string>${VOL}</string></dict></array></dict>
</array></dict></plist>
EOF
run_ca
check "既に開いている: exit 0" [ "${RC}" -eq 0 ]
check "既に開いている: attach しない" [ "$(n_calls '^hdiutil attach')" -eq 0 ]
check "既に開いている: detach しない（自分で開いていない）" [ "$(n_calls '^hdiutil detach')" -eq 0 ]
check "既に開いている: security を呼ばない" [ "$(n_calls '^security')" -eq 0 ]
check "既に開いている: 既存の入れ物へ写す" exists "${VOL}/claude/history.jsonl"

# ── 10. 開けない／上限時間 ───────────────────────────────────────────────────────
fresh_env
STUB_ATTACH_FAIL=1 run_ca --execute
check "attach 失敗: exit 1" [ "${RC}" -eq 1 ]
check "attach 失敗: rsync を呼ばない・last-ok を書かない・何も消えない" bash -c '! grep -q "^rsync" "$1" && [ ! -e "$2" ] && [ -f "$3/$4.jsonl" ]' _ "${STUB_CALLS}" "${CA_LAST_OK}" "${P}" "${UC}"
check "attach 失敗: 通知が呼ばれる（last-ok なし）" [ "$(n_calls '^osascript')" -eq 1 ]
check "attach 失敗: 開く場所が残らない" [ -z "$(ls -A "${MNT}")" ]
fresh_env
STUB_ATTACH_SLEEP=6 CA_TIMEOUT_ATTACH=1 run_ca --execute
check "上限時間超え: exit 1" [ "${RC}" -eq 1 ]
check "上限時間超え: ログに rc=124" grep -q "入れ物を開けない rc=124" "${CA_LOG_FILE}"
check "上限時間超え: 何も写さない" bash -c '! grep -q "^rsync" "$1"' _ "${STUB_CALLS}"

# ── 11. ロックと引数 ─────────────────────────────────────────────────────────
fresh_env
mkdir -p "${CA_LOCK_DIR}"
run_ca
check "ロック中: 実行せず skip（exit 0）" bash -c '[ "$1" -eq 0 ] && grep -q "another instance is running" "$2" && [ ! -s "$3" ]' _ "${RC}" "${CA_LOG_FILE}" "${STUB_CALLS}"
rmdir "${CA_LOCK_DIR}"
run_ca --bogus
check "不明な引数: exit 2" [ "${RC}" -eq 2 ]
fresh_env
run_ca
check "実行後にロックが解除される" gone "${CA_LOCK_DIR}"
# ログの世代: 上限超えは .1 に1世代
head -c 3000 /dev/zero | tr '\0' 'x' > "${CA_LOG_FILE}"
CA_LOG_MAX_BYTES=100 run_ca
check "ログ: 上限超えは .1 に退避され1世代だけ" bash -c '[ -f "$1.1" ] && [ ! -e "$1.2" ]' _ "${CA_LOG_FILE}"

echo ""
echo "=== 合計 ==="
echo "ok: ${OK}"
echo "ng: ${NG}"
if [ "${NG}" -gt 0 ]; then
  echo "試験失敗あり"
  exit 1
fi
echo "全試験 ok"
exit 0
