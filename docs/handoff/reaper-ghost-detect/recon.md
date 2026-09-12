# recon: reaper-ghost-detect

調査日: 2026-09-05
調査者: Hikky-dev (REAPER-02)

---

## 0. 調査起点の事象

2026-09-05 に worktree が 90本超に膨張。reaper は `git worktree list` 経由でしか
worktree を把握しないため、git 登録が外れた実体ディレクトリ（ゴースト）を
永久に検出・削除できなかった。

実測: ゴーストが 5件・計 830MB 発生していた（前セッション DISK-07 調査時）。

---

## 1. ゴーストの発生経路（事実）

`scripts/reaper-worktree.sh:94-126`（本番モード）は
`git worktree list --porcelain` の出力を走査する。

→ `git worktree remove --force` または `git worktree prune` で
  git の登録が外れた後も実体ディレクトリが残る場合、
  reaper の走査リストに現れず、永久に検出されない。

発生パターン:
- `git worktree remove` が失敗して git 登録だけ消えた
- `git worktree prune` で参照だけ消えたがディレクトリ残存
- 手動で mkdir した作業用ディレクトリが混入

---

## 2. 既存コードの走査範囲（事実）

`scripts/reaper-worktree.sh:94-126`:
```bash
# 本番モード: git worktree list --porcelain で全登録 worktree を対象にする
done < <(git -C "${MAIN_REPO_ROOT}" worktree list --porcelain 2>/dev/null; echo "worktree __END__")
```

→ ファイルシステム上の `~/worktrees/salesanchor/` を直接走査する部分は**不在**。

---

## 3. worktree 親ディレクトリの変数（事実）

`scripts/new-worktree.sh:62`:
```bash
WORKTREE_DIR="${HOME}/worktrees/${REPO_NAME}/${BRANCH_SAFE}"
```

→ worktree の格納先は `${HOME}/worktrees/$(basename "${MAIN_REPO_ROOT}")`。
  `MAIN_REPO_ROOT` は `reaper-worktree.sh` 内で定義済み（:40-45）。
  ハードコードせず `${HOME}/worktrees/$(basename "${MAIN_REPO_ROOT}")` で導出できる。

---

## 4. 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `scripts/reaper-worktree.sh` | ゴースト検出ブロック追加（サマリ後・削除前） |
| `docs/handoff/reaper-ghost-detect/recon.md` | 本ファイル |
| `docs/handoff/reaper-ghost-detect/design.md` | 設計ファイル |
