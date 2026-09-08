## 4. worktree・ブランチ

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| `git worktree add` で直接作る → pre-commit が規約外の場所からの commit を拒否 | `bash scripts/new-worktree.sh <ブランチ名>`（`~/worktrees/salesanchor/` 配下・active-work.md に自動登録） | CARD-PMG-FIX11-09・CV-44（未検証） |
| 別セッションの worktree に触る | `worktree-access-guard.sh` が「別セッションのworktreeへのアクセスは禁止」でブロック | 実測 |
| ブランチ名が `release/*` `hotfix/*` 以外で main 向け PR | `gh-pr-create-safe.sh` が**ハードブロック**（§5） | 実測 |
| 上流が origin/main を指す → `git push` 拒否 | `git push -u origin HEAD` | CV-43・MERGE-FIX-05（未検証） |
| 既存ブランチに `-b` で再作成 → already exists | 既存なら `-b` 無しで `git worktree add <path> <branch>` | CARD-BENCH-PR-02 |
| 正本に他便の先約 → 停止 | 触る前に `git grep -n "<ファイル名>" -- .claude-pipeline/` で先約確認（§6.5） | W-01・CARD-DP-RECON-03b |
| ローカル main に未解決コンフリクト → checkout 拒否 | ローカル main を起点にしない。origin/main から worktree | CARD-BENCH-RECON-02 |
| ディスク残量 → ENOSPC で worktree 作成が中途半端に失敗 | 手順0で `df -h .`。2Gi 未満なら止める | CARD-BENCH-PR-01 |
| マージ後 `cleanup-worktree.sh` が worktree とブランチを自動削除する | 削除される前提で、必要なファイルは先に退避 | 実測（gh-pr-merge-safe.sh 末尾） |

