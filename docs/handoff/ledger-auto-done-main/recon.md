# recon — 台帳DONE化の自動化（main）

> この文書は何か（専門用語なしの1行）:
> マージが終わったあとの作業記録の更新を機械にやらせる前に、
> いまの仕組みがどうなっているかを実際に見て記録したもの。

対象ADR: ADR-114
親テーマ: docs/specs/ledger-guard/README.md

## 実測（2026-09-02）

### 既存ワークフローが機能していない

対象ファイル: .github/workflows/active-work-auto-done.yml

- トリガーが develop ブランチ限定。main マージでは発火しない。
- 更新先が .claude-pipeline/active-work.md（本体）固定。
  .claude-pipeline/active-work.d/ の単票は対象外。
- checkout の ref も push 先も develop。
- ADR-114 の時代に作られたまま、ledger-guard 第2弾の書き先分割に追随していない。

### 別経路の自動化は commit しない

対象ファイル: scripts/cleanup-worktree.sh

マージ後に ledger-update.sh を呼んで DONE 化する。ただし commit も push もしない。
その結果、本店に未追跡の台帳が 222 件溜まっていた（2026-09-02 実測）。

### 窓口スクリプトは Actions からも使える

対象ファイル: scripts/ledger-update.sh

12行目と13行目で、環境変数 ACTIVE_WORK_FILE と ACTIVE_WORK_DIR により
対象の場所を差し替えられる。

18行目で active-work.d 配下の単票を優先し、
無ければ ledger-lookup.sh 経由で本体を見る。

### 関所は台帳のみの変更を素通しする

対象ファイル: scripts/check-process-artifacts.js

43行目の DOCS_PATTERNS に、拡張子が md のファイルを docs とみなすパターンがある。
台帳ファイルは拡張子が md のため docs に分類される。

683行目で、書類のみの変更かつ正本を含まない場合に
「書類のみの変更 — 自動スキップ（pass）」を出力して終了する。

つまり台帳のみのPRは GO記録の検証に到達しない。

### main は直接 push できない

ruleset 15777895（main branch protection）の実測値:

- You can bypass: never
- bypass_actors は空
- rules に pull_request が含まれる
- required_status_checks は12件
- strict_required_status_checks_policy は true

したがって GitHub Actions も PR を経由する必要がある。

### PR自動作成の前例がある

対象ファイル: .github/workflows/brand-asset-monitor.yml

220行目に gh pr create の使用例がある。
ただしそちらは GITHUB_TOKEN を使っている。

## 本便で追加する箇所

.github/workflows/ledger-auto-done-main.yml を新規作成する。
既存の .github/workflows/active-work-auto-done.yml は変更しない。
