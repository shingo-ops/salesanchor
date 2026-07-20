# design（③掃除係の職務拡張＋④死活通知）

この文書は何か(専門用語なしの1行): サーバーのゴミを自動で掃除し、掃除が止まったらDiscordに知らせが来る仕組みの設計図。

親: [README.md](./README.md) / [あるべき姿](./ideal-state.md) / [KGI](./kgi.md)

## 1. recon(実測済み・2026-07-20)
- 掃除係の現物: scripts/f2-cleanup.sh(サーバー実物とorigin/main正本はdiffでIDENTICAL実測)。職務は「古い停止コンテナ＋古いbuild cacheのみ。volume/image/稼働中に触れない」。cron週1(日曜4時)稼働中。
- コンテナ日誌: 全サービスにmax-size 5〜20MB設定済み(docker-compose.yml内logging:実測10ブロック)。追加工事不要。
- OS日誌(journal): prod1=2.1GB・上限なし。上限設定は/etc編集=sudo必須(両VPSともsudo不可実測)。本設計の対象外(別便)。
- 監視サーバー(prod2)のPrometheusは prod1 の node_exporter を job="node-exporter", instance="app-vps" で毎日読取中(up=1 実測)。
- prod1→prod2 pushgateway(9091)は不通(UNREACHABLE実測)。受信箱方式は不採用。
- node_exporter定義: docker-compose.exporters.yml:4-25。textfile collector未設定(command 4項目のみ実測)。
- prod2のcrontabは空(掃除係ゼロ)。alertmanagerはDiscord webhook設定済み稼働中。

## 2. design(実現方法)
### ③掃除係の職務拡張(f2-cleanup.sh改修)
1. 旧型イメージ削除(新設): (a)全イメージから「稼働中コンテナが使用中」「各リポジトリの最新1世代」を除外した削除候補名簿を作成しログに全行記録 (b)名簿を1件ずつ docker rmi <ID>(force不使用)で削除・pruneは使わない (c)削除結果(成功/失敗)を1件ずつログ記録。
2. 既存職務(停止コンテナ・build cache)は変更しない。
3. 完了記帳(新設): 全職務成功時のみ、textfileディレクトリに f2_cleanup_last_success_timestamp <epoch秒> を書き出す(node_exporter textfile形式)。
### ④死活通知(黒板方式・dead-man's-switch)
4. docker-compose.exporters.yml の node-exporter に --collector.textfile.directory=/var/lib/node_exporter/textfile を追加し、ホスト側ディレクトリをread-onlyでマウント。
5. prod2の alert_rules.yml に追加: time() - f2_cleanup_last_success_timestamp{instance="app-vps"} > 8日 で警報(severity付与・alertmanager経由Discord)。メトリクス不在(absent)も同時に警報対象とする(黒板自体が消えた場合の検出)。
6. prod2にも同型掃除係を配置(cron週1・黒板つき・警報ルールはinstance="mgmt-vps"で1本追加)。
### 実行順(安全装置・この順以外で進めない)
設計書マージ → 改修PR(scripts変更=GO必須) → 手動発火1回(PO GO) → 名簿・削除結果・黒板をPOに提示し検算 → 問題なければ週1自動続行 → 避難訓練(黒板を意図的に古い値へ書き換え→Discord着信実測=K4合格) → 復元。

## 3. 弊害・トレードオフ(空欄不可)
- 名簿の除外判定にバグがあれば誤削除リスク。手動発火1回目の検算(稼働13台All Up・削除は名簿記載のみ)で潰す。
- node_exporterコンテナの再作成が1回発生(数秒・アプリ本体は無停止)。
- 検出遅延は最長8日+scrape間隔。ディスク60%ラインの余白内で許容(K8)。
- 監視サーバー(prod2)自体の停止は本仕組みでは検出しない(既存早期警告K9の担当)。

## 4. 外部・過去事例
dead-man's-switch(無音検出)はPrometheus運用の標準手法(absent()/timestamp鮮度監視)。自前通知(失敗時self-report)は無音死を検出できないため不採用。過去事例: 本リポジトリADR-124が同種のtextfile/pushgateway週次指標を先行運用。

## 5. 受入基準(各基準に検証方法)
| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 名簿方式で稼働中・最新1世代が1件も削除されない | 手動発火後、docker ps全Up＋削除ログと名簿の突合(生出力) |
| A2 | 黒板が成功時のみ更新される | 手動発火後、黒板のepochと実行時刻の一致(生出力) |
| A3 | prod2から黒板メトリクスが読める | Prometheus API query結果(生出力) |
| A4 | 避難訓練で警報がDiscord着信 | 着信スクリーンショット/ログ(K4合格) |
| A5 | prod2掃除係がcron登録済み | crontab -l 生出力 |

## 6. 維持の仕組み(空欄不可)
- 守り手: monitoring/prometheus/alert_rules.yml(黒板鮮度＋absent警報)。掃除の仕組み自体の死をDiscordへ通知する。
- 守り手2: .github/workflows 既存CI(監視スタック整合性チェック)がルールファイル構文を検査。
- 対象: f2-cleanup.shの停止・cron消失・黒板配線の断線。
- 人手部分: 警報着信時の対処はPO判断(手順は改修PRのdesign追記で明文化)。

## 7. 別便(この設計ではやらない・忘備)
空き箱(volume)163個削除(二段階退避つき) / prod2秘密.bak廃棄 / メモリ増強便(K7・費用判断) / OS日誌2.1GBのsudo問題 / gha-exporter旧版入替(デプロイ運用)。

## 8. 接触面分析(6面)
①人: PO=GO発行と検算のみ(手作業なし)。②エージェント: 実装役が全操作。本design・カードが手順の正本。③機械: cron(prod1/prod2)・node_exporter・Prometheus・alertmanager・CI(監視スタック整合性チェック)。④データ: DBに触れない(tenant_004接触なし)。イメージ・黒板ファイルのみ。⑤本番: prod1のexporterコンテナ再作成1回(数秒)・アプリ無停止。deploy.ymlは触らない。⑥外部: Discord webhook(既存)への通知のみ。利用者影響なし。
