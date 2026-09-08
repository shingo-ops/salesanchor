## 6. マージ

**gh-pr-merge-safe.sh の実装（実測・全文読了）**

- PR番号は `${WORKTREE_DIR}/.pr-number` から読む（`tr -d '[:space:]'` で空白除去）。**引数はすべて `gh pr merge` にそのまま渡る**
- チェック1: `.pr-number` が無い/空 → exit 1
- チェック2: `active-work.md` の PR# 列（6列目）と不一致 → exit 1
- リトライ: `not up to date` なら追従（`git merge origin/main` → `push` → `gh pr checks --watch --required`）を**最大2回**
- `rule violations|required status check|is not mergeable` → RULE_WAIT（30秒×3回、同一 HEAD で再マージ）
- コンフリクトは**自動解決しない**（即停止）
- 未知の拒否は安全のため停止
- 成功後、`cleanup-worktree.sh` が worktree とブランチを自動削除

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| `gh-pr-merge-safe.sh 3323`（番号を渡す）→ `gh pr merge 3323 3323` で失敗 | `bash scripts/gh-pr-merge-safe.sh --merge` | 実測・CARD-BENCH-MERGE-01 |
| 引数なし → 非対話でマージ方式が決まらず中断 | `--merge` 必須（このリポジトリは merge commit が正。CLAUDE.md:50 の記述は実態と逆） | CG-07b・実測 |
| `.pr-number` が無い・別の値・`cd` 失敗で本体リポジトリに書かれた | `register-pr.sh` が両方（`.pr-number` と台帳）を更新する。手で書かない | CARD-PRNUM-RECON-01 |
| BEHIND で拒否 | スクリプトが追従する。`--admin`/`--auto` は素通りに当たり禁止 | 実測・CI-10/20/30/31 |
| マージ完了を手元ログで判断 | GitHub 側（`mergedAt`/`mergeCommit`）で実測 | design-partner.md §6.5 |
| GO が実行役に届いていない | GO の文言は PO が実行役のウィンドウにも貼る。カードに「GO #番号 受領済み」を書く | CI-28（未検証） |

| BEHIND のままマージを撃つ → 追従が走り、追従後の CI 約2分を待ちきれず STOP。追従リトライは2回まで | mergeStateStatus=CLEAN を確認してから撃つ | PR #3355 で2回・2026-09-07 実測 |
| gh-pr-merge-safe.sh --merge はマージ成功後に cleanup-worktree.sh を呼び、ローカルの worktree とブランチのみ削除する。リモートブランチは残る | マージ後の手順を同一カードに置くなら cd 先をリポジトリ直下にする。リモートを消すには別の worktree から git push origin --delete を実行し、git ls-remote --heads origin が空であることで確認する | 実測3件・2026-09-07 と 09-08 |
| BLOCKED と BEHIND を混同する | BLOCKED は必須チェックがまだ報告されていない状態で、待てばよい。BEHIND は main に追いついていない状態で、追従が要る。pytest は約2分かかるため追従直後は BLOCKED になる | 2026-09-08 実測 |
| CI の確認手段 | PO が画面で見る場合と、カードで gh pr checks を叩く場合がある。PO が見ているとは限らないので、設計パートナーは確認カードを用意しておく。どちらで確認したかをマージカードの背景に書く | 2026-09-08 PO 判断 |
