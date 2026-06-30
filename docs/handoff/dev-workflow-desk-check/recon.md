# recon — dev-workflow-desk-check

## 目的
worktree並行開発で「本店(MAINリポジトリ)への誤作業」「古い起点からの分岐」を始業時に検知する補助ツールの必要性を、実コードで裏付ける。

## 確認した事実(file:line)
- `scripts/dev/executor-preflight.sh:1-87` … ネット到達/gh認証(shingo-cc)/長命ブランチ存在は確認するが、「現在ディレクトリが本店か」「現在ブランチ」「起点がorigin/mainから何コミット遅れか」は未チェック。
  - grep(branch|worktree|origin/main|merge-base|show-current) のヒットは `:72,75,77`(長命ブランチ存在確認)のみで、場所/起点の確認ロジックは不在。
- 本店パスは `/Users/tanizawashingo/salesanchor`。作業用worktreeは `/Users/tanizawashingo/worktrees/salesanchor/*` 配下に分離(git worktree list 実測)。両者は物理的に別ディレクトリ。
- gitフック: `frontend/.husky` に pre-commit / pre-push が設定(core.hooksPath=frontend/.husky)。commit時にADR-067チェック・CLAUDE.mdサイズチェック・lint-stagedが走ることを実測(KPI-4前半のダミーcommitで確認)。
- `.pre-commit-config.yaml` は不在(フレームワーク版pre-commitは未使用)。

## 含意
始業時に「場所(本店か)・起点(最新mainからの遅れ)」を確認する仕組みが既存preflightに欠けている。これが過去の混線(本店で別ブランチに誤コミット/古い起点からの分岐)の温床。新規の軽量チェックで補う妥当性を確認。
