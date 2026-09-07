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

## 事実7: 現在唯一機能している削除経路（2026-07-28 実測）

scripts/new-worktree.sh:67 — bash "${REAPER_SCRIPT}" --execute 2>/dev/null || true
本店版・origin/main 版とも同一（65・67・82行）。作業台を作るたびに実削除が走る。
実フォルダ数の推移: 96（未明）→ 95（04時台）→ 94（16:14）。

## 事実8: 常駐・定期の別経路は関与していない

launchctl list: jp.salesanchor.reaper-onlogin は登録済みだが PID なし。
~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist は RunAtLoad のみ・
Interval キーなし・KeepAlive false。
ログ /Users/tanizawashingo/Library/Logs/reaper-onlogin.log の最終更新は 2026-07-24 11:37。
crontab -l は no crontab（exit 1）。

## 事実9: ロック残骸による全停止（実害）

/tmp/reaper-worktree.lock.d が 2026-07-28 16:14:39 に作成され、17:04 時点で
プロセス不在・中身空のまま残存（約50分）。
scripts/reaper-worktree.sh:31-35 により、ロック在中の掃除機は
「another instance is running; skip.」で無言終了する。
この間に作業台は 94 から 95 に増えたが、削除は発生しなかった。
GO #reaper-lock-release により rmdir で解除（rmdir_exit=0）。

## 事実10: 手元経路での実削除が成功（K5 実測・2026-07-28 21:37 JST）

release-deal-removal-serviceD（対策版・claude-pipeline 出現5）から
環境変数なしで bash scripts/reaper-worktree.sh --execute を実行。

dry-run 検算: 対象90件／IN_PROGRESS・未マージ35件／未保存24件／未マージ7件／削除対象24件。
削除候補24件に main・develop の完全一致は 0 件（grep -cx で実測）。

実行結果: フォルダ削除 24件／ブランチ削除 24件／フォルダ削除スキップ 0件。
実フォルダ 95 から 72、登録簿 100 から 76。
実行後 main・develop は手元・リモートとも残存。ロック残存なし。

未確定: フォルダ削除24件に対し実フォルダは23件減。差1件の原因は未特定。

## 事実11: 実行方式による差

前面実行はログ 3,955 バイトで完走（2回）。
背景実行（nohup）はログ 0 バイトで終了しロックを残した（1回）。原因は未特定。

## 構造（事実7〜11の追加分）

Actions 経由（走査=本店・削除=_work）では削除0件、手元経路（走査・削除とも本店）では
24件成功した。事実3の構造が実測で裏づけられた。
K5（即時掃除が実際に消す）は手元経路で達成。Actions 経路は未達。
