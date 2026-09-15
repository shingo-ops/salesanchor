分類: 6-1
出所: （2026-09-07 PR #3332）

# Note_JA 調査〜設計第1稿マージ便の教訓（3件）

## 1. --delete-branch は worktree がチェックアウト中のブランチを消せない（分類 6-1）

PR #3332 を `gh pr merge --merge --delete-branch` でマージしたところ、マージ自体は成功
（state=MERGED / mergeCommit f70daf7f）したが、`failed to delete local branch ... checked out at
/Users/.../worktrees/salesanchor/release-tcg-note-master-design` が出て、リモートブランチも
残った（`git ls-remote --heads origin release/tcg-note-master-design` が 3f880f26 を返す）。
報告は同じ出力の直後に「(空 = リモートブランチ削除済み)」と注記しており、データと注記が食い違っていた。

対策: マージカードで --delete-branch を使うときは「その worktree が同ブランチをチェックアウト中なら
削除は失敗する」を前提に置き、削除の完了判定は必ず `git ls-remote --heads origin <branch>` の
空で行う。gh の出力文言や実行者の注記を完了の根拠にしない。

## 2. マージ済み push 拒否ガードと worktree 内削除ルールの組み合わせで、削除だけが通れない（分類 6-1）

上記の残存ブランチを worktree 内から `git push origin --delete` で消そうとしたところ、pre-push ガードが
「push を中断しました: このブランチのPRはすでにマージ済みです」で拒否した。ガードは削除の push と
追加コミットの push を区別していない。一方、リポジトリ直下からの `push --delete` は worktree ガードが
拒否する（design-partner.md §6 既知）。結果、正規の削除経路がマージ時の --delete-branch だけになる。
GitHub UI と `gh api` の ref delete は CLAUDE.md が禁止しているため、迂回はしない。

対策: マージ済みブランチの削除は、マージと同一手順の中で（worktree を先に片付けたうえで）行う。
事後に消せなかった場合は迂回せず残存を受け入れ、マージ済みかつ origin/main の祖先であることを
`git merge-base --is-ancestor` で実測して報告する。ガードの組み合わせの是正はガード層テーマへ。

## 3. コマンドの exit をパイプ越しに取らない（分類 6-1）

`./scripts/dev/executor-preflight.sh` を tee 等のパイプで受けた便で `exit:` が空になり、実装役が
「exit 1」と読んで一度 STOP した（再実行して exit 0 を確認し続行）。同型で、`git push origin --delete`
が `error: failed to push some refs` を出しているのに `delete exit: 0` と記録された便もあった。

対策: 判定に使う exit は、コマンドを単独行で実行した直後に別行で `echo "exit: $?"` として取る。
パイプ・コマンド置換の中で `$?` を読まない。カード側でこの書き方を明示する。
