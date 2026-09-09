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

| new-worktree.sh の出力を head や tail に通す → 完了行が遅れて届き、次手順の ls が作成前に走って無いと誤判定する | 出力はパイプに通さない。判定は ls -1d と git worktree list の両方で行う | 別セッション実測・同型2回 |
| new-worktree.sh は reaper が全 worktree を走査してから作成に入る（2026-09-08 実測で64件） | 出力の見た目で成否を決めない。次手順で実在を確かめる | 実測 |
| new-worktree.sh はディレクトリが既に在ると fatal で失敗する。ブランチ作成は成功した後なので、ブランチだけが残る | 作る前に ls -1d で実在を確かめる | 別セッション報告・本セッション未検証 |
| 追加の push で git push だけを使う | PR 作成時に -u を付けても、後続の push で忘れると上流が main を指して拒否される。毎回 git push -u origin HEAD を使う | 2026-09-08 実測・同一ブランチで両方 |
| new-worktree.sh のオプション | CLAUDE.md と本ファイルで --claude の要否が食い違っている。推測でどちらかを採らない。正本は CLAUDE.md。本セッションでは --claude なしで5回成功している | 2026-09-08 別セッション報告 |
| 新規 worktree の作成確認を git worktree list の末尾で行う → 一覧は名前順で、新しい行は中ほどに入るため末尾に現れず確認できない | 作成した名前を名指しして ls -1d フルパス で確かめる | 2026-09-09 実測・CARD-PMG-WT-01 |
