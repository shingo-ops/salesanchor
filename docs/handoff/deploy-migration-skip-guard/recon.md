# recon: デプロイが途中で止まると次のデプロイが DB 更新を飛ばす件（P6）

基準: origin/main 0f2d5bff2（2026-10-17 fetch 後）。生出力: `~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p6_deploy_skip/recon_raw/`

## 既存 ADR の検索
- docs/adr/ と docs/adr/FEATURE-INDEX.md を検索（結果: `~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p6_deploy_skip/recon_raw/item6_adr_grep.txt`）。
- 関係する ADR: docs/adr/ADR-082-deploy-skip-migrations-on-frontend-only.md:48（「判定不能・差分取得失敗時は安全側（実行）に倒れる」）、docs/adr/ADR-092-deploy-concurrency-control.md:33-39,78（cancel-in-progress:false で直列化）、ADR-115（ヘルスチェック失敗で PREV_SHA に戻す）、ADR-1005（migration の一度きり台帳）。
- 関係する handoff: docs/handoff/predeploy-backup-db-filter/（db_migrations フィルタの由来）。

## 観測事実
1. 判定は push 直前の commit との差分だけ: .github/workflows/deploy.yml:33-59 の dorny/paths-filter@v4 は base 未指定。公式 README「If it references the same branch it was pushed to, changes are detected against the most recent commit before the push.」（https://github.com/dorny/paths-filter README、2026-10-17 取得）。
2. この判定を使う箇所は5つ: .github/workflows/deploy.yml:178（Pre-deploy DB backup・db_migrations）、:447（Recreate nginx・nginx）、:528（Run database migrations・migrations）、:549（smoke・migrations）、:629（Finalize のメッセージ）。
3. サーバー側の記録は .deploy_prev_sha だけ（.github/workflows/deploy.yml:228-230、git pull 前の HEAD）。「どの SHA まで migration を適用したか」の記録は無い（`~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p6_deploy_skip/recon_raw/item4_server.txt`）。
4. 同じ concurrency グループ（.github/workflows/deploy.yml:13-15）で待っている run は、新しい run に置き換えられて cancelled になる（GitHub 公式 concurrency 文書）。
5. 実例 2026-10-17: run 39009743471（08367dd13、migration 2件）が cancelled → 次の run 39009815224 は migrations とバックアップを skip（`~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p6_deploy_skip/recon_raw/run_39009815224.log`）。39009743471 の rerun で解消。
6. 直近1000 run で同じ型（migration 系を含む run が完了せず、次の成功 run が migrations を skip）は7件: 35575043609, 35577152930, 35582678553, 35597315780, 35613468344, 36007632918, 39009743471（失敗6・cancelled 1、`~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p6_deploy_skip/recon_raw/item5_strict.txt`）。backend/** 等だけの同型は6件。
7. 所要時間: migrations 71〜459秒、バックアップ 86〜90秒（`~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p6_deploy_skip/recon_raw/item7_durations.txt`）。
8. deploy.yml に permissions の指定は無い（`grep -n permissions .github/workflows/deploy.yml` 0件）。既存で secrets.PIPELINE_PAT を GH_TOKEN に使う段がある（.github/workflows/deploy.yml:860-861）。

## 未確認
- paths-filter の base に commit SHA を渡したとき、push イベントで「その SHA との差分」になるか。README は「any other event」としか書いていない → この方式は採らない（design.md の案A）。
- 既定の GITHUB_TOKEN で Actions の run 一覧が読めるか（リポジトリ設定次第）→ 読めなければ安全側に倒す設計にし、実装後の試験で確かめる（design.md K3）。
