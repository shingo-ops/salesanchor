# recon — 台帳DONE化の自動化（main）

> この文書は何か（専門用語なしの1行）:
> マージが終わったあとの作業記録の更新を機械にやらせる前に、
> いまの仕組みがどうなっているかを実際に見て記録したもの。

対象ADR: ADR-114
親テーマ: docs/specs/ledger-guard/README.md

## 実測（2026-09-02）

### 既存ワークフローが main では発火しない

.github/workflows/active-work-auto-done.yml:9 のトリガーが develop 限定である。
main へのマージでは発火しない。

同ファイル:42 の更新先が本体の台帳ファイル固定であり、
1ブランチ1ファイルの単票は対象外である。

checkout の ref も push 先も develop になっている。
ADR-114 の時代に作られたまま、ledger-guard 第2弾の書き先分割に追随していない。

### 別経路の自動化は commit しない

scripts/cleanup-worktree.sh:52 がマージ後に台帳を DONE 化する。
ただし commit も push もしないため、本店に残るだけである。
その結果、未追跡の台帳が 222 件溜まっていた（2026-09-02 実測）。

### 窓口スクリプトは Actions からも使える

scripts/ledger-update.sh:12 と scripts/ledger-update.sh:13 で、
環境変数により対象の場所を差し替えられる。

scripts/ledger-update.sh:18 で単票を優先し、
無ければ本体を見る仕組みになっている。

### 関所は台帳のみの変更を素通しする

scripts/check-process-artifacts.js:43 の分類定義に、
拡張子が md のファイルを書類とみなすパターンがある。
台帳ファイルは拡張子が md のため書類に分類される。

scripts/check-process-artifacts.js:683 で、書類のみの変更かつ正本を含まない場合に
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

.github/workflows/brand-asset-monitor.yml:220 に PR 自動作成の使用例がある。
ただしそちらは既定のトークンを使っている。

## 本便で追加する箇所

.github/workflows/ledger-auto-done-main.yml を新規作成する。
既存の .github/workflows/active-work-auto-done.yml:9 は変更しない。
