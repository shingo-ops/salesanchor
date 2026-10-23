# recon: pr-ownership-rest

## KGI
クラウド実行の git push が pre-push で止まらず、マージ済みブランチだけが止まる。

## 現在地（根拠）
- scripts/validate-pr-ownership.sh:138（変更前）`gh pr list --head ... --state merged --json state` は GraphQL。
- クラウドでは `HTTP 403: GitHub GraphQL is not available from Claude Code sessions; use the REST API`。2>/dev/null で握り潰され、無言で止まった。記録: /tmp/CC報告ファイル/cloud-trial-20261022/run-summary.txt
- 同ファイルの gh 呼び出しは138行目の1か所のみ（grep 'gh ' で確認）。
- 既存ADR検索: docs/adr/ADR-074-worktree-agent-enforcement.md（当スクリプトの出典。判定の意味は変えない）。
