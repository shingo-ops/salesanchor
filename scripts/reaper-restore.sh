#!/bin/bash
# reaper-restore.sh — 置き忘れの部屋（ADR-114 R13）の写しから、部屋を元に戻す
#
# 使い方: bash scripts/reaper-restore.sh <写しの置き場>
#   写しの置き場 = <git-common-dir>/reaper-archive/<YYYYMMDD-HHMMSS>-<部屋の名前>/
#
# 手順（設計 §3-7）:
#   1. （unpushed.bundle があれば）git fetch <bundle> HEAD でコミットを本店に入れる
#   2. git worktree add --detach <元のパス> <head.txt の sha>
#   3. ブランチがあった部屋は git switch <ブランチ>（ブランチの指す先が sha と違えば止めて人に回す）
#   4. git apply --binary --index staged.patch → git apply --binary unstaged.patch
#   5. tar -xf untracked.tar・ignored.tar（部屋の中で）
# 読むのは写しだけ。元のパスに何かあれば何もせず止まる。reset --hard は使わない。
# 失敗したら、そこで止めて理由を出す（途中までの部屋はそのまま残す。人が見る）。

set -u

ARCH="${1:-}"
if [ -z "${ARCH}" ] || [ ! -d "${ARCH}" ] || [ ! -f "${ARCH}/head.txt" ]; then
  echo "使い方: bash scripts/reaper-restore.sh <写しの置き場>（head.txt のある完成した置き場）" >&2
  exit 2
fi
ARCH="$(cd "${ARCH}" && pwd)"

# 作業場所に向ける git の守り（ADR-1039）。読めなければ止まる
if ! source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/git-safe.sh" 2>/dev/null || [ -z "${GIT_SAFE_ARGS+x}" ]; then
  echo "[restore] git の守りを読めない（scripts/git-safe.sh）。何もせず終了します。" >&2
  exit 1
fi

# head.txt（key=value）
_hv() { sed -n "s/^$1=//p" "${ARCH}/head.txt" | head -1; }
BRANCH="$(_hv branch)"
SHA="$(_hv sha)"
ROOM="$(_hv path)"
if [ -z "${SHA}" ] || [ -z "${ROOM}" ]; then
  echo "[restore] head.txt に sha か path が無い。止まります。" >&2
  exit 1
fi

# 本店 = <git-common-dir>/reaper-archive/ の親の親（.git の親）
COMMON="$(dirname "${ARCH}")"; COMMON="$(dirname "${COMMON}")"
if [ "$(basename "$(dirname "${ARCH}")")" != "reaper-archive" ] || [ "$(basename "${COMMON}")" != ".git" ]; then
  echo "[restore] 写しの置き場が <本店>/.git/reaper-archive/ の下にない。止まります。" >&2
  exit 1
fi
MAIN="$(dirname "${COMMON}")"
if ! git_safe_main_ok "${MAIN}"; then
  echo "[restore] 本店の git の繋がりを確かめられない（${GIT_SAFE_LINK_REASON:-不明}）。止まります。" >&2
  exit 1
fi

# 元のパスに何かあれば止まる
if [ -e "${ROOM}" ] || [ -L "${ROOM}" ]; then
  echo "[restore] 元のパスに既に何かある: ${ROOM}。止まります（何も変えていません）。" >&2
  exit 1
fi

G=(git "${GIT_SAFE_ARGS[@]}")


# 1. bundle のコミットを本店に入れる
if [ -s "${ARCH}/unpushed.bundle" ]; then
  if ! "${G[@]}" -C "${MAIN}" fetch "${ARCH}/unpushed.bundle" HEAD >/dev/null 2>&1; then
    echo "[restore] bundle からコミットを取り込めない。止まります。" >&2
    exit 1
  fi
fi

if [ -n "${BRANCH}" ] && [ "${BRANCH}" != "(detached)" ]; then
  TIP="$("${G[@]}" -C "${MAIN}" rev-parse -q --verify "refs/heads/${BRANCH}" 2>/dev/null || true)"
  if [ "${TIP}" != "${SHA}" ]; then
    echo "[restore] ブランチ ${BRANCH} の指す先（${TIP:-無い}）が写しの sha（${SHA}）と違う。止めて人に回します（部屋は作っていません）。" >&2
    exit 1
  fi
fi

# 2. 部屋を作る
if ! "${G[@]}" -C "${MAIN}" worktree add --detach "${ROOM}" "${SHA}" >/dev/null 2>&1; then
  echo "[restore] git worktree add に失敗: ${ROOM}（sha ${SHA}）。止まります。" >&2
  exit 1
fi

# 3. ブランチへ
if [ -n "${BRANCH}" ] && [ "${BRANCH}" != "(detached)" ]; then
  if ! "${G[@]}" -C "${ROOM}" switch "${BRANCH}" >/dev/null 2>&1; then
    echo "[restore] git switch ${BRANCH} に失敗（別の部屋が使っている等）。部屋は detached のまま ${ROOM} に作りました。人が確認してください。" >&2
    exit 1
  fi
fi

# 4. 変更を戻す（ステージ済み → 未ステージ）
if [ -s "${ARCH}/staged.patch" ]; then
  "${G[@]}" -C "${ROOM}" apply --binary --index "${ARCH}/staged.patch" >/dev/null 2>&1 \
    || { echo "[restore] staged.patch を当てられない。止まります（${ROOM}）。" >&2; exit 1; }
fi
if [ -s "${ARCH}/unstaged.patch" ]; then
  "${G[@]}" -C "${ROOM}" apply --binary "${ARCH}/unstaged.patch" >/dev/null 2>&1 \
    || { echo "[restore] unstaged.patch を当てられない。止まります（${ROOM}）。" >&2; exit 1; }
fi

# 5. 新しいファイル・無視ファイル
for T in untracked.tar ignored.tar; do
  if [ -s "${ARCH}/${T}" ]; then
    tar -xf "${ARCH}/${T}" -C "${ROOM}" 2>/dev/null \
      || { echo "[restore] ${T} を取り出せない。止まります（${ROOM}）。" >&2; exit 1; }
  fi
done

echo "[restore] 戻しました: ${ROOM}（ブランチ: ${BRANCH:-なし}、sha ${SHA}）"
exit 0
