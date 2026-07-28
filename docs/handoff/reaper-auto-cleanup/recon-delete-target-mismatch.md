# recon: reaper の走査先と削除先の不一致（2026-07-28）

> この文書は何か（専門用語なしの1行）:
> 掃除機が対象を正しく選んだのに1件も消せない理由を、実際に調べた事実だけで記録したもの。

親（あるべき姿）: ../../specs/reaper-auto-cleanup/README.md

実測日: 2026-07-28
実測時 origin/main SHA: 8dfd80a0667ace07b820dd07e7d59e3516a28b9e

## 事実1: 台帳除外の適用時点

対策コミット 9e462249 は origin/main に合流済み（git merge-base --is-ancestor 9e462249 8dfd80a0 = exit 0）。
定期run 30216232301（2026-07-26T19:08:45Z）は旧 main 1d9ae8cc で実行され、
git merge-base --is-ancestor 9e462249 1d9ae8cc = exit 1 のため対策未適用だった。

## 事実2: 対策適用後の手動実行の結果

run 30290656834（event=workflow_dispatch・2026-07-27T17:45:18Z・conclusion=success）の集計:

| 区分 | 修正前 run 30216232301 | 修正後 run 30290656834 |
|---|---|---|
| 対象 worktree 数 | 88 | 89 |
| IN_PROGRESS/REVIEW 未マージ | 23 | 27 |
| 未保存あり | 50 | 26 |
| 未マージ | 12 | 18 |
| 削除対象（安全条件クリア） | 3 | 18 |
| 実削除 | 0 | 0 |

台帳除外は機能した（未保存 50 → 26・削除対象 3 → 18）。しかし実削除は 0 件のまま。
削除対象18件はすべて「フォルダ削除スキップ（既に存在しないか登録解除済み）」
「ブランチ削除スキップ」を出力した。

## 事実3: 走査先と削除先が異なる

scripts/reaper-worktree.sh:56-58 — REAPER_WORKTREES_DIR 指定ありは
「テスト用オーバーライド」と明記され、単一ディレクトリ走査になる。
scripts/reaper-worktree.sh:63-75 — 走査対象は REAPER_WORKTREES_DIR 配下。
scripts/reaper-worktree.sh:40-45 — MAIN_REPO_ROOT は git rev-parse --git-common-dir
から算出される（実行時のカレント基準）。
scripts/reaper-worktree.sh:297 — git -C "${MAIN_REPO_ROOT}" worktree remove --force
scripts/reaper-worktree.sh:302 — git -C "${MAIN_REPO_ROOT}" branch -D
scripts/reaper-worktree.sh:318 — git -C "${MAIN_REPO_ROOT}" worktree prune

.github/workflows/reaper-schedule.yml は env に
REAPER_WORKTREES_DIR: /Users/tanizawashingo/worktrees/salesanchor を注入する。
走査先は本店、削除先は実行時カレントで、両者が一致しない。

## 事実4: Actions 実行時のカレント

run 30290656834 のログに
/Users/tanizawashingo/actions-runner-shingo/_work/salesanchor/salesanchor
が出現（同ログ内 _work の出現7件）。

## 事実5: 削除できなかった対象は本店に実在する

2026-07-28 実測:

- ls -d /Users/tanizawashingo/worktrees/salesanchor/release-field-size-leads → 実在
- ls -d /Users/tanizawashingo/worktrees/salesanchor/release-rev5-tidy → 実在
- git -C /Users/tanizawashingo/salesanchor worktree list | grep -c field-size-leads → 1
- git -C /Users/tanizawashingo/salesanchor worktree list | grep -c rev5-tidy → 1

Actions 側の「既に存在しないか登録解除済み」は、本店に対する判定ではない。

## 事実6: 基幹ブランチの残存（安全性）

実行後の実測: git branch --list main develop で main・develop とも残存。
git ls-remote --heads origin main = 8dfd80a0 / origin develop = 1b9a93b7 で
リモートにも残存。実行前後の作業台数は git worktree list=101・実フォルダ=96 で不変。

## 未確定（推測で埋めないこと）

実行時の MAIN_REPO_ROOT の値そのものはスクリプトが出力しないため未取得。
事実4のカレントから算出される値であることは、事実3の40-45行の実装から導かれるが、
実値の直接観測はしていない。

## 構造（事実1〜6から言えること）

対策適用後も作業台が減らないのは、保護判定の問題ではなく削除経路の問題である。
design.md のかたまり①（REAPER_WORKTREES_DIR 注入）は走査先のみを本店に向けており、
削除先は変更していない。design.md の弊害欄に本項目の記載はない。
