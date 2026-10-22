<!-- 状態: PO 承認済み（2026-10-22。PO 返信「1」= KGI G1〜G3 を修正なしで承認・対策1は案M）。Architect 自己審査 APPROVE（条件付き：U1〜U3 は各便カード前に解消） -->
# Phase 3 設計 — outage-recovery-watch（さくらメンテ予告の見張り＋復旧後点検）

この文書は何か(専門用語なしの1行): さくらの点検予告に気づけるようにし、本番が止まって戻ったときに元どおりか自動で確かめて知らせる仕組みの設計。

親: [docs/specs/ai-ops-247/README.md](../../specs/ai-ops-247/README.md)（区分: 既存テーマ ai-ops-247 の延長。STANDARD-WORKFLOW §1.8 により仕様書の履歴に追記）

**対象ADR**: 新規 ADR 起案予定（ADR-1012 AI保守運用24時間化の延長として扱う。通知経路の正本=Alertmanager、障害記録の正本=ops_incidents を踏襲）  
**recon**: docs/handoff/outage-recovery-watch/recon.md  
**日付**: 2026-10-22  
**担当**: Planner（Claude Opus）

---

## 0. 発端（事実）

- 2026-10-21 15:54 JST、さくらから緊急メンテ予告メール（作業 10/21 15:00〜10/22 18:00、大阪含む、1VPS約1時間停止）が PO の業務用メールに届いたが未読。
- 2026-10-22 12:02〜12:54 JST、prod1 が一時停止。App/API/LP 全停止。利用者への事前告知なし。
- 復帰後、prod1 の時計が 約40分36.7秒遅れ（Prometheus の node_time_seconds - timestamp(node_time_seconds)、instance=app-vps が -2436.7s。生出力 ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/timesync/impact/prom_skew.txt・prom_skew.json）。13:05頃に一度に補正。
- その間、CeleryHeartbeatStale / ViewerInventoryStale / ContainerStateStale が誤って鳴った（実際は毎分動いていた）。DB に約40分古い時刻の行が最低2行（障害記録1行・解析ジョブ1行）。生出力 ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/cause.md:7、~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/alerts.md、~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/timesync/impact/ops_incidents_row.txt・db_more.txt・beat_nonminute.txt
- 復帰時に「アプリが元どおりか」を確かめる仕組みは無い（recon §4: deploy.yml は push 起動のみ、ServiceDown は「解決」通知だけ）。時計ずれの警報も無い。

## 1. KGI（PO 承認済み 2026-10-22）

| # | KGI（POが○×で判定できる形） |
|---|---|
| G1 | さくらから点検・障害のメールが届いてから **10分以内** に、Discord の運用チャンネルへ「件名・作業日時」が1件届く |
| G2 | 本番サーバーが止まって戻ったとき、戻ってから **10分以内** に Discord へ「点検結果（アプリ・API・LP・裏の作業・時計）」が1件届く。全部 OK なら ✅、1つでも NG なら ❌ と NG 項目名 |
| G3 | 本番の時計が **60秒以上** ずれたら、5分以内に Discord へ「時計ずれ」の警報が1件届く。時計がずれている間は、時刻比較型の「止まっている」警報（誤警報）を鳴らさない |

## 2. 対象と対象外

- 対象: 対策1（メール見張り）、対策2（復旧後点検＋時計ずれ警報＋誤警報の抑止）
- 対象外: 本番の二重化（予備サーバー）、さくら会員情報の変更、時計を自動で直す仕組み（今回は自動補正された。直す操作は本番変更で別判断）、利用者への自動告知（告知文は PO が出す）

## 3. 設計

### 3-1. 対策1 メール見張り — 受け口ルート（PO 判断）

| 案 | 中身 | 良い点 | 弱い点 |
|---|---|---|---|
| **M（推奨）** | PO の業務用メールで「差出人 sakura.ad.jp」を新しい受け箱（さくらレンタルサーバーに作る ops-notice@ 等）へ自動転送。既存の review_mail_notifier（backend/app/services/review_mail_notifier.py、IMAP・300秒ごと）を「受け箱を複数持てる」形に広げ、ops 用は差出人 sakura.ad.jp だけを Discord 運用チャンネルへ | 動いている部品の流用。読むのは件名・差出人・日時だけ（本文は読まない＝現状と同じ） | PO が Gmail の転送設定（確認メール1回）と受け箱作成をする。prod1 停止中は動かない（予告は停止前に届くので目的は満たす） |
| G | PO の Google アカウントで Apps Script が5分ごとに Gmail を検索し Discord へ | 本番が止まっても動く | 新しい置き場が増える。PO アカウントの認証切れ（7日失効等）を見張る必要。リポジトリの CI に乗らない |
| S | さくら会員メニューで通知先に受け箱を直接追加 | 転送不要 | 追加できるか未確認 |

**採用: M（PO 2026-10-22 選択）**。理由: SSOT（メール→Discord の部品は1つ）、既存の重複防止（Redis 30日）をそのまま使える、CI・テストに乗る。

### 3-2. 対策2 復旧後点検 — 置き場は prod2（監視サーバー）

prod1 が止まっても動く必要があるため prod2 に置く（ADR-080 の分離方針に一致）。

- 新しい小さな点検係（prod2 の Docker 常駐・60秒ごと。prod2 に crontab は無い（docs/adr/ADR-153-data-durability.md:22）ため、同じ /opt/salesanchor-monitoring 配下で常駐する monitoring/github-collector の型に揃える）: API ヘルス（https://api.salesanchor.jp/api/health）を見て、前回「NG」→今回「OK」に変わった時だけ点検を1回実行。前回状態は prod2 のファイル1つに保存。型は mac-jobs-watch（docs/handoff/mac-jobs-watch/design.md）の「起動後点検・復旧通知」に揃える。
- 点検項目（読み取りのみ）: ①App/API/LP の HTTP 200 ②health 本文の database/redis/celery が connected ③prod1 の時計ずれ（HTTP Date ヘッダーと prod2 時計の差 < 60秒）④Celery heartbeat が新しい（Prometheus の celery_heartbeat_last_success_timestamp_seconds）⑤container_state が新しい。
- 結果は Discord 運用チャンネルへ ✅/❌ ＋ NG 項目名。復帰後 15 分の間に NG があれば 5 分おきに最大3回まで再点検して結果を追記（一時的な NG で騒がない）。

### 3-3. 時計ずれ警報と誤警報の抑止（Prometheus/Alertmanager）

- 新ルール ClockSkew: `abs(node_time_seconds{job="node-exporter"} - timestamp(node_time_seconds{job="node-exporter"})) > 60` が 2分続いたら critical（10/22 の実測に使った式と同じ。prod1=instance app-vps・prod2=mgmt-vps の両方を見る）。補助に `node_timex_sync_status == 0` が 10分続いたら warning（時刻合わせが止まった兆候）。U1 で3指標とも値が出ていることを確認済み。
- Alertmanager の inhibit: ClockSkew が鳴っている間、時刻比較型ルール（monitoring/prometheus/alert_rules.yml の式の行で :121 F2CleanupStale、:183 CeleryHeartbeatStale、:222 ViewerInventoryStale、:233 ViewerInventoryStaleOnHold、:248 BackupLocalStale、:261 BackupS3Stale、:327 ContainerStateStale の7本）を抑止。:300 MonitoringConfigCheckStale は GitHub Actions が書く時刻なので対象外。

## 外部・過去事例の参照と我々への応用

- 過去事例（社内）: 2026-10-22 の本件そのもの（予告メール未読→無告知停止、復帰後の時計ずれ→誤警報3件）→ 応用: G1〜G3 の各数値は本件の時間軸（予告は約20時間前着、時計補正まで約11分）から決めた。
- 過去事例（社内）: mac-jobs-watch の「起動後点検・✅復旧通知」→ 応用: 3-2 の状態ファイル＋変化時だけ通知の型をそのまま使う。
- 外部事例: 該当なし：理由 = さくらVPS固有の運用（予告メール・メンテ後の時刻ずれ）は、さくら自身の予告メール文面「メンテ完了後 ntpd が停止する可能性」が一次情報であり、他社事例の数値は本設計の判断材料にならないため。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| G1: さくら差出人のテストメールが10分以内に Discord 運用チャンネルに1件届く。差出人が他のメールは届かない | 本番で PO がさくら差出人を模したテスト転送を1通（または過去の予告メールを再転送）→ Discord の到着時刻を記録。差出人絞り込みは pytest（review_mail_notifier の新テスト） |
| G2: prod1 の API を止めずに「NG→OK」を模擬して ✅ 通知が1件届く。NG 項目があれば ❌＋項目名 | prod2 の点検係を状態ファイル「NG」で1回動かす実機確認＋点検係の単体テスト（NG 判定の各項目） |
| G3: 時計ずれ 60秒超で ClockSkew が鳴り、その間時刻比較型の警報が抑止される | promtool test rules（ClockSkew と inhibit の単体テスト）を CI で実行 |
| 既存の review@ 通知が変わらない | 既存 pytest がそのまま通る |

## 技術 How・KPI

- KPI: G1 到着時間（分）、G2 到着時間（分）・誤 ❌ 件数、G3 誤警報件数（時計ずれ中の時刻比較型警報＝0件）
- 技術選択: 対策1は既存 IMAP 部品の拡張（理由: SSOT）。対策2は prod2 の Docker 常駐（理由: prod1 停止中も動く・ADR-080）。時計は Prometheus ルール（理由: 通知経路の正本=Alertmanager、ADR-1012）

## 弊害・トレードオフ

- 転送設定を誤るとさくら以外のメールが流れる → 差出人絞り込みをコード側でも二重に持つ
- 点検係の誤 ❌ で騒がしくなる → 復帰後15分は再点検で確定させ、最大3回で打ち切り
- inhibit で本物の停止を見逃す → 抑止は ClockSkew 発火中だけ。ServiceDown・KumaMonitorDown は抑止しない
- prod1 停止中は対策1が動かない → 予告メールは停止前に届くので許容。停止そのものは Kuma が既に知らせる

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 0 | PO: KGI 承認・受け口ルート選択（済 2026-10-22・案M） | PO |
| 1 | 便1: 時計ずれ警報＋inhibit（Prometheus/Alertmanager、promtool テスト） | Sonnet（実装カード後） |
| 2 | 便2: 復旧後点検係（prod2 Docker 常駐・状態ファイル・Discord） | Sonnet（実装カード後） |
| 3 | 便3: メール見張り（review_mail_notifier の複数受け箱化＋差出人絞り込み）＋ PO の転送設定 | Sonnet＋PO（GUI） |

便ごとに 変更→反映→測定。

## 継続

- 完了後の監視: 次のさくらメンテ予告で G1 の到着時間を記録。prod1 の次回停止・復帰で G2 を記録
- 次フェーズへの引き継ぎ: 点検項目の追加は 3-2 の項目表に足す

## 維持の仕組み

- 守り手: monitoring/prometheus/alert_rules.yml（ClockSkew は promtool テストが CI で守る）
- 守り手: 点検係の単体テストと review_mail_notifier の pytest（CI）
- 対象: 対策1の転送設定・受け箱、対策2の点検係、ClockSkew ルール
- 関所なしの場合: 転送設定は PO の Gmail 側にありリポジトリで検査できない。代わりに便3で「受け箱に30日メールが来ない」ときに Discord へ知らせる見張りを入れる（さくらは月数通の案内を送るため、30日無着信は転送切れの兆候）

## 未解決事項（実装カード発行前に解消する）

- U1（解消 2026-10-22）: node_time_seconds・node_timex_offset_seconds・node_timex_sync_status が app-vps / mgmt-vps とも値を返す。collector の無効化なし（docker-compose.exporters.yml:12-17）。promtool のルール試験は .github/workflows/monitoring-check.yml:70-75 で CI 実行済みの仕組みがある（monitoring/prometheus/tests/alert_rules_test.yml）。生出力 ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/prevention/u1u2/
- U2（一部解消 2026-10-22）: prod2 の設定は /opt/salesanchor-monitoring に repo と同じ相対パスで手作業コピー＋reload で反映する（前例 docs/handoff/ai-ops-247/card-stage1-bin7.md の §8。自動配置の workflow は無い）。ずれは monitoring-config-drift.yml が毎日検知する。Alertmanager の Discord 送り先はファイル参照（monitoring/alertmanager/alertmanager.yml:14、docker-compose.monitoring.yml:180）。残り: 便2 で点検係の通知を Alertmanager 経由にするか（ADR-1012 決定1）を便2カードで確定。prod2 への反映は無制限鍵を使うため、各便で PO の同意票が要る
- U3（解消）: PO が案M を選択（2026-10-22）。便3 では PO の転送設定・受け箱作成の手順書をカードに含める

## Architect 自己審査（同一AIによる自己審査）

- 判定: **APPROVE（条件付き）** — KGI・対象範囲・受入条件は○×で検証可能。U1〜U3 は各便のカード発行前の確認事項として切り出し済みで、設計の骨格を変えない
- 修正済み: ①recon に無いルール名を書いていた箇所を行番号参照に直した ②維持の仕組みで「半年に1回」と「週次」が矛盾していたのを30日無着信の見張りに一本化
- 2回目（reviewer REVISE 2026-10-22 への対応）: ③抑止対象に ViewerInventoryStaleOnHold を足し行番号を式の行に統一 ④実測値に生出力の出典を付け U1 と測り方の矛盾を解消 ⑤状態表示を承認済みに統一 ⑥区分=ai-ops-247 の延長と決め仕様書へリンク ⑦U1/U2 の確認結果で点検係の置き方を cron から Docker 常駐に変更（KGI は不変）
- 残る注意: 外部事例は「該当なし」（理由記載）。設計合格は PO 承認・実装開始の承認を兼ねない
