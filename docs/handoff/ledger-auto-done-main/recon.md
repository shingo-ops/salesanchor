# recon — 台帳DONE化の自動化（main）

> この文書は何か（専門用語なしの1行）:
> マージが終わったあとの作業記録の更新を機械にやらせる前に、
> いまの仕組みがどうなっているかを実際に見て記録したもの。

対象ADR: ADR-114
親テーマ: docs/specs/ledger-guard/README.md

## 実測（2026-09-02）

### 既存ワークフローが機能していない

`.github/workflows/active-work-auto-done.yml`

- トリガーが `branches: [develop]` のみ。main マージでは発火しない。
- 更新先が `.claude-pipeline/active-work.md`（本体）固定。
  `.claude-pipeline/active-work.d/` の単票は対象外。
- checkout の `ref: develop`、push 先も develop。
- ADR-114 の時代に作られたまま、ledger-guard 第2弾の書き先分割に追随していない。

### 別経路の自動化は commit しない

`scripts/cleanup-worktree.sh` がマージ後に `ledger-update.sh --status DONE` を
実行する。ただし commit / push はしない。
その結果、本店に未追跡の台帳が 222 件溜まっていた（2026-09-02 実測）。

### 窓口スクリプトは Actions からも使える

`scripts/ledger-update.sh:12-13`

- `LEDGER_FILE="${ACTIVE_WORK_FILE:-...}"`
- `LEDGER_DIR="${ACTIVE_WORK_DIR:-...}"`

環境変数で対象を差し替えられる。

`scripts/ledger-update.sh:18` で `.d/` の単票を優先し、
無ければ `ledger-lookup.sh` 経由で本体を見る。

### 関所は台帳のみの変更を素通しする

`scripts/check-process-artifacts.js:43` の `DOCS_PATTERNS` に
`.md` 拡張子のパターンがある。台帳ファイルは `.md` のため docs に分類される。

`scripts/check-process-artifacts.js:683`

- `if (hasDocsOnly && !hasCanonicalDoc(changedFiles))` で
  「書類のみの変更 — 自動スキップ（pass）」となり `process.exit(0)`。

つまり台帳のみのPRは GO記録の検証に到達しない。

### main は直接 push できない

ruleset 15777895（main branch protection）

- `You can bypass: never`
- `bypass_actors` は空
- rules に `pull_request` が含まれる
- `required_status_checks` は12件、`strict_required_status_checks_policy: true`

したがって Actions も PR を経由する必要がある。

### PR自動作成の前例がある

`.github/workflows/brand-asset-monitor.yml:220` に `gh pr create` の使用例がある。
ただしそちらは `secrets.GITHUB_TOKEN` を使っている。

## 本便で追加する箇所

`.github/workflows/ledger-auto-done-main.yml` を新規作成する。
既存の `active-work-auto-done.yml` は変更しない。
