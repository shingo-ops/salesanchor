#!/bin/bash
# git-safe.sh — 囲いの外で作業場所に向けて動かす git に付ける上書き（ADR-1039・discord-pdca 設計 §4-5）
#
# Discord 発のセッションが件の作業場所に仕込んだ設定（core.fsmonitor・core.hooksPath）で、
# 自動回収（reaper-worktree.sh）や片付け（disk-janitor.sh）の git が別の命令を動かさないようにする。
# 使い方: source して、作業場所に向けた git に `git "${GIT_SAFE_ARGS[@]}" -C <場所> ...` と付ける。
# source 時に何も実行しない（配列を定義するだけ）。
# shellcheck disable=SC2034  # source 先で使う
GIT_SAFE_ARGS=(-c core.fsmonitor=false -c core.hooksPath=/dev/null)

# ── git の繋がりの確かめ（ADR-1039 便2b-2・ADR-114 R12）────────────────────────
# 作業場所の .git ファイル・commondir・gitdir が書き換えられ、git が偽の設定（filter の命令入り）を
# 読む道を塞ぐ。合えば 0。合わなければ GIT_SAFE_LINK_REASON に理由を入れて 1。
# realpath が無い・失敗したときは 1（残す側）。確かめの正本はこの2関数の1か所。

# 中身が「1行だけ」のファイルを読む（改行の無い1行も可）。成功で GIT_SAFE_ONE_LINE に入れて 0
_git_safe_read_one_line() {
  local f="$1" lines content
  GIT_SAFE_ONE_LINE=""
  [ -f "$f" ] && [ ! -L "$f" ] || return 1
  lines="$(wc -l < "$f" 2>/dev/null | tr -d ' ')" || return 1
  [ -n "${lines}" ] && [ "${lines}" -le 1 ] || return 1
  content="$(cat "$f" 2>/dev/null)" || return 1
  case "${content}" in *$'\n'*) return 1 ;; esac
  GIT_SAFE_ONE_LINE="${content}"
  return 0
}

# 相対パスなら基点を付け、末尾の / を除いた実パスを返す
_git_safe_resolve() {
  local p="$1" base="$2"
  [ -n "${p}" ] || return 1
  case "${p}" in /*) ;; *) p="${base}/${p}" ;; esac
  command realpath "${p%/}" 2>/dev/null
}

# git_safe_main_ok <元のリポジトリの最上位>
git_safe_main_ok() {
  GIT_SAFE_LINK_REASON=""
  local m="${1:-}"
  m="${m%/}"
  if [ -z "${m}" ]; then GIT_SAFE_LINK_REASON="本店のパスが空"; return 1; fi
  if [ ! -d "${m}/.git" ] || [ -L "${m}/.git" ]; then
    GIT_SAFE_LINK_REASON="本店の .git が本物のディレクトリではない"; return 1
  fi
  if [ -e "${m}/.git/commondir" ] || [ -L "${m}/.git/commondir" ]; then
    GIT_SAFE_LINK_REASON="本店の .git/commondir がある"; return 1
  fi
  if [ -e "${m}/.git/config.worktree" ] || [ -L "${m}/.git/config.worktree" ]; then
    GIT_SAFE_LINK_REASON="本店の .git/config.worktree がある"; return 1
  fi
  return 0
}

# git_safe_link_ok <作業場所> <元のリポジトリの最上位>
git_safe_link_ok() {
  GIT_SAFE_LINK_REASON=""
  local p="${1:-}" m="${2:-}"
  p="${p%/}"; m="${m%/}"
  git_safe_main_ok "${m}" || return 1
  if [ -z "${p}" ]; then GIT_SAFE_LINK_REASON="作業場所のパスが空"; return 1; fi
  local c rp rm_ g rg pdotgit
  c="$(command realpath "${m}/.git" 2>/dev/null)" || { GIT_SAFE_LINK_REASON="本店の .git の実パスを取れない"; return 1; }
  rp="$(command realpath "${p}" 2>/dev/null)" || { GIT_SAFE_LINK_REASON="作業場所の実パスを取れない"; return 1; }
  rm_="$(command realpath "${m}" 2>/dev/null)" || { GIT_SAFE_LINK_REASON="本店の実パスを取れない"; return 1; }
  # 1. 作業場所が本店そのもの
  if [ "${rp}" = "${rm_}" ]; then
    if [ -d "${p}/.git" ] && [ ! -L "${p}/.git" ] && [ "$(command realpath "${p}/.git" 2>/dev/null)" = "${c}" ]; then
      return 0
    fi
    GIT_SAFE_LINK_REASON="本店の .git が本物のディレクトリではない"; return 1
  fi
  # 2. worktree: .git が本物のファイルで、1行だけの「gitdir: <G>」
  pdotgit="${p}/.git"
  if [ ! -f "${pdotgit}" ] || [ -L "${pdotgit}" ]; then
    GIT_SAFE_LINK_REASON=".git が本物のファイルではない"; return 1
  fi
  if ! _git_safe_read_one_line "${pdotgit}"; then
    GIT_SAFE_LINK_REASON=".git ファイルが1行ではない"; return 1
  fi
  case "${GIT_SAFE_ONE_LINE}" in
    "gitdir: "?*) g="${GIT_SAFE_ONE_LINE#gitdir: }" ;;
    *) GIT_SAFE_LINK_REASON=".git ファイルが gitdir: の形ではない"; return 1 ;;
  esac
  rg="$(_git_safe_resolve "${g}" "${p}")" || { GIT_SAFE_LINK_REASON="gitdir の実パスを取れない"; return 1; }
  if [ "$(dirname "${rg}")" != "${c}/worktrees" ]; then
    GIT_SAFE_LINK_REASON="gitdir が本店の .git/worktrees の下ではない"; return 1
  fi
  # 3. commondir
  if ! _git_safe_read_one_line "${rg}/commondir"; then
    GIT_SAFE_LINK_REASON="commondir が読めない・1行ではない"; return 1
  fi
  if [ "$(_git_safe_resolve "${GIT_SAFE_ONE_LINE}" "${rg}")" != "${c}" ]; then
    GIT_SAFE_LINK_REASON="commondir が本店の .git を指していない"; return 1
  fi
  # 4. gitdir
  if ! _git_safe_read_one_line "${rg}/gitdir"; then
    GIT_SAFE_LINK_REASON="gitdir ファイルが読めない・1行ではない"; return 1
  fi
  if [ "$(_git_safe_resolve "${GIT_SAFE_ONE_LINE}" "${rg}")" != "$(command realpath "${pdotgit}" 2>/dev/null)" ]; then
    GIT_SAFE_LINK_REASON="gitdir ファイルが作業場所の .git を指していない"; return 1
  fi
  # 5. config / config.worktree が無い
  if [ -e "${rg}/config" ] || [ -L "${rg}/config" ] || [ -e "${rg}/config.worktree" ] || [ -L "${rg}/config.worktree" ]; then
    GIT_SAFE_LINK_REASON="worktree の置き場に config がある"; return 1
  fi
  return 0
}
