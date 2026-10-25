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
# shellcheck disable=SC2064
trap "rmdir '${_REAPER_LOCK}' 2>/dev/null || true" EXIT INT TERM

# ── メインリポジトリルート取得 ──────────────────────────────────────────────
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || echo "")"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then
  MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"
else
  MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
fi

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

# ── 分類バケット ────────────────────────────────────────────────────────────
WILL_DELETE=()
SKIP_IN_PROGRESS=()
SKIP_UNSAVED=()
SKIP_NOT_MERGED=()
SKIP_IN_USE=()
SKIP_BASE_BRANCH=()
# R9: 下書きを許容した部屋の「部屋のパス::相対パス」（実削除前に控える）
DRAFT_BACKUPS=()

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
  _IS_FIRST=1
  while IFS= read -r _LINE; do
    case "${_LINE}" in
      worktree\ *)
        # 前エントリを確定（空パスまたは branch なしはスキップ）
        if [ -n "${_WT_PATH}" ] && [ -n "${_WT_BRANCH}" ]; then
          WT_PATHS+=("${_WT_PATH}")
          WT_BRANCHES+=("${_WT_BRANCH}")
        fi
        _WT_PATH="${_LINE#worktree }"
        _WT_BRANCH=""
        # 最初のエントリ（メインリポジトリ）をスキップ
        if [ "${_IS_FIRST}" -eq 1 ]; then
          _WT_PATH=""
          _IS_FIRST=0
        fi
        ;;
      branch\ refs/heads/*)
        _WT_BRANCH="${_LINE#branch refs/heads/}"
        ;;
    esac
  # 末尾に sentinel を流して最後のエントリの確定トリガーにする
  done < <(git -C "${MAIN_REPO_ROOT}" worktree list --porcelain 2>/dev/null; echo "worktree __END__")
fi

echo "   対象 worktree 数: ${#WT_PATHS[@]} 件"
echo ""

# ── 使用中の検出用: 全プロセスの作業ディレクトリ（cwd）一覧を1回だけ取得 ──
_CWD_LIST="$(lsof -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"

# ── worktree 走査 ──────────────────────────────────────────────────────────
for _IDX in "${!WT_PATHS[@]}"; do
  WORKTREE_PATH="${WT_PATHS[${_IDX}]}"
  BRANCH="${WT_BRANCHES[${_IDX}]}"

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
    continue
  fi

  # その他（NOT_FOUND・ERROR 等）かつ未マージ → 保護
  SKIP_NOT_MERGED+=("${BRANCH}")
done

if [ "${FETCH_OK}" -eq 0 ] && [ "${#WILL_DELETE[@]}" -gt 0 ]; then
  echo "⚠️  fetch 失敗のため、削除候補 ${#WILL_DELETE[@]} 件は今回は削除しません。"
  WILL_DELETE=()
fi

# ── サマリ表示 ────────────────────────────────────────────────────────────
echo "=== reaper 結果 ==="
echo ""

if [ "${#SKIP_IN_USE[@]}" -gt 0 ]; then
  echo "🧑‍💻 使用中（削除しない）: ${#SKIP_IN_USE[@]} 件"
  for B in "${SKIP_IN_USE[@]}"; do echo "   - ${B}"; done
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
