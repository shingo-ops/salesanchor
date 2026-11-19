#!/bin/bash
# reaper-worktree.sh — マージ済み worktree の自動回収（ADR-114）
#
# 安全条件（非交渉・すべて満たした部屋だけ削除）:
#   ① 未コミットがゼロ、かつ HEAD までの全コミットが origin のどれかの ref から到達できる（GitHub から取り戻せる。R8）
#   ② active-work.md が DONE、または gh で PR がマージ済み（main）
#   ③ IN_PROGRESS / REVIEW かつ未マージなら削除しない
#   ④ 使用中（そのフォルダか配下を cwd にしているプロセスがある）なら削除しない
#   ⑤ R9: 未追跡の *pr-body*.md（PR 本文の下書き）だけが残る部屋は、main へのマージ済み PR の本文に
#      下書きの全行があるときだけ未保存扱いしない。実削除前に .git/reaper-drafts/ へ控える（失敗したら消さない）
#
# .worktree-id なし（旧 worktree）: git branch --show-current でブランチ名を取得して処理
#
# 既定: dry-run（削除予定の一覧表示のみ）
# 実削除: --execute フラグが必須
#
# テスト用オーバーライド環境変数:
#   REAPER_WORKTREES_DIR      — 指定するとそのディレクトリのみ走査（テスト互換モード）
#                               未指定（本番）: git worktree list --porcelain で全登録 worktree を対象にする
#   REAPER_ACTIVE_WORK_FILE   — active-work.md のパス（既定: <repo>/.claude-pipeline/active-work.md）
#   REAPER_REPO_NAME          — gh コマンドに使うリポジトリ名（既定: shingo-ops/salesanchor）
#   REAPER_BASE_BRANCH        — PR の行き先ブランチ（既定 main）。develop 運用の他リポジトリ用。
#                               ブランチ名が main・develop・この値と同じ worktree は候補にしない（本体ブランチ保護）
#   REAPER_LOCK_WAIT_SEC      — ロック取得できないときの待ち秒数（既定 0 = 待たずに skip）
#   REAPER_LOCK_DIR           — ロックの場所（テスト用。既定 /tmp/reaper-worktree.lock.d）
#   REAPER_SKIP_FETCH         — 1 で走査前の git fetch --prune を省略（テスト用）
#   REAPER_FETCH_REMOTE       — 走査前 fetch の remote 名（既定 origin。テスト用）
#   REAPER_IDLE_DAYS          — 置き忘れ（R13）とみなす、最後に触ってからの日数（既定 14）
#   REAPER_IDLE_MAX_PER_RUN   — 1 回の実行で片付ける置き忘れの部屋の上限（既定 30。new-worktree.sh からは 10）
#   REAPER_ARCHIVE_MAX_MB     — 1 部屋の写しの上限 MB（既定 200）。超える部屋は写さず残す
#   REAPER_ARCHIVE_STAMP      — 写しの置き場の名前の日時部分（テスト用。既定は実行時刻 YYYYMMDD-HHMMSS）
#
# ⑥ R13（置き忘れの部屋）: $HOME/worktrees/ の下で、PR が開いておらず、使用中でも鍵付きでもなく、
#    最後に触ってから REAPER_IDLE_DAYS 日以上の部屋は、記録していない変更等を <git-common-dir>/reaper-archive/ に
#    写し、照合が合ったときだけ部屋を消す（ブランチと台帳は変えない）。戻しは scripts/reaper-restore.sh。
#    置き忘れの処理は本番の走査（REAPER_WORKTREES_DIR 未指定）でだけ動く。
#
# 使用方法:
#   bash scripts/reaper-worktree.sh            # dry-run（削除予定の一覧のみ）
#   bash scripts/reaper-worktree.sh --execute  # 実削除

# ── 作業場所に向ける git の守り（ADR-1039）。読めなければ何も消さずに終わる ──────
# shellcheck source=scripts/git-safe.sh
if ! source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/git-safe.sh" 2>/dev/null || [ -z "${GIT_SAFE_ARGS+x}" ]; then
  echo "[reaper] git の守りを読めない（scripts/git-safe.sh）。何も消さずに終了します。" >&2
  exit 1
fi

# status が index を書き直して「最後に触った時刻」を毎晩新しくしないようにする（既存の status も含む）
export GIT_OPTIONAL_LOCKS=0

EXECUTE=0
if [ "${1:-}" = "--execute" ]; then
  EXECUTE=1
fi

# ── 多重起動ガード（全経路共通: cron / LaunchAgent / 手動 / GitHub Actions）──────
# mkdir はアトミック操作のため macOS/Linux 両対応の排他ロックとして機能する
# REAPER_LOCK_WAIT_SEC: 取得できないときに待つ秒数（既定 0 = 待たずに skip。
#   new-worktree.sh からの呼び出しは待たせない。GitHub Actions は 300 を指定する）
# REAPER_LOCK_DIR: テスト用にロックの場所を差し替える（既定は本番のロック）
_REAPER_LOCK="${REAPER_LOCK_DIR:-/tmp/reaper-worktree.lock.d}"
_LOCK_WAIT="${REAPER_LOCK_WAIT_SEC:-0}"
_WAITED=0
until mkdir "${_REAPER_LOCK}" 2>/dev/null; do
  if [ "${_WAITED}" -ge "${_LOCK_WAIT}" ]; then
    echo "[reaper] another instance is running; skip."
    exit 0
  fi
  sleep 10
  _WAITED=$(( _WAITED + 10 ))
done
[ "${_WAITED}" -gt 0 ] && echo "[reaper] waited ${_WAITED}s for lock"

# ── 終わりの処理（1 つの関数にまとめる。trap を重ねるとロックが残るため）──────────────
# ① _LINK_OK が 1 のときだけ「作業場所の数」を 1 行出す（繋がりが合わずに止まる道では本店へ git を流さない。R12）
# ② ロックを消す。INT・TERM は exit に変えるだけで、この関数は EXIT の 1 回だけ走る。
_LINK_OK=0
_reaper_on_exit() {
  if [ "${_LINK_OK:-0}" = "1" ]; then
    local _n
    _n=$(git -C "${MAIN_REPO_ROOT}" worktree list 2>/dev/null | tail -n +2 | grep -v '/cbs-copy\.' | wc -l | tr -d ' ')
    echo "作業場所の数: ${_n:-0}（上限 ${WORKTREE_LIMIT:-100} ・知らせる線 70）"
  fi
  rmdir "${_REAPER_LOCK}" 2>/dev/null || true
}
trap _reaper_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ── メインリポジトリルート取得 ──────────────────────────────────────────────
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || echo "")"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then
  MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"
else
  MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
fi

# ── git の繋がりの確かめ（ADR-1039 便2b-2・ADR-114 R12）────────────────────────
# 本店に向けた git（fetch・worktree list・remove・branch -D・prune）より前に、本店の繋がりを確かめる。
# 合わなければ何も消さずに終了コード 1。本番の走査は cwd が本店の最上位であることを求める。
_LINK_CHK=1
if [ -z "${REAPER_WORKTREES_DIR:-}" ]; then
  if ! git_safe_link_ok "${PWD}" "${PWD}"; then
    _LINK_CHK=0
  elif [ -z "${MAIN_REPO_ROOT}" ] || [ "$(command realpath "${MAIN_REPO_ROOT}" 2>/dev/null)" != "$(command realpath "${PWD}" 2>/dev/null)" ]; then
    GIT_SAFE_LINK_REASON="本店の最上位で動かしていない"
    _LINK_CHK=0
  fi
else
  git_safe_link_ok "${PWD}" "${MAIN_REPO_ROOT}" || _LINK_CHK=0
fi
if [ "${_LINK_CHK}" -ne 1 ]; then
  echo "[reaper] 元のリポジトリの git の繋がりを確かめられない（${GIT_SAFE_LINK_REASON:-不明}）。何も消さない。本店の最上位で動かしてください。" >&2
  exit 1
fi
_LINK_OK=1   # 判定は別の変数 _LINK_CHK で行い、合ったときだけここで 1 にする（終わりの処理が読む）

ACTIVE_WORK_FILE="${REAPER_ACTIVE_WORK_FILE:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.md}"
REPO_NAME="${REAPER_REPO_NAME:-shingo-ops/salesanchor}"
BASE_BRANCH="${REAPER_BASE_BRANCH:-main}"

# ── 事前: GitHub 側の最新状態を取り込む（R8）──────────────────────────────
# 「取り戻せるか」を origin の ref で判定するため、古い ref を残さない（--prune）。
# 失敗したら今回は1件も削除しない（安全側）。テストは REAPER_SKIP_FETCH=1 で省略する。
_FETCH_REMOTE="${REAPER_FETCH_REMOTE:-origin}"
FETCH_OK=1
if [ "${REAPER_SKIP_FETCH:-0}" != "1" ]; then
  if ! GIT_TERMINAL_PROMPT=0 git -C "${MAIN_REPO_ROOT}" fetch --prune --quiet "${_FETCH_REMOTE}" 2>/dev/null; then
    FETCH_OK=0
    echo "⚠️  git fetch に失敗しました（${_FETCH_REMOTE}）。今回は削除しません。"
  fi
fi

# ── 置き忘れ（R13）用の関数 ───────────────────────────────────────────────────
# ファイルの更新時刻（エポック秒）。GNU（stat -c）と macOS（stat -f）の両方に対応する。取れなければ非 0
_reaper_mtime() {
  local _t
  _t=$(stat -c %Y "$1" 2>/dev/null) || _t=$(stat -f %m "$1" 2>/dev/null) || return 1
  case "${_t}" in ''|*[!0-9]*) return 1 ;; esac
  printf '%s\n' "${_t}"
}

# 部屋の「最後に触った時刻」: HEAD のコミット時刻・gitdir の index と HEAD の更新時刻・
# status に出る今あるファイルの更新時刻のうち一番新しいもの。どれかの取得に失敗したら「今」（消さない側）。
_reaper_last_touch() {
  local _room="${1%/}" _now _max _t _gd _rec _xy _f
  _now=$(date +%s)
  _max=0
  _t=$(git "${GIT_SAFE_ARGS[@]}" -C "${_room}" log -1 --format=%ct HEAD 2>/dev/null) || { echo "${_now}"; return 0; }
  case "${_t}" in ''|*[!0-9]*) echo "${_now}"; return 0 ;; esac
  [ "${_t}" -gt "${_max}" ] && _max="${_t}"
  _gd=$(git "${GIT_SAFE_ARGS[@]}" -C "${_room}" rev-parse --absolute-git-dir 2>/dev/null) || { echo "${_now}"; return 0; }
  for _f in "${_gd}/index" "${_gd}/HEAD"; do
    [ -e "${_f}" ] || continue
    _t=$(_reaper_mtime "${_f}") || { echo "${_now}"; return 0; }
    [ "${_t}" -gt "${_max}" ] && _max="${_t}"
  done
  # status は -z（名前の特殊文字を避ける）。失敗したら「今」。消したファイル（どちらかの桁が D）は時刻が無いので外す
  local _tmp
  _tmp=$(mktemp "${TMPDIR:-/tmp}/reaper-touch.XXXXXX") || { echo "${_now}"; return 0; }
  if ! git "${GIT_SAFE_ARGS[@]}" -C "${_room}" status --porcelain -z --untracked-files=all --ignore-submodules=all --no-renames > "${_tmp}" 2>/dev/null; then
    rm -f "${_tmp}"; echo "${_now}"; return 0
  fi
  while IFS= read -r -d '' _rec; do
    _xy="${_rec:0:2}"
    case "${_xy}" in *D*) continue ;; esac
    _f="${_room}/${_rec:3}"
    [ -e "${_f}" ] || [ -L "${_f}" ] || continue
    _t=$(_reaper_mtime "${_f}") || { rm -f "${_tmp}"; echo "${_now}"; return 0; }
    [ "${_t}" -gt "${_max}" ] && _max="${_t}"
  done < "${_tmp}"
  rm -f "${_tmp}"
  [ "${_max}" -gt 0 ] || _max="${_now}"
  echo "${_max}"
}

# 使用中か（cwd 一覧にその部屋かその配下がある）。$2 は lsof の cwd 一覧
_reaper_in_use() {
  local _p="${1%/}"
  printf '%s\n' "$2" | awk -v p="${_p}" '$0==p || index($0, p"/")==1 {f=1} END {exit !f}'
}

# 鍵付きか（git worktree list --porcelain で locked 行が出た部屋の一覧 LOCKED_PATHS に入っているか）
_reaper_is_locked() {
  local _p="${1%/}" _l
  for _l in "${LOCKED_PATHS[@]}"; do
    [ "${_l%/}" = "${_p}" ] && return 0
  done
  return 1
}

# 置き忘れの候補を積む: "<最後に触った時刻>\t<部屋のパス>\t<ブランチ名 または (detached)>"
# I1（$HOME/worktrees/ の下）をここで確かめ、時刻は I3 の後・最初の status の前に呼ぶ側が渡す
_reaper_push_idle() {
  [ "${IDLE_ENABLED}" -eq 1 ] || return 0
  local _p="${1%/}" _b="$2" _ts="$3"
  case "${_p}/" in "${HOME%/}/worktrees/"*) ;; *) return 0 ;; esac
  IDLE_CANDIDATES+=("${_ts}"$'\t'"${_p}"$'\t'"${_b}")
}

# reclaim.log と標準出力の両方へ（日時つき）
_reaper_log() {
  echo "$1"
  [ -n "${ARCHIVE_ROOT:-}" ] || return 0
  mkdir -p "${ARCHIVE_ROOT}" 2>/dev/null || return 0
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "${ARCHIVE_ROOT}/reclaim.log" 2>/dev/null || true
}

# 作りかけの置き場だけを消す（reaper-archive の直下で名前が .inprogress- で始まるものだけ）
_reaper_drop_inprogress() {
  local _d="${1%/}"
  case "${_d##*/}" in .inprogress-*) ;; *) return 1 ;; esac
  [ "$(dirname "${_d}")" = "${ARCHIVE_ROOT}" ] || return 1
  [ -d "${_d}" ] && [ ! -L "${_d}" ] || return 0
  find "${_d}" -depth -delete 2>/dev/null
}

# 1 部屋ぶんの写しを作って照合する（§3-3）。0=写し完成（_ARCH_DEST に置き場）・1=残す（理由は標準出力）。
# 写しは作りかけの置き場（.inprogress-…）に作り、照合が全部合ってから完成の名前（数字で始まる）へ変える。
# 合わなければ作りかけをその場で消す。部屋の index と作業ファイルには触らない。
_reaper_archive_room() {
  local room="${1%/}" branch="$2" ts="$3"
  local name stamp tmp dest st sha ok=1 n sc uc ds du_ ti est_kb avail_kb f
  name="${room##*/}"
  stamp="${REAPER_ARCHIVE_STAMP:-$(date +%Y%m%d-%H%M%S)}"
  dest="${ARCHIVE_ROOT}/${stamp}-${name}"
  tmp="${ARCHIVE_ROOT}/.inprogress-${stamp}-${name}"
  _ARCH_DEST="${dest}"
  local _g=(git "${GIT_SAFE_ARGS[@]}" -C "${room}")

  mkdir -p "${ARCHIVE_ROOT}" 2>/dev/null || { echo "   ⏭  残す（写しの置き場を作れない）: ${room}"; return 1; }
  if [ -e "${dest}" ] || [ -L "${dest}" ] || [ -e "${tmp}" ] || [ -L "${tmp}" ]; then
    echo "   ⏭  残す（写しの置き場が既にある）: ${room}"; return 1
  fi
  st=$("${_g[@]}" status --porcelain --untracked-files=all --ignore-submodules=all --no-renames 2>/dev/null) \
    || { echo "   ⏭  残す（status を取れない）: ${room}"; return 1; }
  if printf '%s\n' "${st}" | grep -q '^.A '; then
    echo "   ⏭  残す（git add -N のファイルがある。戻したときに status が同じにならない）: ${room}"; return 1
  fi
  sha=$("${_g[@]}" rev-parse -q --verify HEAD 2>/dev/null) || { echo "   ⏭  残す（HEAD が無い）: ${room}"; return 1; }

  # 空き容量: 置き場のある場所に REAPER_ARCHIVE_MAX_MB の 2 倍以上
  avail_kb=$(df -Pk "${ARCHIVE_ROOT}" 2>/dev/null | awk 'NR==2{print $4}')
  case "${avail_kb}" in ''|*[!0-9]*) echo "   ⏭  残す（空き容量を測れない）: ${room}"; return 1 ;; esac
  if [ "${avail_kb}" -lt $(( ARCHIVE_MAX_MB * 1024 * 2 )) ]; then
    echo "   ⏭  残す（空き容量が足りない。上限 ${ARCHIVE_MAX_MB}MB の 2 倍が要る）: ${room}"; return 1
  fi

  mkdir "${tmp}" 2>/dev/null || { echo "   ⏭  残す（作りかけの置き場を作れない）: ${room}"; return 1; }

  # 写すファイルの一覧（untracked / ignored。node_modules 等の作り直せる置き場は ignored から外す）
  "${_g[@]}" ls-files --others --exclude-standard -z > "${tmp}/.untracked.lst" 2>/dev/null || ok=0
  "${_g[@]}" ls-files --others --ignored --exclude-standard -z > "${tmp}/.ignored.raw" 2>/dev/null || ok=0
  : > "${tmp}/.ignored.lst"
  while IFS= read -r -d '' f; do
    case "/${f}" in
      */node_modules/*|*/.venv/*|*/dist/*|*/build/*|*/__pycache__/*|*/.pytest_cache/*|*/.mypy_cache/*|*/coverage/*) continue ;;
    esac
    printf '%s\0' "${f}"
  done < "${tmp}/.ignored.raw" >> "${tmp}/.ignored.lst"
  if [ "${ok}" -eq 0 ]; then
    _reaper_drop_inprogress "${tmp}"; echo "   ⏭  残す（写すファイルの一覧を作れない）: ${room}"; return 1
  fi

  # 先に du で見込みの大きさを測る。上限を超えるなら写しを作らずに残す
  est_kb=0
  for f in .untracked.lst .ignored.lst; do
    [ -s "${tmp}/${f}" ] || continue
    n=$(cd "${room}" && xargs -0 du -ck -- < "${tmp}/${f}" 2>/dev/null | awk '$2=="total"{s+=$1} END{print s+0}')
    est_kb=$(( est_kb + ${n:-0} ))
  done
  if [ "${est_kb}" -gt $(( ARCHIVE_MAX_MB * 1024 )) ]; then
    _reaper_drop_inprogress "${tmp}"
    echo "   ⏭  残す（写しの見込み ${est_kb}KB が上限 ${ARCHIVE_MAX_MB}MB を超える）: ${room}"; return 1
  fi

  # 写し本体（1 つでも失敗したら ok=0）
  {
    printf 'branch=%s\n' "${branch}"
    printf 'sha=%s\n' "${sha}"
    printf 'path=%s\n' "${room}"
    printf 'last_touched=%s (%s)\n' "${ts}" "$(date -r "${ts}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -d "@${ts}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '?')"
  } > "${tmp}/head.txt" || ok=0
  { [ -z "${st}" ] || printf '%s\n' "${st}"; } > "${tmp}/status.txt" || ok=0
  # git diff は index を書き直すことがある（GIT_OPTIONAL_LOCKS では止まらない）。部屋の index の時刻が新しくならないよう、
  # index の写しに向けて流す（残した部屋が翌日「最近触った」扱いにならないため）
  local _gd
  _gd=$("${_g[@]}" rev-parse --absolute-git-dir 2>/dev/null) || ok=0
  cp -p "${_gd}/index" "${tmp}/.diff-index" 2>/dev/null || ok=0
  GIT_INDEX_FILE="${tmp}/.diff-index" "${_g[@]}" diff --cached --binary --no-renames --no-ext-diff --no-textconv --ignore-submodules=all > "${tmp}/staged.patch" 2>/dev/null || ok=0
  GIT_INDEX_FILE="${tmp}/.diff-index" "${_g[@]}" diff --binary --no-renames --no-ext-diff --no-textconv --ignore-submodules=all > "${tmp}/unstaged.patch" 2>/dev/null || ok=0
  rm -f "${tmp}/.diff-index"
  if [ -s "${tmp}/.untracked.lst" ]; then
    tar -cf "${tmp}/untracked.tar" -C "${room}" --null -T "${tmp}/.untracked.lst" 2>/dev/null || ok=0
  else
    : > "${tmp}/untracked.tar" || ok=0
  fi
  if [ -s "${tmp}/.ignored.lst" ]; then
    tar -cf "${tmp}/ignored.tar" -C "${room}" --null -T "${tmp}/.ignored.lst" 2>/dev/null || ok=0
  else
    : > "${tmp}/ignored.tar" || ok=0
  fi
  tr '\0' '\n' < "${tmp}/.ignored.lst" > "${tmp}/ignored.list" || ok=0

  # origin から届かないコミット（§3-3 の unpushed.bundle）
  if [ "${branch}" != "(detached)" ]; then
    n=$("${_g[@]}" rev-list --count HEAD --not --remotes=origin 2>/dev/null) || { n=0; ok=0; }
    if [ "${n}" != "0" ]; then
      "${_g[@]}" bundle create "${tmp}/unpushed.bundle" HEAD --not --remotes=origin >/dev/null 2>&1 || ok=0
    fi
  else
    if ! "${_g[@]}" rev-parse -q --verify "refs/remotes/origin/${BASE_BRANCH}" >/dev/null 2>&1; then
      ok=0   # origin/<main> が無いと届くか分からない → 残す
    elif ! "${_g[@]}" merge-base --is-ancestor HEAD "refs/remotes/origin/${BASE_BRANCH}" 2>/dev/null; then
      "${_g[@]}" bundle create "${tmp}/unpushed.bundle" HEAD --not "refs/remotes/origin/${BASE_BRANCH}" >/dev/null 2>&1 || ok=0
    fi
    # HEAD から届かない reflog は写さない（件数だけ出す）
    n=0
    while IFS= read -r f; do
      [ -n "${f}" ] || continue
      "${_g[@]}" merge-base --is-ancestor "${f}" HEAD 2>/dev/null || n=$(( n + 1 ))
    done < <("${_g[@]}" reflog show --format=%H HEAD 2>/dev/null | head -100)
    [ "${n}" -gt 0 ] && echo "   ℹ️  HEAD から届かない reflog ${n} 件は写していません: ${room}"
  fi

  # ── 照合（1 つでも合わなければ消さない）──
  if [ "${ok}" -eq 1 ]; then
    # patch の diff --git の数 ＝ status の 1 文字目・2 文字目の変更の数
    sc=$(awk 'length($0)>0 && substr($0,1,1)!=" " && substr($0,1,1)!="?" && substr($0,1,1)!="!" {n++} END{print n+0}' "${tmp}/status.txt")
    uc=$(awk 'length($0)>0 && substr($0,2,1)!=" " && substr($0,2,1)!="?" && substr($0,2,1)!="!" {n++} END{print n+0}' "${tmp}/status.txt")
    ds=$(grep -c '^diff --git ' "${tmp}/staged.patch" || true)
    du_=$(grep -c '^diff --git ' "${tmp}/unstaged.patch" || true)
    [ "${ds:-x}" = "${sc}" ] || ok=0
    [ "${du_:-x}" = "${uc}" ] || ok=0
  fi
  if [ "${ok}" -eq 1 ]; then
    # 一時の index で、ステージ済み → 未ステージの順に当たることを確かめる（部屋の index は触らない）
    ti="${tmp}/.tmp-index"
    GIT_INDEX_FILE="${ti}" "${_g[@]}" read-tree HEAD >/dev/null 2>&1 || ok=0
    if [ "${ok}" -eq 1 ] && [ -s "${tmp}/staged.patch" ]; then
      GIT_INDEX_FILE="${ti}" "${_g[@]}" apply --cached --binary "${tmp}/staged.patch" >/dev/null 2>&1 || ok=0
    fi
    if [ "${ok}" -eq 1 ] && [ -s "${tmp}/unstaged.patch" ]; then
      GIT_INDEX_FILE="${ti}" "${_g[@]}" apply --cached --check --binary "${tmp}/unstaged.patch" >/dev/null 2>&1 || ok=0
    fi
    rm -f "${ti}"
  fi
  if [ "${ok}" -eq 1 ]; then
    # tar の件数 ＝ status の ?? の数、ignored.list の行数
    n=0; [ -s "${tmp}/untracked.tar" ] && n=$(tar -tf "${tmp}/untracked.tar" 2>/dev/null | wc -l | tr -d ' ')
    [ "${n}" = "$(grep -c '^?? ' "${tmp}/status.txt" || true)" ] || ok=0
    n=0; [ -s "${tmp}/ignored.tar" ] && n=$(tar -tf "${tmp}/ignored.tar" 2>/dev/null | wc -l | tr -d ' ')
    [ "${n}" = "$(wc -l < "${tmp}/ignored.list" | tr -d ' ')" ] || ok=0
  fi
  if [ "${ok}" -eq 1 ] && [ -e "${tmp}/unpushed.bundle" ]; then
    "${_g[@]}" bundle verify "${tmp}/unpushed.bundle" >/dev/null 2>&1 || ok=0
  fi
  rm -f "${tmp}/.untracked.lst" "${tmp}/.ignored.raw" "${tmp}/.ignored.lst"
  if [ "${ok}" -eq 1 ]; then
    n=$(du -sk "${tmp}" 2>/dev/null | awk '{print $1}')
    [ "${n:-999999999}" -le $(( ARCHIVE_MAX_MB * 1024 )) ] || ok=0
  fi
  if [ "${ok}" -ne 1 ]; then
    _reaper_drop_inprogress "${tmp}"
    echo "   ⏭  残す（写しの照合が合わない。作りかけは消した）: ${room}"; return 1
  fi

  # 消す直前にもう一度、使用中でないことを確かめる（I4）
  if _reaper_in_use "${room}" "$(lsof -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"; then
    _reaper_drop_inprogress "${tmp}"
    echo "   ⏭  残す（消す直前に使用中になった）: ${room}"; return 1
  fi
  if ! mv "${tmp}" "${dest}" 2>/dev/null; then
    _reaper_drop_inprogress "${tmp}"
    echo "   ⏭  残す（写しを完成の名前へ変えられない）: ${room}"; return 1
  fi
  # 部屋を消す途中で止まっても、戻すべき写しが記録から分かるように、消す前に書く
  _reaper_log "写し完成: ${room} → ${dest}"
  return 0
}

# 置き忘れの部屋の片付け（§3-1）。dry-run は候補の名前と件数だけ（du も写しもしない）
_reaper_idle_stage() {
  local now limit_sec ts room branch e out
  local ELIGIBLE=() sorted
  now=$(date +%s)
  limit_sec=$(( IDLE_DAYS * 86400 ))
  if [ "${#IDLE_CANDIDATES[@]}" -gt 0 ]; then
    sorted=$(printf '%s\n' "${IDLE_CANDIDATES[@]}" | sort -n -t $'\t' -k1,1)   # 古い順
    while IFS=$'\t' read -r ts room branch; do
      [ -n "${room}" ] || continue
      [ $(( now - ts )) -ge "${limit_sec}" ] || continue                       # I7
      _reaper_is_locked "${room}" && continue                                  # I5
      if git "${GIT_SAFE_ARGS[@]}" -C "${room}" ls-files --stage 2>/dev/null | grep -q '^160000 '; then
        echo "   ⏭  残す（入れ子のリポジトリがある）: ${room}"; continue        # I8
      fi
      if [ "${branch}" != "(detached)" ]; then                                 # I6: 失敗・空は残す
        out=$(gh pr list --repo "${REPO_NAME}" --state open --head "${branch}" --json number --jq 'length' 2>/dev/null) || continue
        [ "${out}" = "0" ] || continue
      fi
      ELIGIBLE+=("${room}"$'\t'"${branch}"$'\t'"${ts}")
    done <<< "${sorted}"
  fi

  echo "🧹 置き忘れの候補（${IDLE_DAYS} 日以上触っておらず PR が開いていない）: ${#ELIGIBLE[@]} 件"
  for e in "${ELIGIBLE[@]}"; do
    IFS=$'\t' read -r room branch ts <<< "${e}"
    echo "   - ${branch}（${room}）"
  done
  echo ""
  [ "${EXECUTE}" -eq 1 ] || return 0
  [ "${#ELIGIBLE[@]}" -gt 0 ] || return 0

  local done_n=0 arch_n=0
  for e in "${ELIGIBLE[@]}"; do
    [ "${done_n}" -lt "${IDLE_MAX_PER_RUN}" ] || break
    IFS=$'\t' read -r room branch ts <<< "${e}"
    echo "  ▶ 置き忘れ: ${branch}（${room}）"
    _reaper_archive_room "${room}" "${branch}" "${ts}" || continue
    if git -C "${MAIN_REPO_ROOT}" worktree remove --force "${room}" 2>/dev/null; then
      done_n=$(( done_n + 1 ))
      _reaper_log "置き忘れを片付け: ${room} → 写し ${_ARCH_DEST}"
      [ -d "${_ARCH_DEST}" ] && arch_n=$(( arch_n + 1 ))
    else
      _reaper_log "片付けに失敗: ${room}（写しは ${_ARCH_DEST} に残した）"
    fi
  done
  git -C "${MAIN_REPO_ROOT}" worktree prune 2>/dev/null || true
  echo "片付け ${done_n} 件 / 写し ${arch_n} 件"
  echo ""
}

# ── 分類バケット ────────────────────────────────────────────────────────────
WILL_DELETE=()
SKIP_IN_PROGRESS=()
SKIP_UNSAVED=()
SKIP_NOT_MERGED=()
SKIP_IN_USE=()
SKIP_BASE_BRANCH=()
SKIP_LINK=()
# R9: 下書きを許容した部屋の「部屋のパス::相対パス」（実削除前に控える）
DRAFT_BACKUPS=()
# R13: 置き忘れの候補（"<時刻>\t<パス>\t<ブランチ>"）・鍵付きの部屋・branch 行の無い（detached）部屋
IDLE_CANDIDATES=()
LOCKED_PATHS=()
DETACHED_PATHS=()
IDLE_ENABLED=0
[ -z "${REAPER_WORKTREES_DIR:-}" ] && IDLE_ENABLED=1
IDLE_DAYS="${REAPER_IDLE_DAYS:-14}"
IDLE_MAX_PER_RUN="${REAPER_IDLE_MAX_PER_RUN:-30}"
ARCHIVE_MAX_MB="${REAPER_ARCHIVE_MAX_MB:-200}"
ARCHIVE_ROOT="$(git -C "${MAIN_REPO_ROOT}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)/reaper-archive"

# ── worktree リスト収集 ──────────────────────────────────────────────────────
# REAPER_WORKTREES_DIR 指定あり（テスト用オーバーライド）: 単一ディレクトリ走査
# 指定なし（本番）: git worktree list --porcelain で全登録 worktree を対象にする
# 結果: WT_PATHS / WT_BRANCHES 並列配列（同インデックスが対応）
WT_PATHS=()
WT_BRANCHES=()

if [ -n "${REAPER_WORKTREES_DIR:-}" ]; then
  # ── テストモード: 単一ディレクトリ走査（REAPER_WORKTREES_DIR 優先）────────
  _SCAN_DIR="${REAPER_WORKTREES_DIR}"
  echo "🔍 worktree を走査（ディレクトリ指定）: ${_SCAN_DIR}"
  echo ""

  if [ ! -d "${_SCAN_DIR}" ]; then
    echo "📂 ${_SCAN_DIR} が存在しません"
    exit 0
  fi

  for _WT_PATH in "${_SCAN_DIR}"/*/; do
    [ -d "${_WT_PATH}" ] || continue
    _WT_ID_FILE="${_WT_PATH}.worktree-id"
    if [ -f "${_WT_ID_FILE}" ]; then
      _WT_BRANCH=$(python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get('branch',''))
except Exception:
    print('')
" "${_WT_ID_FILE}" 2>/dev/null || echo "")
    else
      # .worktree-id なし（旧 worktree）: git から現在ブランチ名を取得
      _WT_BRANCH=$(git "${GIT_SAFE_ARGS[@]}" -C "${_WT_PATH}" branch --show-current 2>/dev/null || echo "")
    fi
    [ -z "${_WT_BRANCH}" ] && continue
    WT_PATHS+=("${_WT_PATH}")
    WT_BRANCHES+=("${_WT_BRANCH}")
  done
else
  # ── 本番モード: git worktree list --porcelain で全登録 worktree を対象にする
  # フォーマット: worktree <path> / HEAD <hash> / branch refs/heads/<name> / (空行)
  # 最初のエントリ（メインリポジトリ）はスキップ。detached HEAD（branch行なし）もスキップ。
  echo "🔍 worktree を走査（全件）: git worktree list"
  echo ""

  _WT_PATH=""
  _WT_BRANCH=""
  _WT_DETACHED=0
  _IS_FIRST=1
  while IFS= read -r _LINE; do
    case "${_LINE}" in
      worktree\ *)
        # 前エントリを確定（空パスまたは branch なしはスキップ。detached は R13 の候補用に別に持つ）
        if [ -n "${_WT_PATH}" ] && [ -n "${_WT_BRANCH}" ]; then
          WT_PATHS+=("${_WT_PATH}")
          WT_BRANCHES+=("${_WT_BRANCH}")
        elif [ -n "${_WT_PATH}" ] && [ "${_WT_DETACHED}" -eq 1 ]; then
          DETACHED_PATHS+=("${_WT_PATH}")
        fi
        _WT_PATH="${_LINE#worktree }"
        _WT_BRANCH=""
        _WT_DETACHED=0
        # 最初のエントリ（メインリポジトリ）をスキップ
        if [ "${_IS_FIRST}" -eq 1 ]; then
          _WT_PATH=""
          _IS_FIRST=0
        fi
        ;;
      branch\ refs/heads/*)
        _WT_BRANCH="${_LINE#branch refs/heads/}"
        ;;
      detached)
        _WT_DETACHED=1
        ;;
      locked|locked\ *)
        # I5: 鍵がかかっている部屋（最初のエントリ=本店は _WT_PATH が空なので入らない）
        [ -n "${_WT_PATH}" ] && LOCKED_PATHS+=("${_WT_PATH}")
        ;;
    esac
  # 末尾に sentinel を流して最後のエントリの確定トリガーにする
  done < <(git -C "${MAIN_REPO_ROOT}" worktree list --porcelain 2>/dev/null; echo "worktree __END__")
fi

echo "   対象 worktree 数: ${#WT_PATHS[@]} 件"
echo ""

# R13: 前の回が途中で止まって残った作りかけの写しを消す（実削除の回の最初。消すのは直下の .inprogress- だけ）
if [ "${IDLE_ENABLED}" -eq 1 ] && [ "${EXECUTE}" -eq 1 ] && [ -d "${ARCHIVE_ROOT}" ]; then
  for _IP in "${ARCHIVE_ROOT}"/.inprogress-*; do
    [ -d "${_IP}" ] && [ ! -L "${_IP}" ] || continue
    _reaper_drop_inprogress "${_IP}" && echo "   🧹 作りかけの写しを消しました: ${_IP##*/}"
  done
fi

# ── 使用中の検出用: 全プロセスの作業ディレクトリ（cwd）一覧を1回だけ取得 ──
_CWD_LIST="$(lsof -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"

# ── worktree 走査 ──────────────────────────────────────────────────────────
for _IDX in "${!WT_PATHS[@]}"; do
  WORKTREE_PATH="${WT_PATHS[${_IDX}]}"
  BRANCH="${WT_BRANCHES[${_IDX}]}"

  # ── チェック -1（ADR-1039 便2b-2）: 本番の走査では、git を動かす前に git の繋がりを確かめる ──
  # 合わない部屋には git を1回も動かさず、消さない。
  if [ -z "${REAPER_WORKTREES_DIR:-}" ]; then
    if ! git_safe_link_ok "${WORKTREE_PATH}" "${MAIN_REPO_ROOT}"; then
      SKIP_LINK+=("${BRANCH}（${GIT_SAFE_LINK_REASON}）")
      continue
    fi
  fi

  # ── チェック 0: 本体ブランチ（main・develop・PR の行き先）の worktree は候補にしない ──
  case "${BRANCH}" in
    main|develop|"${BASE_BRANCH}")
      SKIP_BASE_BRANCH+=("${BRANCH}")
      continue
      ;;
  esac

  # ── チェック 1: active-work.md のステータス ──────────────────────────────
  ACTIVE_STATUS="NOT_FOUND"
  ROW="$(ACTIVE_WORK_FILE="${ACTIVE_WORK_FILE}" bash "$(dirname "$0")/ledger-lookup.sh" "${BRANCH}" 2>/dev/null)"
  if [ -n "${ROW}" ]; then
    ACTIVE_STATUS="$(echo "${ROW}" | awk -F'|' '{gsub(/^ +| +$/, "", $5); print $5}')"
    [ -z "${ACTIVE_STATUS}" ] && ACTIVE_STATUS="ERROR"
  fi

  # ── チェック 1.5: 使用中（そのフォルダか配下を cwd にしているプロセスがある）なら保護 ──
  # マージ直後の即時回収（R2）で、まだ作業中のセッションのフォルダを消さないため。
  _WT_NORM="${WORKTREE_PATH%/}"
  if printf '%s\n' "${_CWD_LIST}" | awk -v p="${_WT_NORM}" '$0==p || index($0, p"/")==1 {f=1} END {exit !f}'; then
    SKIP_IN_USE+=("${BRANCH}")
    continue
  fi

  # ── R13: 最後に触った時刻（I3 の繋がりの確かめの後・最初の status の前に取る。§3-2）──
  # $HOME/worktrees/ の下の部屋だけ。取れなければ「今」（消さない側）。
  _ROOM_TS=""
  if [ "${IDLE_ENABLED}" -eq 1 ]; then
    case "${_WT_NORM}/" in "${HOME%/}/worktrees/"*) _ROOM_TS="$(_reaper_last_touch "${WORKTREE_PATH}")" ;; esac
  fi

  # ── チェック 2: 未保存の作業がないか（最優先保護） ──────────────────────
  # 判定順:
  #   a. 未コミット・未ステージ確認
  #   b. HEAD までの全コミットが origin のどれかの ref から到達できるか（R8）
  UNSAVED=0
  _NESTED_REPO=0
  # git status は HEAD なしの fresh init でも動く（untracked files を検出可能）
  if git "${GIT_SAFE_ARGS[@]}" -C "${WORKTREE_PATH}" status --ignore-submodules=all >/dev/null 2>&1; then
    # a. 未コミット・未ステージ確認
    # 2026-07-25 対策A: 台帳(.claude-pipeline/)のみの変更は未保存保護から除外する。
    # 理由: 完了記録が worktree 側の台帳に未コミットで残り、マージ済みの机が永続保護されていた。
    # 実測(origin/main=1bbd338): 未保存37件中28件が .claude-pipeline/ のみ・手書き混入0件。台帳以外があれば従来どおり保護。
    # R9(2026-10-11): 未追跡の *pr-body*.md（PR 本文の下書き）は候補として別に集め、下の検証を通ったときだけ許容する。
    #   --untracked-files=all で未追跡ディレクトリの中のファイル名まで見る。それ以外の行が1行でもあれば従来どおり保護。
    DRAFT_CANDIDATES=()
    # ADR-1039/R11: 入れ子のリポジトリ（mode 160000）がある部屋は消さない。
    #   status に --ignore-submodules=all を付けると入れ子の中の未保存が見えなくなるため、ここで印を見て残す。
    #   ls-files --stage は入れ子の中に入らない。
    if git "${GIT_SAFE_ARGS[@]}" -C "${WORKTREE_PATH}" ls-files --stage 2>/dev/null | grep -q '^160000 '; then
      UNSAVED=1
      _NESTED_REPO=1
    fi
    while IFS= read -r _SLINE; do
      [ -z "${_SLINE}" ] && continue
      case "${_SLINE}" in *.claude-pipeline/*) continue ;; esac
      if [[ "${_SLINE}" == "?? "* ]]; then
        _SPATH="${_SLINE#\?\? }"
        case "${_SPATH##*/}" in
          *pr-body*.md) DRAFT_CANDIDATES+=("${_SPATH}"); continue ;;
        esac
      fi
      UNSAVED=1
    done < <(git "${GIT_SAFE_ARGS[@]}" -C "${WORKTREE_PATH}" status --porcelain --untracked-files=all --ignore-submodules=all 2>/dev/null)

    if [ "${UNSAVED}" -eq 0 ]; then
      # b. 取り戻せるか（R8、2026-10-10 PO 方針「後から完全に取り戻せる部屋だけ消す」）
      #    HEAD までのコミットが、origin のどれかの ref（main・各ブランチ）から到達できること。
      #    1つでも GitHub に無いコミットがあれば保護する。upstream の設定有無・向き先は問わない。
      #    コミットが1つも無い（HEAD なし）部屋は、失うコミットが無いので判定しない。
      if git "${GIT_SAFE_ARGS[@]}" -C "${WORKTREE_PATH}" rev-parse -q --verify HEAD >/dev/null 2>&1; then
        _UNREACH=$(git "${GIT_SAFE_ARGS[@]}" -C "${WORKTREE_PATH}" rev-list --count HEAD --not --remotes=origin 2>/dev/null) || _UNREACH="ERR"
        if [ "${_UNREACH}" != "0" ]; then
          UNSAVED=1
        fi
      fi
    fi

    # R9: 下書き候補があり、他に未保存が無いときだけ、マージ済み PR の本文と照合する。
    #   ① main へのマージ済み PR の本文を取れる（失敗・空は保護）  ② 下書きが空でない
    #   ③ 下書きの全行が本文にある（末尾の空白・\r を除いて比較。本文に無い行が0）
    if [ "${UNSAVED}" -eq 0 ] && [ "${#DRAFT_CANDIDATES[@]}" -gt 0 ]; then
      _PR_BODY=$(gh pr list \
        --repo "${REPO_NAME}" \
        --state merged \
        --head "${BRANCH}" \
        --json baseRefName,body \
        --jq '[.[]|select(.baseRefName=="'"${BASE_BRANCH}"'")]|.[0].body // empty' \
        2>/dev/null) || _PR_BODY=""
      if [ -z "${_PR_BODY}" ]; then
        UNSAVED=1
      else
        _ROOM_DRAFTS=()
        for _DREL in "${DRAFT_CANDIDATES[@]}"; do
          _DFILE="${WORKTREE_PATH%/}/${_DREL}"
          if [ ! -s "${_DFILE}" ]; then
            UNSAVED=1
            break
          fi
          _MISSING=$(diff \
            <(sed 's/[[:space:]]*$//' "${_DFILE}") \
            <(printf '%s\n' "${_PR_BODY}" | sed 's/[[:space:]]*$//') 2>/dev/null | grep -c '^<') || true
          if [ "${_MISSING:-1}" != "0" ]; then
            UNSAVED=1
            break
          fi
          _ROOM_DRAFTS+=("${WORKTREE_PATH}::${_DREL}")
        done
        if [ "${UNSAVED}" -eq 0 ]; then
          DRAFT_BACKUPS+=("${_ROOM_DRAFTS[@]}")
        fi
      fi
    fi
  fi
  # git が存在しない場合（.git なし）は orphaned dir として UNSAVED=0 のまま（安全に削除可）

  if [ "${UNSAVED}" -eq 1 ]; then
    if [ "${_NESTED_REPO}" -eq 1 ]; then
      SKIP_UNSAVED+=("${BRANCH}（入れ子のリポジトリがある（残す））")
    else
      SKIP_UNSAVED+=("${BRANCH}")
    fi
    [ -n "${_ROOM_TS}" ] && _reaper_push_idle "${WORKTREE_PATH}" "${BRANCH}" "${_ROOM_TS}"
    continue
  fi

  # ── チェック 3: DONE またはマージ済み ────────────────────────────────────
  IS_DONE=0
  [ "${ACTIVE_STATUS}" = "DONE" ] && IS_DONE=1

  if [ "${IS_DONE}" -eq 0 ]; then
    # gh で PR マージ済み確認（squash マージでも機能）
    # main へのマージを検知（release/hotfix の main マージも対象）
    # エラー時は 0 扱い（安全側）
    MERGED_COUNT=$(gh pr list \
      --repo "${REPO_NAME}" \
      --state merged \
      --head "${BRANCH}" \
      --json number,baseRefName \
      --jq '[.[] | select(.baseRefName == "'"${BASE_BRANCH}"'")] | length' \
      2>/dev/null || echo "0")
    [ "${MERGED_COUNT:-0}" -gt 0 ] && IS_DONE=1
  fi

  if [ "${IS_DONE}" -eq 0 ]; then
    # CLOSED（却下）PR も削除対象: mergedAt=null かつ state=CLOSED
    # マージせず閉じられたブランチ（放棄・却下）は保持する意味がない
    # PRなし（CLOSED_COUNT=0）は保護のまま（保護条件変えず）
    # 未保存保護は前段（チェック2）で既に通過済み → CLOSED でも未保存なら削除しない
    CLOSED_COUNT=$(gh pr list \
      --repo "${REPO_NAME}" \
      --state closed \
      --head "${BRANCH}" \
      --json number,baseRefName,mergedAt \
      --jq '[.[] | select(.baseRefName == "'"${BASE_BRANCH}"'") | select(.mergedAt == null)] | length' \
      2>/dev/null || echo "0")
    [ "${CLOSED_COUNT:-0}" -gt 0 ] && IS_DONE=1
  fi

  # DONE またはマージ済み → 削除候補
  if [ "${IS_DONE}" -eq 1 ]; then
    WILL_DELETE+=("${BRANCH}::${WORKTREE_PATH}")
    continue
  fi

  # IN_PROGRESS または REVIEW かつ未マージ → 保護（マージ済みなら上で回収済み）
  if [ "${ACTIVE_STATUS}" = "IN_PROGRESS" ] || [ "${ACTIVE_STATUS}" = "REVIEW" ]; then
    SKIP_IN_PROGRESS+=("${BRANCH}")
    [ -n "${_ROOM_TS}" ] && _reaper_push_idle "${WORKTREE_PATH}" "${BRANCH}" "${_ROOM_TS}"
    continue
  fi

  # その他（NOT_FOUND・ERROR 等）かつ未マージ → 保護
  SKIP_NOT_MERGED+=("${BRANCH}")
  [ -n "${_ROOM_TS}" ] && _reaper_push_idle "${WORKTREE_PATH}" "${BRANCH}" "${_ROOM_TS}"
done

# ── R13（§3-4）: branch 行の無い（detached）部屋も置き忘れの候補にする ──────────────
# 本ループの外で積むため、I3（git_safe_link_ok）を最初の git 命令より前に当てる。I2・I6 はブランチが無いので飛ばす。
if [ "${IDLE_ENABLED}" -eq 1 ]; then
  for _DP in "${DETACHED_PATHS[@]}"; do
    case "${_DP%/}/" in "${HOME%/}/worktrees/"*) ;; *) continue ;; esac
    git_safe_link_ok "${_DP}" "${MAIN_REPO_ROOT}" || { SKIP_LINK+=("(detached) ${_DP##*/}（${GIT_SAFE_LINK_REASON}）"); continue; }
    _reaper_in_use "${_DP}" "${_CWD_LIST}" && { SKIP_IN_USE+=("(detached) ${_DP##*/}"); continue; }
    _reaper_push_idle "${_DP}" "(detached)" "$(_reaper_last_touch "${_DP}")"
  done
fi

if [ "${FETCH_OK}" -eq 0 ] && [ "${#WILL_DELETE[@]}" -gt 0 ]; then
  echo "⚠️  fetch 失敗のため、削除候補 ${#WILL_DELETE[@]} 件は今回は削除しません。"
  WILL_DELETE=()
fi
# fetch が失敗した回は、置き忘れの候補も空にして何も消さない
if [ "${FETCH_OK}" -eq 0 ]; then
  IDLE_CANDIDATES=()
fi

# ── サマリ表示 ────────────────────────────────────────────────────────────
echo "=== reaper 結果 ==="
echo ""

if [ "${#SKIP_IN_USE[@]}" -gt 0 ]; then
  echo "🧑‍💻 使用中（削除しない）: ${#SKIP_IN_USE[@]} 件"
  for B in "${SKIP_IN_USE[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#SKIP_LINK[@]}" -gt 0 ]; then
  echo "🔗 git の繋がりが本店と合わない（削除しない）: ${#SKIP_LINK[@]} 件"
  for B in "${SKIP_LINK[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#SKIP_BASE_BRANCH[@]}" -gt 0 ]; then
  echo "🛡️  本体ブランチ（削除しない）: ${#SKIP_BASE_BRANCH[@]} 件"
  for B in "${SKIP_BASE_BRANCH[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#SKIP_IN_PROGRESS[@]}" -gt 0 ]; then
  echo "🔒 IN_PROGRESS/REVIEW 未マージ（削除しない）: ${#SKIP_IN_PROGRESS[@]} 件"
  for B in "${SKIP_IN_PROGRESS[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#SKIP_UNSAVED[@]}" -gt 0 ]; then
  echo "⚠️  未保存あり（削除しない）: ${#SKIP_UNSAVED[@]} 件 ← 人の判断が必要"
  for B in "${SKIP_UNSAVED[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#SKIP_NOT_MERGED[@]}" -gt 0 ]; then
  echo "🔄 未マージ（削除しない）: ${#SKIP_NOT_MERGED[@]} 件"
  for B in "${SKIP_NOT_MERGED[@]}"; do echo "   - ${B}"; done
  echo ""
fi

# ── ゴースト検出（git 未登録の実体ディレクトリ）──────────────────────────────
# ~/worktrees/<repo>/ を走査し、git worktree list に登録されていないディレクトリを警告する
# 2026-09-05: 5件・830MB のゴーストが発生。reaper は git worktree list 経由のため
#             git 登録が外れた実体ディレクトリを永久に検出できなかった。本ブロックで補完する。
# ★ 削除はしない。警告のみ。
_GHOST_SCAN_DIR="${HOME}/worktrees/$(basename "${MAIN_REPO_ROOT}")"

# 登録済み worktree パスを収集
_REGISTERED_WT_PATHS=()
while IFS= read -r _LINE; do
  case "${_LINE}" in
    worktree\ *) _REGISTERED_WT_PATHS+=("${_LINE#worktree }") ;;
  esac
done < <(git -C "${MAIN_REPO_ROOT}" worktree list --porcelain 2>/dev/null)

GHOST_COUNT=0
GHOST_TOTAL_KB=0
GHOST_ENTRIES=()

if [ -d "${_GHOST_SCAN_DIR}" ]; then
  for _GDIR in "${_GHOST_SCAN_DIR}"/*/; do
    [ -d "${_GDIR}" ] || continue
    _GDIR_PATH="${_GDIR%/}"
    _IS_REG=0
    for _REGP in "${_REGISTERED_WT_PATHS[@]}"; do
      if [ "${_GDIR_PATH}" = "${_REGP}" ]; then
        _IS_REG=1
        break
      fi
    done
    if [ "${_IS_REG}" -eq 0 ]; then
      _SIZE_KB=$(du -sk "${_GDIR_PATH}" 2>/dev/null | awk '{print $1}')
      _SIZE_MB=$(awk "BEGIN {printf \"%.1f\", ${_SIZE_KB:-0}/1024}")
      GHOST_ENTRIES+=("${_GDIR_PATH} (${_SIZE_MB} MB)")
      GHOST_COUNT=$(( GHOST_COUNT + 1 ))
      GHOST_TOTAL_KB=$(( GHOST_TOTAL_KB + ${_SIZE_KB:-0} ))
    fi
  done
fi

echo "=== ゴースト検出 ==="
echo "   走査: ${_GHOST_SCAN_DIR}"
echo ""
if [ "${GHOST_COUNT}" -eq 0 ]; then
  echo "👻 GHOST: 0件"
else
  for _GE in "${GHOST_ENTRIES[@]}"; do
    echo "   👻 GHOST: ${_GE}"
  done
  _TOTAL_MB=$(awk "BEGIN {printf \"%.1f\", ${GHOST_TOTAL_KB}/1024}")
  echo ""
  echo "⚠️  GHOST 合計: ${GHOST_COUNT} 件 / ${_TOTAL_MB} MB（手動確認してください）"
fi
echo ""

# ── R13: 置き忘れの部屋の片付け（既存の「削除対象なし」の終わり・dry-run の終わりより前）──
if [ "${IDLE_ENABLED}" -eq 1 ]; then
  _reaper_idle_stage
fi

if [ "${#WILL_DELETE[@]}" -eq 0 ]; then
  echo "✅ 削除対象なし"
  exit 0
fi

echo "🗑️  削除対象（安全条件クリア）: ${#WILL_DELETE[@]} 件"
for ENTRY in "${WILL_DELETE[@]}"; do
  BRANCH="${ENTRY%%::*}"
  WPATH="${ENTRY#*::}"
  _NDRAFT=0
  for _DB in "${DRAFT_BACKUPS[@]}"; do
    [ "${_DB%%::*}" = "${WPATH}" ] && _NDRAFT=$(( _NDRAFT + 1 ))
  done
  if [ "${_NDRAFT}" -gt 0 ]; then
    echo "   - ${BRANCH}（PR本文の下書き ${_NDRAFT} 件は GitHub の本文と一致）"
  else
    echo "   - ${BRANCH}"
  fi
done
echo ""

if [ "${EXECUTE}" -eq 0 ]; then
  echo "ℹ️  dry-run モード（上記は削除候補の一覧です）"
  echo "   実削除するには: bash scripts/reaper-worktree.sh --execute"
  exit 0
fi

# ── 実削除 ────────────────────────────────────────────────────────────────
echo "🗑️  削除を実行します..."
DELETED=0

for ENTRY in "${WILL_DELETE[@]}"; do
  BRANCH="${ENTRY%%::*}"
  WPATH="${ENTRY#*::}"

  echo ""
  echo "  ▶ ${BRANCH}"

  # R9: 許容した PR 本文の下書きを、消す前に .git 内（git 管理外）へ控える。1件でも失敗したらこの部屋は消さない。
  _DRAFT_DIR="$(git -C "${MAIN_REPO_ROOT}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)/reaper-drafts/${BRANCH//\//-}"
  _BACKUP_OK=1
  for _DB in "${DRAFT_BACKUPS[@]}"; do
    [ "${_DB%%::*}" = "${WPATH}" ] || continue
    _DREL="${_DB#*::}"
    _DEST="${_DRAFT_DIR}/${_DREL}"
    if mkdir -p "$(dirname "${_DEST}")" && cp -p "${WPATH%/}/${_DREL}" "${_DEST}"; then
      echo "    📝 下書きを控えました: ${_DEST}"
    else
      echo "    ⚠️  下書きの控えに失敗: ${_DREL}。この部屋は削除しません。"
      _BACKUP_OK=0
      break
    fi
  done
  if [ "${_BACKUP_OK}" -eq 0 ]; then
    continue
  fi

  # worktree フォルダ削除
  git -C "${MAIN_REPO_ROOT}" worktree remove --force "${WPATH}" 2>/dev/null && \
    echo "    ✅ フォルダ削除: ${WPATH}" || \
    echo "    ⚠️  フォルダ削除スキップ（既に存在しないか登録解除済み）"

  # ローカルブランチ削除
  git -C "${MAIN_REPO_ROOT}" branch -D "${BRANCH}" 2>/dev/null && \
    echo "    ✅ ブランチ削除: ${BRANCH}" || \
    echo "    ⚠️  ブランチ削除スキップ"

  # active-work.md を DONE に更新（行は消さず残す・窓口経由）
  ROWW="$(ACTIVE_WORK_FILE="${ACTIVE_WORK_FILE}" bash "$(dirname "$0")/ledger-lookup.sh" "${BRANCH}" 2>/dev/null || true)"
  if echo "${ROWW}" | grep -q "IN_PROGRESS"; then
    ACTIVE_WORK_FILE="${ACTIVE_WORK_FILE}" bash "$(dirname "$0")/ledger-update.sh" "${BRANCH}" --status DONE > /dev/null       && echo "    ✅ active-work.md → DONE: ${BRANCH}"       || echo "    ⚠️  active-work.md DONE 更新失敗: ${BRANCH}"
  else
    echo "    ℹ️  active-work.md DONE 更新不要（既に DONE または行なし）: ${BRANCH}"
  fi

  DELETED=$(( DELETED + 1 ))
done

# worktree prune（参照のみ残っているゴミを掃除）
git -C "${MAIN_REPO_ROOT}" worktree prune 2>/dev/null || true

echo ""
echo "✅ reaper 完了: 削除 ${DELETED} 件"
if [ "${#SKIP_UNSAVED[@]}" -gt 0 ]; then
  echo "⚠️  未保存あり ${#SKIP_UNSAVED[@]} 件は保護済み（人が確認してください）"
fi
