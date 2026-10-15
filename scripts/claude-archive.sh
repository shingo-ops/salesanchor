#!/bin/bash
# claude-archive.sh — 残すデータを毎日 HDD の鍵付きの入れ物へ写し、写した物を Mac から片付ける
# （docs/handoff/claude-archive/design.md §4）
#
#   1 ロック → 2 HDD の確認 → 3 入れ物を開く → 4 写す（足すだけ・--delete なし）→ 5 確かめる
#   → 6 last-ok → 7 片付け（写しが全項目成功したときだけ）→ 8 閉じる → 9 通知 → 10 終了とログ
#
# 使い方:
#   bash scripts/claude-archive.sh            # 写す。片付けは dry-run（一覧だけ）
#   bash scripts/claude-archive.sh --execute  # 写す。片付けも実行（LaunchAgent はこちら）
#
# 設定（CA_ で始まる環境変数で上書きできる。試験用）は ca_config に1か所でまとめてある。
# 合言葉はシェル変数に入れず、security → tr → hdiutil のパイプで直接渡す。set -x / bash -x は使わない。
# set -e は使わない（1項目の失敗で残りを止めないため。各手順の rc を見る）。
# このファイルは source できる。source 時は何も実行しない。

set -u

# ── 設定（1か所）─────────────────────────────────────────────────────────────
ca_config() {
  local h="${HOME:-/Users/tanizawashingo}"
  : "${CA_HDD_MOUNT:=/Volumes/HIGHLIFEJPN HDD}"
  : "${CA_IMAGE:=${CA_HDD_MOUNT}/claude-archive.sparsebundle}"
  : "${CA_SECURITY_CMD:=security}"
  : "${CA_HDIUTIL_CMD:=hdiutil}"
  : "${CA_RSYNC_CMD:=/usr/bin/rsync}"
  : "${CA_OSASCRIPT_CMD:=osascript}"
  : "${CA_LOG_FILE:=${h}/Library/Logs/claude-archive.log}"
  : "${CA_LOG_MAX_BYTES:=1048576}"
  : "${CA_LAST_OK:=${h}/Library/Logs/claude-archive.last-ok}"
  : "${CA_LOCK_DIR:=/tmp/claude-archive.lock.d}"
  : "${CA_MNT_PARENT:=/tmp}"
  : "${CA_NOW:=$(date +%s)}"
  : "${CA_SRC_PROJECTS:=${h}/.claude/projects}"
  : "${CA_SRC_HISTORY:=${h}/.claude/history.jsonl}"
  : "${CA_SRC_PLANS:=${h}/.claude/plans}"
  : "${CA_SRC_KEEP:=${h}/CC報告ファイル-keep}"
  : "${CA_SRC_TMPMD:=/private/tmp/CC報告ファイル}"
  : "${CA_SRC_CLAUDE_TMP:=/private/tmp/claude-501}"
  : "${CA_DATADIR:=${h}/Library/Application Support/agent-console}"
  : "${CA_SESSIONS_DIR:=${h}/.claude/sessions}"
  : "${CA_MOVE_DAYS:=7}"
  : "${CA_NOTIFY_SEC:=259200}"             # 3日
  : "${CA_TIMEOUT_ATTACH:=150}"            # 合言葉の取得から attach までのパイプライン全体
  : "${CA_TIMEOUT_DETACH:=120}"            # detach 1回
  : "${CA_TIMEOUT_RSYNC:=3600}"            # rsync 1項目
  : "${CA_DETACH_RETRY_SEC:=10}"
  : "${CA_POLL_SEC:=1}"
}

# ── 共通部品 ─────────────────────────────────────────────────────────────────
CA_MP=""              # 入れ物の中身が見える場所（自分で開いたときは mktemp -d の場所）
CA_OPENED_BY_ME=0
CA_DETACH_DONE=0
CA_LOCKED=0
CA_FAIL_COPY=0
CA_FAIL_CLEAN=0
CA_FAIL_DETACH=0
CA_FAIL_OPEN=0
CA_TMPFILES=()

ca_log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

# ca_run_timeout <秒> <コマンド...>: 背景実行 → CA_POLL_SEC ごとに確認 → 超えたら kill（macOS に timeout が無いため）。超過は 124。
ca_run_timeout() {
  local secs="$1" pid start
  shift
  "$@" &
  pid=$!
  start="${SECONDS}"
  while kill -0 "${pid}" 2>/dev/null; do
    if [ $(( SECONDS - start )) -ge "${secs}" ]; then
      pkill -P "${pid}" 2>/dev/null || true
      kill "${pid}" 2>/dev/null || true
      sleep 1
      kill -9 "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
      return 124
    fi
    sleep "${CA_POLL_SEC}"
  done
  wait "${pid}"
}

ca_tmpfile() { # 一時ファイルを作り、パスを CA_TMPF に入れる（trap で消す）
  CA_TMPF="$(mktemp "${TMPDIR:-/tmp}/claude-archive.XXXXXX")" || return 1
  CA_TMPFILES+=("${CA_TMPF}")
}

ca_setup_log() {
  [ -n "${CA_LOG_FILE}" ] || return 0
  mkdir -p "$(dirname "${CA_LOG_FILE}")" 2>/dev/null || true
  if [ -f "${CA_LOG_FILE}" ]; then
    local sz
    sz="$(wc -c <"${CA_LOG_FILE}" | tr -d ' ')"
    if [ "${sz:-0}" -gt "${CA_LOG_MAX_BYTES}" ]; then mv -f -- "${CA_LOG_FILE}" "${CA_LOG_FILE}.1"; fi
  fi
  exec >>"${CA_LOG_FILE}" 2>&1
}

ca_detach_once() { # 1回 detach。成功したら 0
  ca_run_timeout "${CA_TIMEOUT_DETACH}" "${CA_HDIUTIL_CMD}" detach "${CA_MP}" >/dev/null 2>&1
}

ca_trap() { # EXIT INT TERM: 開いたままなら detach、mktemp の場所は rmdir、ロック解除
  local f
  if [ "${CA_OPENED_BY_ME}" -eq 1 ] && [ "${CA_DETACH_DONE}" -eq 0 ]; then
    ca_detach_once && CA_OPENED_BY_ME=0
  fi
  if [ -n "${CA_MP}" ] && [ "${CA_MP_CREATED:-0}" -eq 1 ] && [ "${CA_OPENED_BY_ME}" -eq 0 ]; then
    rmdir "${CA_MP}" 2>/dev/null || true
  fi
  for f in ${CA_TMPFILES[@]+"${CA_TMPFILES[@]}"}; do rm -f -- "${f}" 2>/dev/null || true; done
  if [ "${CA_LOCKED}" -eq 1 ]; then rmdir "${CA_LOCK_DIR}" 2>/dev/null || true; fi
}

# ── 3 入れ物を開く ───────────────────────────────────────────────────────────
ca_find_mounted() { # 既に開いているなら mount-point を標準出力へ（C3）。無い・読めないなら何も出さず 1
  local json
  json="$("${CA_HDIUTIL_CMD}" info -plist 2>/dev/null | plutil -convert json -o - - 2>/dev/null)" || return 1
  [ -n "${json}" ] || return 1
  printf '%s' "${json}" | python3 -I -c '
import json, sys
image = sys.argv[1]
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for im in d.get("images", []) or []:
    if im.get("image-path") != image:
        continue
    for ent in im.get("system-entities", []) or []:
        mp = ent.get("mount-point")
        if mp:
            print(mp)
            sys.exit(0)
sys.exit(1)
' "${CA_IMAGE}"
}

ca_open() { # 成功したら CA_MP に中身の場所
  local existing out_file rc
  if existing="$(ca_find_mounted)" && [ -n "${existing}" ] && [ -d "${existing}" ]; then
    CA_MP="${existing}"; CA_OPENED_BY_ME=0
    ca_log "入れ物は既に開いている（自分では閉じない）: ${CA_MP}"
    return 0
  fi
  CA_MP="$(mktemp -d "${CA_MNT_PARENT}/claude-archive-mnt.XXXXXX")" || { ca_log "[失敗] 開く場所を作れない"; return 1; }
  CA_MP_CREATED=1
  ca_tmpfile || return 1
  out_file="${CA_TMPF}"
  # 合言葉はシェル変数に入れない。パイプ全体で上限時間を持つ。
  ca_run_timeout "${CA_TIMEOUT_ATTACH}" bash -c \
    '"$1" find-generic-password -s claude-archive-hdd -a archive -w | tr -d "\n" | "$2" attach -stdinpass -nobrowse -mountpoint "$3" "$4"' \
    _ "${CA_SECURITY_CMD}" "${CA_HDIUTIL_CMD}" "${CA_MP}" "${CA_IMAGE}" >"${out_file}" 2>&1
  rc=$?
  if [ "${rc}" -ne 0 ]; then
    ca_log "[失敗] 入れ物を開けない rc=${rc}（124 は上限時間超え）"
    head -n 5 "${out_file}" | sed 's/^/    /'
    return 1
  fi
  CA_OPENED_BY_ME=1
  ca_log "入れ物を開いた: ${CA_MP}"
  return 0
}

# ── 4・5 写す／確かめる ──────────────────────────────────────────────────────
ca_count() { # ca_count <path> <name glob>: ファイル数（無ければ 0）
  if [ -f "$1" ]; then echo 1; return 0; fi
  if [ -d "$1" ]; then find -P "$1" -type f -name "$2" 2>/dev/null | wc -l | tr -d ' '; return 0; fi
  echo 0
}

ca_diff_lines() { # rsync -ani の行数（記録のみ）
  local src="$1" dst="$2"; shift 2
  "${CA_RSYNC_CMD}" -a -n -i "$@" "${src}" "${dst}" 2>/dev/null | wc -l | tr -d ' '
}

# ca_copy <項目名> <元> <先> <数える名前glob> [rsync の追加引数...]
#   元がディレクトリなら末尾 / 付きで中身を写す。元が無ければ「元 0」で成功扱い。
ca_copy() {
  local name="$1" src="$2" dst="$3" cglob="$4" rc=0 s d nd result="OK"
  shift 4
  if [ ! -e "${src}" ]; then
    ca_log "item=${name} 元なし（元 0）→ 成功扱い"
    return 0
  fi
  s="$(ca_count "${src}" "${cglob}")"
  if [ -d "${src}" ]; then
    mkdir -p "${dst}" || { ca_log "item=${name} [失敗] 先を作れない"; CA_FAIL_COPY=1; return 1; }
    ca_run_timeout "${CA_TIMEOUT_RSYNC}" "${CA_RSYNC_CMD}" -a "$@" "${src}/" "${dst}/" >/dev/null 2>&1; rc=$?
    d="$(ca_count "${dst}" "${cglob}")"
    nd="$(ca_diff_lines "${src}/" "${dst}/" "$@")"
  else
    mkdir -p "$(dirname "${dst}")" || { ca_log "item=${name} [失敗] 先を作れない"; CA_FAIL_COPY=1; return 1; }
    ca_run_timeout "${CA_TIMEOUT_RSYNC}" "${CA_RSYNC_CMD}" -a "$@" "${src}" "${dst}" >/dev/null 2>&1; rc=$?
    d="$(ca_count "${dst}" "${cglob}")"
    nd="$(ca_diff_lines "${src}" "${dst}" "$@")"
  fi
  if [ "${rc}" -ne 0 ] || { [ "${s}" -ge 1 ] && [ "${d}" -eq 0 ]; }; then result="NG"; CA_FAIL_COPY=1; fi
  ca_log "item=${name} rc=${rc} src=${s} dst=${d} diff=${nd} ${result}"
  [ "${result}" = "OK" ]
}

ca_copy_images() { # images: 各 <slug>/<uuid>/images/ ごとに -R で構造を保って写す（scratchpad の下の images は対象外）
  local root="${CA_SRC_CLAUDE_TMP}" dst="$1/claude-tmp-images" imgs p rel rc=0 s=0 d=0 n=0 one result="OK"
  if [ ! -d "${root}" ]; then ca_log "item=images 元なし（元 0）→ 成功扱い"; return 0; fi
  ca_tmpfile || return 1
  imgs="${CA_TMPF}"
  find -P "${root}" -mindepth 3 -maxdepth 3 -type d -name images 2>/dev/null | sort >"${imgs}"
  mkdir -p "${dst}" || { ca_log "item=images [失敗] 先を作れない"; CA_FAIL_COPY=1; return 1; }
  while IFS= read -r p; do
    [ -n "${p}" ] || continue
    rel="${p#"${root}"/}"
    n=$(( n + 1 ))
    one="$(ca_count "${p}" '*')"; s=$(( s + one ))
    # openrsync は元の "/./" を無視する（実測）ので、根へ cd して相対パスで -R を使う
    ca_run_timeout "${CA_TIMEOUT_RSYNC}" bash -c 'cd "$1" && exec "$2" -a -R -- "$3" "$4"' _ "${root}" "${CA_RSYNC_CMD}" "${rel}/" "${dst}/" >/dev/null 2>&1 || rc=$?
    d=$(( d + $(ca_count "${dst}/${rel}" '*') ))
  done <"${imgs}"
  if [ "${rc}" -ne 0 ] || { [ "${s}" -ge 1 ] && [ "${d}" -eq 0 ]; }; then result="NG"; CA_FAIL_COPY=1; fi
  ca_log "item=images places=${n} rc=${rc} src=${s} dst=${d} ${result}"
  [ "${result}" = "OK" ]
}

ca_copy_all() { # ca_copy_all <入れ物の中身の場所>
  local V="$1" dd="${CA_DATADIR}"
  ca_copy projects "${CA_SRC_PROJECTS}" "${V}/claude/projects" '*'
  ca_copy history  "${CA_SRC_HISTORY}"  "${V}/claude/history.jsonl" '*'
  ca_copy plans    "${CA_SRC_PLANS}"    "${V}/claude/plans" '*'
  ca_copy keep     "${CA_SRC_KEEP}"     "${V}/CC報告ファイル-keep" '*'
  ca_copy tmpmd    "${CA_SRC_TMPMD}"    "${V}/tmp-CC報告ファイル-md" '*.md' -m --include='*/' --include='*.md' --exclude='*'
  ca_copy_images "${V}"
  ca_copy dataDir-boards     "${dd}/boards"             "${V}/agent-console/boards" '*'
  ca_copy dataDir-audit      "${dd}/routine-audit.jsonl" "${V}/agent-console/routine-audit.jsonl" '*'
  ca_copy dataDir-diffcomments "${dd}/diff-comments.json" "${V}/agent-console/diff-comments.json" '*'
  ca_copy dataDir-uploads    "${dd}/uploads"            "${V}/agent-console/uploads" '*'
}

# ── 7 片付け（§4-11）────────────────────────────────────────────────────────
CA_PROTECT_FILE=""        # 守るセッション ID の一覧（1行1ID）
CA_PROTECT_OK=0

ca_uuid_re() { printf '%s' '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'; }

# ca_ids_from_json <open|sessions> <file>: ID を標準出力へ。形が違えば rc 1。
ca_ids_from_json() {
  python3 -I -c '
import json, re, sys
kind, path = sys.argv[1], sys.argv[2]
uuid = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
try:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
except Exception:
    sys.exit(1)
if not isinstance(d, dict):
    sys.exit(1)
if kind == "open":
    if d.get("version") != 1 or not isinstance(d.get("items"), list):
        sys.exit(1)
    for it in d["items"]:
        if isinstance(it, dict):
            v = it.get("claudeSessionId")
            if isinstance(v, str) and uuid.match(v):
                print(v.lower())
else:
    v = d.get("sessionId")
    if not (isinstance(v, str) and uuid.match(v)):
        sys.exit(1)
    print(v.lower())
' "$1" "$2"
}

# 守る集合 = open-sessions*.json の claudeSessionId ∪ sessions/*.json の sessionId（C4）。作れなければ rc 1。
ca_build_protect() {
  local f n=0
  CA_PROTECT_OK=0
  ca_tmpfile || return 1
  CA_PROTECT_FILE="${CA_TMPF}"
  : >"${CA_PROTECT_FILE}"
  if [ ! -f "${CA_DATADIR}/open-sessions.json" ]; then
    ca_log "守る集合: open-sessions.json が無い"; return 1
  fi
  for f in "${CA_DATADIR}/open-sessions.json" "${CA_DATADIR}/open-sessions.tmux-held.json"; do
    [ -e "${f}" ] || continue
    if ! ca_ids_from_json open "${f}" >>"${CA_PROTECT_FILE}"; then
      ca_log "守る集合: ${f##*/} が読めない・version≠1"; return 1
    fi
  done
  if [ ! -d "${CA_SESSIONS_DIR}" ]; then
    ca_log "守る集合: sessions ディレクトリが無い"; return 1
  fi
  for f in "${CA_SESSIONS_DIR}"/*.json; do
    [ -e "${f}" ] || continue
    n=$(( n + 1 ))
    if ! ca_ids_from_json sessions "${f}" >>"${CA_PROTECT_FILE}"; then
      ca_log "守る集合: sessions の ${n} 番目の json が読めない"; return 1
    fi
  done
  sort -u "${CA_PROTECT_FILE}" -o "${CA_PROTECT_FILE}"
  CA_PROTECT_OK=1
  ca_log "守る集合: $(wc -l <"${CA_PROTECT_FILE}" | tr -d ' ') 件（sessions の json ${n} 件）"
  return 0
}

ca_is_protected() { grep -qix -- "$1" "${CA_PROTECT_FILE}" 2>/dev/null; }

ca_guard_src_root() { # 元の根が空・/・HOME のときは何もしない
  case "$1" in ""|"/"|"${HOME:-/nonexistent}") return 1 ;; /*) return 0 ;; *) return 1 ;; esac
}

ca_old() { # ca_old <mtime>: CA_MOVE_DAYS より古ければ 0
  [ $(( CA_NOW - $1 )) -gt $(( CA_MOVE_DAYS * 86400 )) ]
}

# 1ファイルの照合: ca_match <元> <先>。大きさと更新時刻が一致したら 0
ca_match() {
  [ -f "$2" ] && [ ! -L "$2" ] || return 1
  [ "$(stat -f '%z %m' -- "$1" 2>/dev/null)" = "$(stat -f '%z %m' -- "$2" 2>/dev/null)" ]
}

CA_MOVELOG=""
CA_U_OLD=0; CA_U_DEL=0; CA_U_SKIP=0; CA_U_BYTES=0; CA_U_REASONS=""

ca_unit_begin() { CA_U_OLD=0; CA_U_DEL=0; CA_U_SKIP=0; CA_U_BYTES=0; CA_U_REASONS=""; }
ca_unit_end() { ca_log "片付け ${1}: 対象 ${CA_U_OLD} / ${CA_EXEC_VERB} ${CA_U_DEL} / 見送り ${CA_U_SKIP}${CA_U_REASONS:+（${CA_U_REASONS}）} / ${CA_EXEC_VERB}バイト ${CA_U_BYTES}"; }
ca_unit_skip() { CA_U_SKIP=$(( CA_U_SKIP + $1 )); CA_U_REASONS="${CA_U_REASONS}${CA_U_REASONS:+, }$2 $1"; }

ca_movelog_add() { # 入れ物の中の move-log に名前を足す（--execute のときだけ）
  [ "${CA_EXECUTE}" -eq 1 ] || return 0
  printf '%s\n' "$1" >>"${CA_MOVELOG}"
}

# 単位が「ファイル単位」の片付け（計画・文書・画像）。
#   ca_sweep_files <元の根> <先の根> <名前glob>
#   一致した物だけ消す。消す直前にもう一度 stat して、確かめた時の値から変わっていなければ消す。
ca_sweep_files() {
  local sroot="$1" droot="$2" glob="$3" f rel m sz sig dstf cur
  ca_guard_src_root "${sroot}" || return 0
  [ -d "${sroot}" ] || return 0
  while IFS= read -r -d '' f; do
    m="$(stat -f '%m' -- "${f}" 2>/dev/null)" || continue
    ca_old "${m}" || continue
    CA_U_OLD=$(( CA_U_OLD + 1 ))
    rel="${f#"${sroot}"/}"
    dstf="${droot}/${rel}"
    sig="$(stat -f '%z %m' -- "${f}" 2>/dev/null)"
    sz="${sig% *}"
    if ! ca_match "${f}" "${dstf}"; then ca_unit_skip 1 "入れ物の写しと不一致"; continue; fi
    cur="$(stat -f '%z %m' -- "${f}" 2>/dev/null)"
    if [ "${cur}" != "${sig}" ] || [ -L "${f}" ]; then ca_unit_skip 1 "直前の再確認で変化"; continue; fi
    ca_movelog_add "${dstf}"
    if [ "${CA_EXECUTE}" -eq 1 ]; then
      if ! rm -f -- "${f}" 2>/dev/null || [ -e "${f}" ]; then ca_unit_skip 1 "削除に失敗"; CA_FAIL_CLEAN=1; continue; fi
    fi
    CA_U_DEL=$(( CA_U_DEL + 1 )); CA_U_BYTES=$(( CA_U_BYTES + sz ))
  done < <(find -P "${sroot}" -type f -name "${glob}" -print0 2>/dev/null)
}

# セッション単位の manifest（パス 大きさ 更新時刻）を作る。ca_manifest <slug dir> <uuid>
ca_manifest() {
  local sdir="$1" id="$2"
  [ -f "${sdir}/${id}.jsonl" ] && [ ! -L "${sdir}/${id}.jsonl" ] && \
    printf '%s %s\n' "${sdir}/${id}.jsonl" "$(stat -f '%z %m' -- "${sdir}/${id}.jsonl")"
  if [ -d "${sdir}/${id}" ] && [ ! -L "${sdir}/${id}" ]; then
    find -P "${sdir}/${id}" -type f -print0 2>/dev/null | sort -z | while IFS= read -r -d '' f; do
      printf '%s %s\n' "${f}" "$(stat -f '%z %m' -- "${f}")"
    done
  fi
  return 0
}

ca_sweep_sessions() {
  local V="$1" sdir slug id man man2 line path size mt maxm ok reason sess_dst bytes n f
  local uuid_re; uuid_re="$(ca_uuid_re)"
  local n_all=0 n_old=0 n_prot=0 n_mis=0 n_chg=0 n_del=0
  ca_guard_src_root "${CA_SRC_PROJECTS}" || return 0
  [ -d "${CA_SRC_PROJECTS}" ] || { ca_log "片付け セッション: 元が無い"; return 0; }
  if [ "${CA_PROTECT_OK}" -ne 1 ]; then
    ca_log "片付け セッション: セッション単位の片付けを全部見送り（守る集合を作れない）"
    return 0
  fi
  while IFS= read -r -d '' sdir; do
    slug="${sdir##*/}"
    # この slug の UUID 一覧（<uuid>.jsonl と <uuid>/）。memory/ や UUID でない物は対象外
    while IFS= read -r id; do
      [ -n "${id}" ] || continue
      n_all=$(( n_all + 1 ))
      man="$(ca_manifest "${sdir}" "${id}")"
      [ -n "${man}" ] || continue
      maxm=0
      while IFS= read -r line; do mt="${line##* }"; [ "${mt}" -gt "${maxm}" ] && maxm="${mt}"; done <<<"${man}"
      ca_old "${maxm}" || continue
      n_old=$(( n_old + 1 ))
      if ca_is_protected "${id}"; then n_prot=$(( n_prot + 1 )); continue; fi
      ok=1; reason=""
      sess_dst="${V}/claude/projects/${slug}"
      while IFS= read -r line; do
        mt="${line##* }"; line="${line% *}"; size="${line##* }"; path="${line% *}"
        if ! ca_match "${path}" "${sess_dst}/${path#"${sdir}"/}"; then ok=0; reason="${path#"${sdir}"/}"; break; fi
      done <<<"${man}"
      if [ "${ok}" -eq 0 ]; then
        n_mis=$(( n_mis + 1 )); ca_log "片付け セッション ${slug}/${id}: 写しと不一致のため丸ごと残す（${reason}）"; continue
      fi
      man2="$(ca_manifest "${sdir}" "${id}")"
      if [ "${man}" != "${man2}" ]; then
        n_chg=$(( n_chg + 1 )); ca_log "片付け セッション ${slug}/${id}: 直前の再確認で変化があり残す"; continue
      fi
      bytes=0
      while IFS= read -r line; do
        line="${line% *}"; size="${line##* }"; bytes=$(( bytes + size ))
        path="${line% *}"
        ca_movelog_add "${sess_dst}/${path#"${sdir}"/}"
      done <<<"${man}"
      if [ "${CA_EXECUTE}" -eq 1 ]; then
        while IFS= read -r line; do
          line="${line% *}"; path="${line% *}"
          rm -f -- "${path}" 2>/dev/null || CA_FAIL_CLEAN=1
        done <<<"${man}"
        if [ -d "${sdir}/${id}" ] && [ ! -L "${sdir}/${id}" ]; then
          find -P "${sdir}/${id}" -depth -type d -print0 2>/dev/null | while IFS= read -r -d '' f; do rmdir "${f}" 2>/dev/null || true; done
        fi
      fi
      n_del=$(( n_del + 1 )); CA_SES_BYTES=$(( CA_SES_BYTES + bytes ))
    done < <({ find -P "${sdir}" -mindepth 1 -maxdepth 1 -type f -name '*.jsonl' -print 2>/dev/null | sed -e 's#^.*/##' -e 's#\.jsonl$##'
               find -P "${sdir}" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sed -e 's#^.*/##'; } \
             | grep -E "${uuid_re}" | sort -u)
  done < <(find -P "${CA_SRC_PROJECTS}" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
  ca_log "片付け セッション: 全 ${n_all} / 古い ${n_old} / 開いているため残す ${n_prot} / 写し不一致 ${n_mis} / 再確認で変化 ${n_chg} / ${CA_EXEC_VERB} ${n_del} / ${CA_EXEC_VERB}バイト ${CA_SES_BYTES}"
}

ca_sweep_images() { # 画像: 守るセッションの <slug>/<uuid>/images/ は消さない
  local V="$1" root="${CA_SRC_CLAUDE_TMP}" p rel uuid
  ca_guard_src_root "${root}" || return 0
  [ -d "${root}" ] || return 0
  while IFS= read -r -d '' p; do
    rel="${p#"${root}"/}"            # <slug>/<uuid>/images
    uuid="$(printf '%s' "${rel}" | awk -F/ '{print $2}')"
    if [ "${CA_PROTECT_OK}" -eq 1 ] && ca_is_protected "${uuid}"; then continue; fi
    ca_sweep_files "${p}" "${V}/claude-tmp-images/${rel}" '*'
  done < <(find -P "${root}" -mindepth 3 -maxdepth 3 -type d -name images -print0 2>/dev/null)
}

ca_cleanup() { # ca_cleanup <入れ物の中身の場所>
  local V="$1"
  CA_EXEC_VERB="消す予定"; [ "${CA_EXECUTE}" -eq 1 ] && CA_EXEC_VERB="消した"
  CA_SES_BYTES=0
  if [ "${CA_EXECUTE}" -eq 1 ]; then
    mkdir -p "${V}/move-log" || { ca_log "[失敗] move-log を作れない。片付けを見送り"; CA_FAIL_CLEAN=1; return 0; }
    CA_MOVELOG="${V}/move-log/$(date -r "${CA_NOW}" +%Y%m%d).txt"
  fi
  ca_log "片付け開始 mode=$([ "${CA_EXECUTE}" -eq 1 ] && echo execute || echo dry-run) 古さ=${CA_MOVE_DAYS}日"
  ca_build_protect || true
  ca_sweep_sessions "${V}"
  ca_unit_begin; ca_sweep_files "${CA_SRC_PLANS}" "${V}/claude/plans" '*';             ca_unit_end 計画
  ca_unit_begin; ca_sweep_files "${CA_SRC_TMPMD}" "${V}/tmp-CC報告ファイル-md" '*.md'; ca_unit_end 文書
  ca_unit_begin; ca_sweep_images "${V}";                                               ca_unit_end 画像
}

# ── 9 通知 ───────────────────────────────────────────────────────────────────
ca_notify_if_stale() {
  local last=""
  [ -f "${CA_LAST_OK}" ] && last="$(tr -dc '0-9' <"${CA_LAST_OK}" 2>/dev/null)"
  if [ -z "${last}" ] || [ $(( CA_NOW - last )) -gt "${CA_NOTIFY_SEC}" ]; then
    ca_log "通知: last-ok が無いか 3日より古い"
    "${CA_OSASCRIPT_CMD}" -e 'display notification "HDD への写しが3日以上できていません。HDD をつないでください" with title "Claude アーカイブ"' >/dev/null 2>&1 || true
  fi
}

# ── main ─────────────────────────────────────────────────────────────────────
ca_main() {
  CA_EXECUTE=0
  case "${1:-}" in
    "") ;;
    --execute) CA_EXECUTE=1 ;;
    *) echo "使い方: bash scripts/claude-archive.sh [--execute]" >&2; return 2 ;;
  esac
  ca_config
  ca_setup_log
  ca_log "===== claude-archive 開始 mode=$([ "${CA_EXECUTE}" -eq 1 ] && echo execute || echo dry-run) ====="

  # 1 ロック
  if ! mkdir "${CA_LOCK_DIR}" 2>/dev/null; then
    ca_log "another instance is running; skip."
    return 0
  fi
  CA_LOCKED=1
  trap ca_trap EXIT INT TERM

  local hdd_present=0 opened=0 V="" rc=0
  # 2 HDD の確認
  if [ -d "${CA_HDD_MOUNT}" ] && [ -e "${CA_IMAGE}" ]; then
    hdd_present=1
  else
    ca_log "HDD なし（名前が変わった可能性も含む）: ${CA_HDD_MOUNT}"
  fi

  if [ "${hdd_present}" -eq 1 ]; then
    # 3 開く
    if ca_open; then
      opened=1; V="${CA_MP}"
    else
      CA_FAIL_OPEN=1
    fi
  fi

  if [ "${opened}" -eq 1 ]; then
    # 4・5 写す／確かめる
    ca_copy_all "${V}"
    # 6 last-ok
    if [ "${CA_FAIL_COPY}" -eq 0 ]; then
      mkdir -p "$(dirname "${CA_LAST_OK}")" 2>/dev/null || true
      printf '%s\n' "${CA_NOW}" >"${CA_LAST_OK}" || ca_log "[失敗] last-ok を書けない"
      ca_log "全項目成功。last-ok を更新"
      # 7 片付け
      ca_cleanup "${V}"
    else
      ca_log "片付け見送り（写しに失敗した項目がある）。last-ok は更新しない"
    fi
    # 8 閉じる
    if [ "${CA_OPENED_BY_ME}" -eq 1 ]; then
      local i=0
      while [ "${i}" -lt 3 ]; do
        i=$(( i + 1 ))
        if ca_detach_once; then CA_OPENED_BY_ME=0; break; fi
        [ "${i}" -lt 3 ] && sleep "${CA_DETACH_RETRY_SEC}"
      done
      CA_DETACH_DONE=1
      if [ "${CA_OPENED_BY_ME}" -eq 1 ]; then
        ca_log "detach 失敗（3回試した）: ${CA_MP}"
        CA_FAIL_DETACH=1
      else
        rmdir "${CA_MP}" 2>/dev/null || true
        ca_log "入れ物を閉じた"
      fi
    fi
  fi

  # 9 通知
  ca_notify_if_stale

  # 10 終了とログ
  if [ "${CA_FAIL_OPEN}" -ne 0 ] || [ "${CA_FAIL_COPY}" -ne 0 ] || [ "${CA_FAIL_CLEAN}" -ne 0 ] || [ "${CA_FAIL_DETACH}" -ne 0 ]; then rc=1; fi
  ca_log "===== claude-archive 終了 rc=${rc}（open失敗=${CA_FAIL_OPEN} 写し失敗=${CA_FAIL_COPY} 片付け失敗=${CA_FAIL_CLEAN} detach失敗=${CA_FAIL_DETACH}）====="
  return "${rc}"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  ca_main "$@"
  exit $?
fi
