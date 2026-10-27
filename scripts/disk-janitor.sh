#!/bin/bash
# disk-janitor.sh — 開発データの毎日の自動片付け（docs/handoff/disk-janitor/design.md）
#
# 消すのは「作り直せる物」と「GitHub に同じ内容がある物」だけ。既定は dry-run（一覧と容量のみ）。
#   R1 散らばった .npm-cache            （根の下・深さ4まで）
#   R2 使っていない作業用コピーの node_modules（package-lock.json あり・14日更新なし・最終コミット14日より前・使用中でない）
#   R3 agent-console の旧版              （current・その1つ前・current より新しい版・使用中の版は残す）
#   R4 他リポジトリの作業用コピー        （reaper-worktree.sh を REAPER_BASE_BRANCH 付きで呼ぶ。安全条件は reaper のまま）
#   R5 /tmp/CC報告ファイルの .md 以外    （7日更新なし。HDD への写しが2日以内に成功しているときだけ。docs/handoff/claude-archive/design.md §5）
#   R6 セッションの作業メモ              （claude-501 の <slug>/<uuid>/scratchpad の中と tasks/b*.output。同じ前提。images/ は触らない）
#
# 使い方:
#   bash scripts/disk-janitor.sh            # dry-run
#   bash scripts/disk-janitor.sh --execute  # 実削除（LaunchAgent はこちら）
#
# 設定（すべて DJ_ で始まる環境変数で上書きできる。試験用）は dj_config に1か所でまとめてある。
# 消す直前のガード（絶対パス・根の下・シンボリックリンクでない・名前一致）は dj_guard 1つで、全規則が必ず通る。
# このファイルは source できる（試験が dj_guard を直接呼ぶ）。source 時は何も実行しない。

set -u

# ── 作業場所に向ける git の守り（ADR-1039）。読めなければ何も消さずに終わる ──────
# shellcheck source=scripts/git-safe.sh
if ! source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/git-safe.sh" 2>/dev/null || [ -z "${GIT_SAFE_ARGS+x}" ]; then
  echo "[disk-janitor] git の守りを読めない（scripts/git-safe.sh）。何も消さずに終了します。" >&2
  # shellcheck disable=SC2317  # source されたときは return、直接実行なら exit
  return 1 2>/dev/null || exit 1
fi

# ── 設定（1か所）─────────────────────────────────────────────────────────────
dj_config() {
  local home_dir="${HOME:-/Users/tanizawashingo}"
  : "${DJ_ROOT_WORKTREES:=${home_dir}/worktrees}"
  : "${DJ_ROOT_AC_WT:=${home_dir}/agent-console-wt}"
  : "${DJ_ROOT_SALESANCHOR:=${home_dir}/salesanchor}"
  : "${DJ_ROOT_AGENT_CONSOLE:=${home_dir}/agent-console}"
  : "${DJ_ROOT_VERSIONS:=${home_dir}/Library/Application Support/agent-console/versions}"
  : "${DJ_CURRENT_LINK:=${DJ_ROOT_VERSIONS}/../current}"
  : "${DJ_NPM_CACHE_KEEP:=${home_dir}/.npm-shared-cache}"
  : "${DJ_STALE_DAYS:=14}"
  # R5・R6 専用の根（DJ_ROOTS には入れない＝R1 の走査を広げない）
  : "${DJ_ROOT_TMP_CC:=/private/tmp/CC報告ファイル}"
  : "${DJ_ROOT_CLAUDE_TMP:=/private/tmp/claude-501}"
  : "${DJ_CA_LAST_OK:=${home_dir}/Library/Logs/claude-archive.last-ok}"
  : "${DJ_CA_FRESH_SEC:=172800}"       # 2日。last-ok がこれより古い／無いと R5・R6 を見送る
  : "${DJ_TMP_STALE_DAYS:=7}"          # R5・R6 の古さ（PO 決定: 7日動いていない物は終わった物）
  : "${DJ_LOG_FILE:=}"                 # 空なら標準出力のまま。LaunchAgent の plist が指定する
  : "${DJ_LOG_MAX_BYTES:=1048576}"
  : "${DJ_LOCK_DIR:=/tmp/disk-janitor.lock.d}"
  : "${DJ_DF_PATH:=/System/Volumes/Data}"
  : "${DJ_LSOF:=lsof}"
  : "${DJ_NPM_CMD:=npm config get cache}"
  : "${DJ_REAPER:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/reaper-worktree.sh}"
  # 対象リポジトリ「パス|owner/repo|行き先」を1行ずつ（F8 の確定値）
  : "${DJ_REPOS:=${home_dir}/agent-console|GEN-RYU-System/agent-console|main
${home_dir}/ebay-gas-automation|GEN-RYU-System/bay-auto|develop
${home_dir}/crm-app-current|GEN-RYU-System/crm-app|develop
${home_dir}/crm-app-canonical-20260830|GEN-RYU-System/crm-app|develop}"
  # 1回の出力で候補を並べる上限。既定: 実削除は20件、dry-run は全件
  if [ -z "${DJ_LIST_MAX:-}" ]; then
    if [ "${EXECUTE}" -eq 1 ]; then DJ_LIST_MAX=20; else DJ_LIST_MAX=1000000; fi
  fi
}

# ── 共通部品 ─────────────────────────────────────────────────────────────────
DJ_ROOTS=()           # 正規化済み（物理パス）の根
DJ_LSOF_FILE=""       # lsof -nP -F pn の出力（実行開始時に1回だけ取る）
DJ_LSOF_OK=0
DJ_GUARD_REASON=""
DJ_RULE_COUNT=0       # 規則ごとの集計（dj_rule_begin でリセット）
DJ_RULE_KB=0
DJ_RULE_SKIP=0
DJ_RULE_LISTED=0

dj_canon() { # 存在するディレクトリの物理パスを返す。無ければ失敗
  [ -d "$1" ] || return 1
  (cd -P "$1" 2>/dev/null && pwd -P)
}

dj_human() { # KB -> 人が読む容量
  awk -v k="${1:-0}" 'BEGIN{ if (k>=1048576) printf "%.1fGB", k/1048576; else if (k>=1024) printf "%.1fMB", k/1024; else printf "%dKB", k }'
}

dj_under() { # dj_under <path> <root>: path が root の「下」（root 自身は含まない）か
  case "$1" in "$2"/?*) return 0 ;; *) return 1 ;; esac
}

# 削除の直前ガード。通れば 0。通らなければ 1 と DJ_GUARD_REASON。
#   dj_guard <path> <名前の正規表現(ERE)> <許可する根>...
dj_guard() {
  local p="${1:-}" namepat="${2:-}" r
  shift 2 2>/dev/null || { DJ_GUARD_REASON="引数不足"; return 1; }
  DJ_GUARD_REASON=""
  case "${p}" in
    "") DJ_GUARD_REASON="空のパス"; return 1 ;;
    /*) ;;
    *) DJ_GUARD_REASON="絶対パスでない"; return 1 ;;
  esac
  case "/${p}/" in */../*|*/./*) DJ_GUARD_REASON="パスに . または .. を含む"; return 1 ;; esac
  case "${p}" in */) DJ_GUARD_REASON="末尾が /"; return 1 ;; esac
  if [ "${p}" = "/" ] || [ "${p}" = "${HOME:-/nonexistent}" ]; then
    DJ_GUARD_REASON="ルートまたはホームそのもの"; return 1
  fi
  local ok=0
  for r in "$@"; do
    [ -n "${r}" ] || continue
    [ "${p}" = "${r}" ] && { DJ_GUARD_REASON="根そのもの"; return 1; }
    dj_under "${p}" "${r}" && ok=1
  done
  [ "${ok}" -eq 1 ] || { DJ_GUARD_REASON="根の下でない"; return 1; }
  [ -L "${p}" ] && { DJ_GUARD_REASON="シンボリックリンク"; return 1; }
  [ -d "${p}" ] || { DJ_GUARD_REASON="ディレクトリでない・存在しない"; return 1; }
  local phys
  phys="$(dj_canon "${p}")" || { DJ_GUARD_REASON="実体パスを求められない"; return 1; }
  [ "${phys}" = "${p}" ] || { DJ_GUARD_REASON="途中にシンボリックリンクがある"; return 1; }
  if ! printf '%s\n' "${p##*/}" | grep -Eq "${namepat}"; then
    DJ_GUARD_REASON="名前が規則と一致しない"; return 1
  fi
  return 0
}

dj_in_use() { # dj_in_use <path>: lsof の出力に、その配下（または自身）を開いているものが1件でもあれば 0
  [ -s "${DJ_LSOF_FILE}" ] || return 1
  P="$1" awk 'BEGIN{p="n" ENVIRON["P"]} $0==p || index($0, p "/")==1 {f=1; exit} END{exit !f}' "${DJ_LSOF_FILE}"
}

dj_take_lsof() { # 失敗したら 1
  DJ_LSOF_FILE="$(mktemp "${TMPDIR:-/tmp}/disk-janitor-lsof.XXXXXX")" || return 1
  if ${DJ_LSOF} -nP -F pn >"${DJ_LSOF_FILE}" 2>/dev/null && [ -s "${DJ_LSOF_FILE}" ]; then
    DJ_LSOF_OK=1
  else
    DJ_LSOF_OK=0
  fi
  [ "${DJ_LSOF_OK}" -eq 1 ]
}

dj_rule_begin() { DJ_RULE_COUNT=0; DJ_RULE_KB=0; DJ_RULE_SKIP=0; DJ_RULE_LISTED=0; echo ""; echo "== $1 =="; }

dj_skip() { # dj_skip <path> <理由>
  DJ_RULE_SKIP=$(( DJ_RULE_SKIP + 1 ))
  echo "  [飛ばす] $1 （$2）"
}

dj_rule_end() {
  local verb="削除候補"; [ "${EXECUTE}" -eq 1 ] && verb="削除"
  if [ "${DJ_RULE_COUNT}" -gt "${DJ_RULE_LISTED}" ]; then
    echo "  …他 $(( DJ_RULE_COUNT - DJ_RULE_LISTED )) 件は一覧省略（件数・容量には含む）"
  fi
  echo "[$1] ${verb}: ${DJ_RULE_COUNT} 件 / $(dj_human "${DJ_RULE_KB}")（${DJ_RULE_KB}KB）、飛ばした: ${DJ_RULE_SKIP} 件"
  TOTAL_COUNT=$(( TOTAL_COUNT + DJ_RULE_COUNT ))
  TOTAL_KB=$(( TOTAL_KB + DJ_RULE_KB ))
}

# 1件の処理。ガード → dry-run なら記録だけ／execute なら容量を測って消し、無くなったことを確かめる。
#   dj_act <規則> <path> <名前ERE> <根>...
dj_act() {
  local rule="$1" p="$2" namepat="$3"
  shift 3
  if ! dj_guard "${p}" "${namepat}" "$@"; then
    dj_skip "${p}" "ガード: ${DJ_GUARD_REASON}"
    return 0
  fi
  local kb
  kb="$(du -sk "${p}" 2>/dev/null | awk '{print $1}')"
  kb="${kb:-0}"
  if [ "${EXECUTE}" -eq 1 ]; then
    if ! rm -rf -- "${p}" 2>/dev/null || [ -e "${p}" ]; then
      dj_skip "${p}" "削除に失敗または一部が残った"
      return 0
    fi
  fi
  DJ_RULE_COUNT=$(( DJ_RULE_COUNT + 1 ))
  DJ_RULE_KB=$(( DJ_RULE_KB + kb ))
  if [ "${DJ_RULE_LISTED}" -lt "${DJ_LIST_MAX}" ]; then
    DJ_RULE_LISTED=$(( DJ_RULE_LISTED + 1 ))
    echo "  [${rule}] ${p} ($(dj_human "${kb}"))"
  fi
}

# ── R5・R6 用: ファイル専用のガードと処理（dj_guard・dj_act は変えない）─────────────
# 削除の直前ガード（ファイル版）。通れば 0。通らなければ 1 と DJ_GUARD_REASON。
#   dj_guard_file <種類 f|dangling> <path> <名前の正規表現(ERE)> <許可する根>...
#   f        … 通常ファイルで、シンボリックリンクでない
#   dangling … 指し先が無くなったシンボリックリンク（リンク自身だけを対象にする。指し先はたどらない）
#   どちらも: 絶対パス・. や .. なし・根の下・親ディレクトリが物理パスと一致・名前一致・mtime が DJ_TMP_STALE_DAYS より古い
dj_guard_file() {
  local kind="${1:-}" p="${2:-}" namepat="${3:-}" r
  shift 3 2>/dev/null || { DJ_GUARD_REASON="引数不足"; return 1; }
  DJ_GUARD_REASON=""
  case "${p}" in
    "") DJ_GUARD_REASON="空のパス"; return 1 ;;
    /*) ;;
    *) DJ_GUARD_REASON="絶対パスでない"; return 1 ;;
  esac
  case "/${p}/" in */../*|*/./*) DJ_GUARD_REASON="パスに . または .. を含む"; return 1 ;; esac
  case "${p}" in */) DJ_GUARD_REASON="末尾が /"; return 1 ;; esac
  local ok=0
  for r in "$@"; do
    [ -n "${r}" ] || continue
    [ "${p}" = "${r}" ] && { DJ_GUARD_REASON="根そのもの"; return 1; }
    dj_under "${p}" "${r}" && ok=1
  done
  [ "${ok}" -eq 1 ] || { DJ_GUARD_REASON="根の下でない"; return 1; }
  case "${kind}" in
    f)
      [ -L "${p}" ] && { DJ_GUARD_REASON="シンボリックリンク"; return 1; }
      [ -f "${p}" ] || { DJ_GUARD_REASON="通常ファイルでない・存在しない"; return 1; }
      ;;
    dangling)
      [ -L "${p}" ] || { DJ_GUARD_REASON="シンボリックリンクでない"; return 1; }
      [ ! -e "${p}" ] || { DJ_GUARD_REASON="指し先がある"; return 1; }
      ;;
    *) DJ_GUARD_REASON="種類が不明"; return 1 ;;
  esac
  local parent phys
  parent="${p%/*}"
  phys="$(dj_canon "${parent}")" || { DJ_GUARD_REASON="親ディレクトリの実体パスを求められない"; return 1; }
  [ "${phys}" = "${parent}" ] || { DJ_GUARD_REASON="途中にシンボリックリンクがある"; return 1; }
  if ! printf '%s\n' "${p##*/}" | grep -Eq "${namepat}"; then
    DJ_GUARD_REASON="名前が規則と一致しない"; return 1
  fi
  if [ -z "$(find -P "${p}" -maxdepth 0 -mtime "+${DJ_TMP_STALE_DAYS}" -print 2>/dev/null)" ]; then
    DJ_GUARD_REASON="${DJ_TMP_STALE_DAYS}日以内に更新されている"; return 1
  fi
  return 0
}

# 1件の処理（ファイル版）。ガード → dry-run なら記録だけ／execute なら rm -f -- で消し、無くなったことを確かめる。
#   dj_act_file <規則> <種類 f|dangling> <path> <名前ERE> <根>...
dj_act_file() {
  local rule="$1" kind="$2" p="$3" namepat="$4"
  shift 4
  if ! dj_guard_file "${kind}" "${p}" "${namepat}" "$@"; then
    dj_skip "${p}" "ガード: ${DJ_GUARD_REASON}"
    return 0
  fi
  local bytes=0
  if [ "${kind}" = "f" ]; then bytes="$(stat -f %z "${p}" 2>/dev/null || echo 0)"; fi
  if [ "${EXECUTE}" -eq 1 ]; then
    if ! rm -f -- "${p}" 2>/dev/null || [ -e "${p}" ] || [ -L "${p}" ]; then
      dj_skip "${p}" "削除に失敗"
      return 0
    fi
  fi
  DJ_RULE_COUNT=$(( DJ_RULE_COUNT + 1 ))
  DJ_RULE_KB=$(( DJ_RULE_KB + (bytes + 1023) / 1024 ))
  if [ "${DJ_RULE_LISTED}" -lt "${DJ_LIST_MAX}" ]; then
    DJ_RULE_LISTED=$(( DJ_RULE_LISTED + 1 ))
    echo "  [${rule}] ${p} ($(dj_human $(( (bytes + 1023) / 1024 ))))"
  fi
}

# ── R1 散らばった .npm-cache ─────────────────────────────────────────────────
dj_rule_r1() {
  dj_rule_begin "R1 散らばった .npm-cache"
  if [ "${DJ_LSOF_OK}" -ne 1 ]; then
    echo "  [規則ごと飛ばす] lsof が失敗したため使用中を判定できない"; dj_rule_end R1; return 0
  fi
  # D1 適用の確認: 場所（/ と HOME）を変えて2回測り、2つとも保護する cache と完全一致したときだけ進む。
  # 相対パス設定（cache=./.npm-cache）に戻ると、場所によって値が変わるので一致しない。
  local cache_root cache_home
  cache_root="$(cd / 2>/dev/null && ${DJ_NPM_CMD} 2>/dev/null | tail -n 1)"
  cache_home="$(cd "${HOME:-/}" 2>/dev/null && ${DJ_NPM_CMD} 2>/dev/null | tail -n 1)"
  if [ -z "${cache_root}" ] || [ -z "${cache_home}" ]; then
    echo "  [規則ごと飛ばす] npm config get cache が取得できない"; dj_rule_end R1; return 0
  fi
  if [ "${cache_root}" != "${DJ_NPM_CACHE_KEEP}" ] || [ "${cache_home}" != "${DJ_NPM_CACHE_KEEP}" ]; then
    echo "  [警告] npm の cache が保護先 (${DJ_NPM_CACHE_KEEP}) と一致しない（/ では '${cache_root}'、HOME では '${cache_home}'）。D1 未適用の可能性。R1 全体を飛ばす"
    dj_rule_end R1; return 0
  fi
  local cache_now="${cache_root}"
  local cand
  while IFS= read -r cand; do
    [ -n "${cand}" ] || continue
    if [ "${cand}" = "${DJ_NPM_CACHE_KEEP}" ] || [ "${cand}" = "${cache_now}" ]; then
      dj_skip "${cand}" "npm の設定先（保護）"; continue
    fi
    case "${DJ_NPM_CACHE_KEEP}" in "${cand}"/*) dj_skip "${cand}" "保護する cache を含む"; continue ;; esac
    if dj_in_use "${cand}"; then
      dj_skip "${cand}" "使用中（プロセスが開いている）"; continue
    fi
    dj_act R1 "${cand}" '^\.npm-cache$' ${DJ_ROOTS[@]+"${DJ_ROOTS[@]}"}
  done < <(for r in ${DJ_ROOTS[@]+"${DJ_ROOTS[@]}"}; do
             find -P "${r}" -maxdepth 4 -type d -name .npm-cache -prune -print 2>/dev/null
           done | sort -u)
  dj_rule_end R1
}

# ── R2 使っていない作業用コピーの node_modules ────────────────────────────────
dj_wt_unused() { # dj_wt_unused <wt>: 使っていないなら 0。理由は DJ_WT_REASON
  local wt="$1" recent last_ct now cutoff
  DJ_WT_REASON=""
  if dj_in_use "${wt}"; then DJ_WT_REASON="使用中（プロセスが開いている）"; return 1; fi
  recent="$(find -P "${wt}" \( -name node_modules -o -name .npm-cache -o -name dist -o -name .sa-cache \
      -o -name coverage -o -name storybook-static -o -name test-results -o -name playwright-report -o -name .git \) -prune \
      -o -type f -mtime "-${DJ_STALE_DAYS}" -print -quit 2>/dev/null)"
  if [ -n "${recent}" ]; then DJ_WT_REASON="${DJ_STALE_DAYS}日以内に更新されたファイルあり"; return 1; fi
  last_ct="$(git "${GIT_SAFE_ARGS[@]}" -C "${wt}" log -1 --format=%ct 2>/dev/null)"
  case "${last_ct}" in ''|*[!0-9]*) DJ_WT_REASON="最終コミット時刻を取得できない（残す）"; return 1 ;; esac
  now="$(date +%s)"
  cutoff=$(( now - DJ_STALE_DAYS * 86400 ))
  if [ "${last_ct}" -ge "${cutoff}" ]; then DJ_WT_REASON="最終コミットが${DJ_STALE_DAYS}日以内"; return 1; fi
  return 0
}

# 照らす元のリポジトリ（DJ_ROOT_SALESANCHOR と DJ_REPOS の各行のパス）のどれか1つと git の繋がりが合えば 0
dj_link_known() { # <作業場所>
  local wt="$1" main rpath _w _b
  DJ_LINK_REASON="照らす元のリポジトリが無い"
  while IFS= read -r main; do
    [ -n "${main}" ] || continue
    [ -d "${main}" ] || continue
    if git_safe_link_ok "${wt}" "${main}"; then return 0; fi
    DJ_LINK_REASON="${GIT_SAFE_LINK_REASON}"
  done < <({ printf '%s\n' "${DJ_ROOT_SALESANCHOR}"; while IFS='|' read -r rpath _w _b; do printf '%s\n' "${rpath}"; done <<<"${DJ_REPOS}"; })
  return 1
}

dj_rule_r2() {
  dj_rule_begin "R2 使っていない作業用コピーの node_modules"
  if [ "${DJ_LSOF_OK}" -ne 1 ]; then
    echo "  [規則ごと飛ばす] lsof が失敗したため使用中を判定できない"; dj_rule_end R2; return 0
  fi
  local r gitfile wt sub nm
  for r in "${DJ_ROOT_WORKTREES_N}" "${DJ_ROOT_AC_WT_N}"; do
    [ -n "${r}" ] || continue
    while IFS= read -r gitfile; do
      [ -n "${gitfile}" ] || continue
      wt="${gitfile%/.git}"
      # この作業用コピーの候補（直下と frontend/ 直下）。無ければ判定しない
      local cands=() c
      for sub in "" "/frontend"; do
        nm="${wt}${sub}/node_modules"
        [ -d "${nm}" ] || [ -L "${nm}" ] || continue
        if [ ! -f "${wt}${sub}/package-lock.json" ]; then
          dj_skip "${nm}" "package-lock.json が無い（作り直せない）"; continue
        fi
        cands+=("${nm}")
      done
      [ "${#cands[@]}" -gt 0 ] || continue
      # ADR-1039 便2b-2: git の繋がりが、照らす元のリポジトリのどれとも合わない作業場所は残す
      if ! dj_link_known "${wt}"; then
        for c in "${cands[@]}"; do dj_skip "${c}" "git の繋がりが知っている元のリポジトリと合わない（残す）: ${DJ_LINK_REASON}"; done
        continue
      fi
      if ! dj_wt_unused "${wt}"; then
        for c in "${cands[@]}"; do dj_skip "${c}" "${DJ_WT_REASON}"; done
        continue
      fi
      for c in "${cands[@]}"; do
        dj_act R2 "${c}" '^node_modules$' "${DJ_ROOT_WORKTREES_N}" "${DJ_ROOT_AC_WT_N}"
      done
    done < <(find -P "${r}" -maxdepth 3 -name .git -type f -print 2>/dev/null | sort -u)
  done
  dj_rule_end R2
}

# ── R3 agent-console の旧版 ──────────────────────────────────────────────────
dj_ver_key() { # v1.2.3 -> 数値キー（比較用）
  local v="${1#v}" a b c
  IFS=. read -r a b c <<<"${v}"
  echo $(( 10#${a} * 100000000 + 10#${b} * 10000 + 10#${c} ))
}

dj_rule_r3() {
  dj_rule_begin "R3 agent-console の旧版"
  if [ "${DJ_LSOF_OK}" -ne 1 ]; then
    echo "  [規則ごと飛ばす] lsof が失敗したため使用中を判定できない"; dj_rule_end R3; return 0
  fi
  local vroot="${DJ_ROOT_VERSIONS_N}"
  if [ -z "${vroot}" ]; then
    echo "  [規則ごと飛ばす] versions ディレクトリが無い"; dj_rule_end R3; return 0
  fi
  local target tag
  target="$(readlink "${DJ_CURRENT_LINK}" 2>/dev/null)"
  tag="${target##*/}"
  if ! printf '%s\n' "${tag}" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || [ ! -d "${vroot}/${tag}" ]; then
    echo "  [規則ごと飛ばす] current が読めない、または指し先が無い (current -> '${target}')"
    dj_rule_end R3; return 0
  fi
  local curkey prevkey=-1 prevtag="" d name key
  curkey="$(dj_ver_key "${tag}")"
  for d in "${vroot}"/v*; do
    [ -d "${d}" ] || continue
    name="${d##*/}"
    printf '%s\n' "${name}" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || continue
    key="$(dj_ver_key "${name}")"
    if [ "${key}" -lt "${curkey}" ] && [ "${key}" -gt "${prevkey}" ]; then prevkey="${key}"; prevtag="${name}"; fi
  done
  echo "  current=${tag}、1つ前=${prevtag:-なし}（これらと current より新しい版は残す）"
  for d in "${vroot}"/v*; do
    [ -e "${d}" ] || [ -L "${d}" ] || continue
    name="${d##*/}"
    printf '%s\n' "${name}" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || continue
    key="$(dj_ver_key "${name}")"
    if [ "${name}" = "${tag}" ]; then continue; fi
    if [ "${name}" = "${prevtag}" ]; then continue; fi
    if [ "${key}" -gt "${curkey}" ]; then dj_skip "${d}" "current より新しい版"; continue; fi
    if dj_in_use "${d}"; then dj_skip "${d}" "使用中（プロセスが開いている）"; continue; fi
    dj_act R3 "${d}" '^v[0-9]+\.[0-9]+\.[0-9]+$' "${vroot}"
  done
  dj_rule_end R3
}

# ── R4 他リポジトリの作業用コピー（reaper に任せる）──────────────────────────
dj_rule_r4() {
  dj_rule_begin "R4 他リポジトリの作業用コピー（reaper-worktree.sh）"
  if [ ! -f "${DJ_REAPER}" ]; then
    echo "  [規則ごと飛ばす] reaper が無い: ${DJ_REAPER}"; dj_rule_end R4; return 0
  fi
  local path want base url got out_file rc nlines
  while IFS='|' read -r path want base; do
    [ -n "${path}" ] || continue
    if [ ! -d "${path}" ]; then dj_skip "${path}" "リポジトリが無い"; continue; fi
    if ! git_safe_link_ok "${path}" "${path}"; then
      dj_skip "${path}" "git の繋がりを確かめられない（残す）: ${GIT_SAFE_LINK_REASON}"; continue
    fi
    url="$(git "${GIT_SAFE_ARGS[@]}" -C "${path}" remote get-url origin 2>/dev/null)"
    got="$(printf '%s\n' "${url}" | sed -E 's#\.git$##; s#^.*[:/]([^/:]+/[^/:]+)$#\1#')"
    if [ -z "${url}" ] || [ "${got}" != "${want}" ]; then
      dj_skip "${path}" "origin が想定と違う（想定 ${want}、実測 ${got:-取得できない}）"; continue
    fi
    local args=()
    [ "${EXECUTE}" -eq 1 ] && args=(--execute)
    out_file="$(mktemp "${TMPDIR:-/tmp}/disk-janitor-reaper.XXXXXX")" || { dj_skip "${path}" "一時ファイルを作れない"; continue; }
    ( cd "${path}" && REAPER_REPO_NAME="${want}" REAPER_BASE_BRANCH="${base}" \
        REAPER_ACTIVE_WORK_FILE=/dev/null ACTIVE_WORK_DIR=/nonexistent-disk-janitor \
        bash "${DJ_REAPER}" ${args[@]+"${args[@]}"} ) >"${out_file}" 2>&1
    rc=$?
    nlines="$(wc -l <"${out_file}" | tr -d ' ')"
    echo "  -- ${path} (${want}, 行き先 ${base}) reaper rc=${rc}, ${nlines} 行 --"
    head -n 40 "${out_file}" | sed 's/^/     /'
    [ "${nlines}" -gt 40 ] && echo "     …(残り $(( nlines - 40 )) 行は省略)"
    if grep -Eq '^✅ reaper 完了: 削除 [0-9]+ 件' "${out_file}"; then
      DJ_RULE_COUNT=$(( DJ_RULE_COUNT + $(sed -n 's/^✅ reaper 完了: 削除 \([0-9]*\) 件.*/\1/p' "${out_file}" | tail -n 1) ))
    elif [ "${EXECUTE}" -eq 0 ]; then
      DJ_RULE_COUNT=$(( DJ_RULE_COUNT + $(grep -Ec '^   - ' <(sed -n '/🗑️  削除対象/,$p' "${out_file}") || true) ))
    fi
    rm -f -- "${out_file}"
  done <<<"${DJ_REPOS}"
  DJ_RULE_LISTED="${DJ_RULE_COUNT}"   # R4 の一覧は reaper の出力そのもの（上に表示済み）
  dj_rule_end R4
}

# ── R5・R6 の前提: HDD への写しが最近成功している ─────────────────────────────
dj_ca_fresh() { # last-ok があり、現在 − その値 ≤ DJ_CA_FRESH_SEC なら 0
  local last now
  [ -f "${DJ_CA_LAST_OK}" ] || return 1
  last="$(tr -dc '0-9' <"${DJ_CA_LAST_OK}" 2>/dev/null)"
  [ -n "${last}" ] || return 1
  now="$(date +%s)"
  [ $(( now - last )) -le "${DJ_CA_FRESH_SEC}" ]
}

# ── R5 /tmp/CC報告ファイルの .md 以外（7日更新なし）──────────────────────────────
dj_rule_r5() {
  dj_rule_begin "R5 /tmp/CC報告ファイルの .md 以外"
  if ! dj_ca_fresh; then
    echo "  [規則ごと飛ばす] R5/R6 見送り（HDD 写しが2日以上成功していない）"; dj_rule_end R5; return 0
  fi
  local root f
  root="$(dj_canon "${DJ_ROOT_TMP_CC}")" || { echo "  [規則ごと飛ばす] 根が無い: ${DJ_ROOT_TMP_CC}"; dj_rule_end R5; return 0; }
  while IFS= read -r -d '' f; do
    case "${f}" in *.md) dj_skip "${f}" ".md は残す"; continue ;; esac
    dj_act_file R5 f "${f}" '.' "${root}"
  done < <(find -P "${root}" -type f ! -name '*.md' -mtime "+${DJ_TMP_STALE_DAYS}" -print0 2>/dev/null)
  dj_rule_end R5
}

# ── R6 セッションの作業メモ（scratchpad の中・tasks/b*.output・宙に浮いた a*.output）────
dj_rule_r6() {
  dj_rule_begin "R6 セッションの作業メモ"
  if ! dj_ca_fresh; then
    echo "  [規則ごと飛ばす] R5/R6 見送り（HDD 写しが2日以上成功していない）"; dj_rule_end R6; return 0
  fi
  local root sp td f
  root="$(dj_canon "${DJ_ROOT_CLAUDE_TMP}")" || { echo "  [規則ごと飛ばす] 根が無い: ${DJ_ROOT_CLAUDE_TMP}"; dj_rule_end R6; return 0; }
  # <slug>/<uuid>/scratchpad の中の全ファイル（中の images/ も消す）。<slug>/<uuid>/images/ は根に含めないので触れない
  while IFS= read -r -d '' sp; do
    while IFS= read -r -d '' f; do
      dj_act_file R6 f "${f}" '.' "${sp}"
    done < <(find -P "${sp}" -type f -mtime "+${DJ_TMP_STALE_DAYS}" -print0 2>/dev/null)
  done < <(find -P "${root}" -mindepth 3 -maxdepth 3 -type d -name scratchpad -print0 2>/dev/null)
  # <slug>/<uuid>/tasks/b*.output（通常ファイル）と、指し先が無くなった a*.output（リンク自身だけ）
  while IFS= read -r -d '' td; do
    while IFS= read -r -d '' f; do
      dj_act_file R6 f "${f}" '^b[^/]*\.output$' "${td}"
    done < <(find -P "${td}" -mindepth 1 -maxdepth 1 -type f -name 'b*.output' -mtime "+${DJ_TMP_STALE_DAYS}" -print0 2>/dev/null)
    while IFS= read -r -d '' f; do
      [ -L "${f}" ] && [ ! -e "${f}" ] || continue
      dj_act_file R6 dangling "${f}" '^a[^/]*\.output$' "${td}"
    done < <(find -P "${td}" -mindepth 1 -maxdepth 1 -type l -name 'a*.output' -mtime "+${DJ_TMP_STALE_DAYS}" -print0 2>/dev/null)
  done < <(find -P "${root}" -mindepth 3 -maxdepth 3 -type d -name tasks -print0 2>/dev/null)
  dj_rule_end R6
}

# ── ログ（1MB 超で .1 に1世代だけ退避）───────────────────────────────────────
dj_setup_log() {
  [ -n "${DJ_LOG_FILE}" ] || return 0
  mkdir -p "$(dirname "${DJ_LOG_FILE}")" 2>/dev/null || true
  if [ -f "${DJ_LOG_FILE}" ]; then
    local sz
    sz="$(wc -c <"${DJ_LOG_FILE}" | tr -d ' ')"
    if [ "${sz:-0}" -gt "${DJ_LOG_MAX_BYTES}" ]; then mv -f -- "${DJ_LOG_FILE}" "${DJ_LOG_FILE}.1"; fi
  fi
  exec >>"${DJ_LOG_FILE}" 2>&1
}

# ── main ─────────────────────────────────────────────────────────────────────
dj_main() {
  EXECUTE=0
  TOTAL_COUNT=0
  TOTAL_KB=0
  case "${1:-}" in
    "") ;;
    --execute) EXECUTE=1 ;;
    *) echo "使い方: bash scripts/disk-janitor.sh [--execute]" >&2; return 2 ;;
  esac
  dj_config
  dj_setup_log

  if ! mkdir "${DJ_LOCK_DIR}" 2>/dev/null; then
    echo "[disk-janitor] another instance is running; skip."
    return 0
  fi
  # shellcheck disable=SC2064
  trap "rmdir '${DJ_LOCK_DIR}' 2>/dev/null || true; rm -f -- \"\${DJ_LSOF_FILE:-}\" 2>/dev/null || true" EXIT INT TERM

  local mode="dry-run"; [ "${EXECUTE}" -eq 1 ] && mode="execute"
  echo "===== disk-janitor 開始 $(date '+%Y-%m-%d %H:%M:%S') mode=${mode} ====="
  echo "--- df（開始）---"; df -h "${DJ_DF_PATH}"

  # 根の正規化（無いものは外す）
  DJ_ROOT_WORKTREES_N="$(dj_canon "${DJ_ROOT_WORKTREES}")" || DJ_ROOT_WORKTREES_N=""
  DJ_ROOT_AC_WT_N="$(dj_canon "${DJ_ROOT_AC_WT}")" || DJ_ROOT_AC_WT_N=""
  DJ_ROOT_VERSIONS_N="$(dj_canon "${DJ_ROOT_VERSIONS}")" || DJ_ROOT_VERSIONS_N=""
  local sa_n ac_n
  sa_n="$(dj_canon "${DJ_ROOT_SALESANCHOR}")" || sa_n=""
  ac_n="$(dj_canon "${DJ_ROOT_AGENT_CONSOLE}")" || ac_n=""
  DJ_ROOTS=()
  local r
  for r in "${DJ_ROOT_WORKTREES_N}" "${DJ_ROOT_AC_WT_N}" "${sa_n}" "${ac_n}" "${DJ_ROOT_VERSIONS_N}"; do
    [ -n "${r}" ] && DJ_ROOTS+=("${r}")
  done
  echo "根: ${DJ_ROOTS[*]:-（なし）}"

  if dj_take_lsof; then
    echo "lsof: $(wc -l <"${DJ_LSOF_FILE}" | tr -d ' ') 行を取得"
  else
    echo "[警告] lsof が失敗した。R1〜R3 は飛ばす（R4 は reaper 自身の判定）"
  fi

  dj_rule_r1
  dj_rule_r2
  dj_rule_r3
  dj_rule_r4
  dj_rule_r5
  dj_rule_r6

  echo ""
  echo "--- df（終了）---"; df -h "${DJ_DF_PATH}"
  echo "===== disk-janitor 終了 $(date '+%Y-%m-%d %H:%M:%S') mode=${mode} 合計 ${TOTAL_COUNT} 件 / $(dj_human "${TOTAL_KB}")（R4 の容量は含まない） ====="
  return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  dj_main "$@"
fi
