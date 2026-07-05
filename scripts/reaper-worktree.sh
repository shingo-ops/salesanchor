#!/bin/bash
# reaper-worktree.sh — マージ済み worktree の自動回収（ADR-114）
#
# 安全条件（非交渉・すべて満たした部屋だけ削除）:
#   ① 未コミット・未push がゼロ（絶対保護・最優先）
#   ② active-work.md が DONE、または gh で PR がマージ済み（main）
#   ③ IN_PROGRESS / REVIEW かつ未マージなら削除しない
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
#
# 使用方法:
#   bash scripts/reaper-worktree.sh            # dry-run（削除予定の一覧のみ）
#   bash scripts/reaper-worktree.sh --execute  # 実削除

EXECUTE=0
if [ "${1:-}" = "--execute" ]; then
  EXECUTE=1
fi

# ── 多重起動ガード（全経路共通: cron / LaunchAgent / 手動）─────────────────
# mkdir はアトミック操作のため macOS/Linux 両対応の排他ロックとして機能する
_REAPER_LOCK="/tmp/reaper-worktree.lock.d"
if ! mkdir "${_REAPER_LOCK}" 2>/dev/null; then
  echo "[reaper] another instance is running; skip."
  exit 0
fi
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

# ── 分類バケット ────────────────────────────────────────────────────────────
WILL_DELETE=()
SKIP_IN_PROGRESS=()
SKIP_UNSAVED=()
SKIP_NOT_MERGED=()

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
      _WT_BRANCH=$(git -C "${_WT_PATH}" branch --show-current 2>/dev/null || echo "")
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

# ── worktree 走査 ──────────────────────────────────────────────────────────
for _IDX in "${!WT_PATHS[@]}"; do
  WORKTREE_PATH="${WT_PATHS[${_IDX}]}"
  BRANCH="${WT_BRANCHES[${_IDX}]}"

  # ── チェック 1: active-work.md のステータス ──────────────────────────────
  ACTIVE_STATUS="NOT_FOUND"
  ROW="$(ACTIVE_WORK_FILE="${ACTIVE_WORK_FILE}" bash "$(dirname "$0")/ledger-lookup.sh" "${BRANCH}" 2>/dev/null)"
  if [ -n "${ROW}" ]; then
    ACTIVE_STATUS="$(echo "${ROW}" | awk -F'|' '{gsub(/^ +| +$/, "", $5); print $5}')"
    [ -z "${ACTIVE_STATUS}" ] && ACTIVE_STATUS="ERROR"
  fi

  # ── チェック 2: 未保存の作業がないか（最優先保護） ──────────────────────
  # 判定順:
  #   a. 未コミット・未ステージ確認
  #   b. upstream 設定済み → @{u}..HEAD で未push 確認
  #   c. upstream 未設定 → origin/<branch> が存在すれば比較する
  #      upstream 未設定だけを理由に未push 扱いしない（設定漏れで削除保護が過剰になるのを防ぐ）
  UNSAVED=0
  # git status は HEAD なしの fresh init でも動く（untracked files を検出可能）
  if git -C "${WORKTREE_PATH}" status >/dev/null 2>&1; then
    # a. 未コミット・未ステージ確認
    if [ -n "$(git -C "${WORKTREE_PATH}" status --porcelain 2>/dev/null)" ]; then
      UNSAVED=1
    fi

    if [ "${UNSAVED}" -eq 0 ]; then
      # b. upstream 設定済みなら @{u}..HEAD で比較
      #    ただし専用棚 origin/<branch> と HEAD が一致していれば push 済みとみなす
      #    （@{u} が共用側（main 等）を指す設定漏れによる誤検出を防ぐ）
      if git -C "${WORKTREE_PATH}" rev-parse "@{u}" >/dev/null 2>&1; then
        OWN_REMOTE=$(git -C "${WORKTREE_PATH}" rev-parse "origin/${BRANCH}" 2>/dev/null || true)
        HEAD_SHA=$(git -C "${WORKTREE_PATH}" rev-parse HEAD 2>/dev/null || true)
        if [ -n "${OWN_REMOTE}" ] && [ "${HEAD_SHA}" = "${OWN_REMOTE}" ]; then
          :  # 専用棚と一致 → push 済み。UNSAVED=0 のまま（保護しない）
        elif [ -n "$(git -C "${WORKTREE_PATH}" log --oneline "@{u}..HEAD" 2>/dev/null)" ]; then
          UNSAVED=1
        fi
      else
        # c. upstream 未設定: origin/<branch> が存在すれば直接比較
        REMOTE_SHA=$(git -C "${WORKTREE_PATH}" rev-parse "origin/${BRANCH}" 2>/dev/null || true)
        if [ -n "${REMOTE_SHA}" ]; then
          LOCAL_SHA=$(git -C "${WORKTREE_PATH}" rev-parse HEAD 2>/dev/null || true)
          if [ -n "${LOCAL_SHA}" ] && [ "${LOCAL_SHA}" != "${REMOTE_SHA}" ]; then
            UNPUSHED=$(git -C "${WORKTREE_PATH}" log --oneline "${REMOTE_SHA}..HEAD" 2>/dev/null || true)
            if [ -n "${UNPUSHED}" ]; then
              UNSAVED=1
            fi
          fi
        fi
        # origin/<branch> も存在しない場合: upstream 未設定だけを理由に未push 扱いしない
      fi
    fi
  fi
  # git が存在しない場合（.git なし）は orphaned dir として UNSAVED=0 のまま（安全に削除可）

  if [ "${UNSAVED}" -eq 1 ]; then
    SKIP_UNSAVED+=("${BRANCH}")
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
      --jq '[.[] | select(.baseRefName == "main")] | length' \
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
      --jq '[.[] | select(.baseRefName == "main") | select(.mergedAt == null)] | length' \
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

# ── サマリ表示 ────────────────────────────────────────────────────────────
echo "=== reaper 結果 ==="
echo ""

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

if [ "${#WILL_DELETE[@]}" -eq 0 ]; then
  echo "✅ 削除対象なし"
  exit 0
fi

echo "🗑️  削除対象（安全条件クリア）: ${#WILL_DELETE[@]} 件"
for ENTRY in "${WILL_DELETE[@]}"; do
  BRANCH="${ENTRY%%::*}"
  echo "   - ${BRANCH}"
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
