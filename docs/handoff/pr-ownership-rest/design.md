# design: pr-ownership-rest

参照: recon.md / ADR-074（docs/adr/ADR-074-worktree-agent-enforcement.md）

## How
scripts/validate-pr-ownership.sh のチェック4を `gh api repos/<origin>/pulls?head=<owner>:<branch>&state=closed` に置換し、merged_at 非nullの件数で判定。失敗時は理由1行を stderr に出し exit 1。

## 受け入れ基準
|基準|検証方法|
|---|---|
|マージ済みブランチで止まる|release/loading-mold-pages-2 → rc=1|
|未作成ブランチで通る|新規名 → rc=0|
|問い合わせ失敗で理由つき rc=1|GH_HOST=invalid.example|
|文法|bash -n|

## 外部事例
GitHub REST API「List pull requests」(head=user:ref-name, state=closed) の公式仕様。GraphQL不可環境の標準的な代替。

## 戻し方
このPRをrevert。
