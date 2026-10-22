<!-- 状態: PO 承認済み（2026-10-22。PO 返信「1」= KGI G1〜G3 を修正なしで承認・対策1は案M）。Architect 自己審査 APPROVE（条件付き：U1〜U3 は各便カード前に解消） -->
# Phase 3 設計 — outage-recovery-watch（さくらメンテ予告の見張り＋復旧後点検）

この文書は何か(専門用語なしの1行): さくらの点検予告に気づけるようにし、本番が止まって戻ったときに元どおりか自動で確かめて知らせる仕組みの設計。

親: [docs/specs/ai-ops-247/README.md](../../specs/ai-ops-247/README.md)（区分: 既存テーマ ai-ops-247 の延長。STANDARD-WORKFLOW §1.8 により仕様書の履歴に追記）

**対象ADR**: 新規 ADR は作らない（ADR-1012 決定1・ADR-080 の範囲。§3-2-1）（ADR-1012 AI保守運用24時間化の延長として扱う。通知経路の正本=Alertmanager、障害記録の正本=ops_incidents を踏襲）  
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

#### 3-1-1. 便3 での確定（2026-10-23 Opus。KGI G1 は不変。詳細は card-bin3.md）

- 部品の分け方: review@ の部品（backend/app/services/review_mail_notifier.py）は 1 行も変えない。運用の受け箱用に新しい部品 `ops_mail_notifier.py` を作り、review@ の部品からヘッダーの読み解き（`_decode_mime_header`）と Redis の取得（`_get_redis`）を読み込んで使う。→ 3-1 の「受け箱を複数持てる形に広げる」を変更
  - 理由1: 受け入れ基準「既存の review@ 通知が変わらない」を、既存の 39 件の試験がそのまま通ることで確かめられる。
  - 理由2: 運用の受け箱は、絞り込み・本文の一部の読み取り・重複防止の鍵の形・検索の範囲が review@ と違う。1 つの関数に分岐を足すより、別の関数のほうが試験しやすい。
  - 理由3: 重複防止の鍵を受け箱ごとに分けられる（今の鍵 `review_mail:notified:<uid>` には受け箱の名前が無く、同じ UID がぶつかる。recon 2026-10-23）。
- 絞り込み（コードの側）: 差出人のアドレスのドメインが `sakura.ad.jp` と完全に一致し、かつ件名に「メンテナンス・障害・緊急・停止・工事・再起動・復旧・作業」のどれかを含むメールだけを Discord へ送る。
  - 理由: PO の業務用メールで、さくらの差出人のメールは約 1 年で約 53 通。多くは決済・約款・認証などの案内で、点検・障害の件名は 10/21 の 1 通（2026-10-23 Opus が Gmail で読み取りだけ確認。件名に「［緊急］」「メンテナンス」）。差出人だけで送ると、週に 1 通ほど関係のない知らせが運用チャンネルに流れる。
  - 件名で外れたさくらのメールは送らないが、「さくらからメールが届いた時刻」には数える（下の 40 日の見張り）。
- 作業日時の読み取り: G1 は「件名・作業日時」を求めるが、作業日時は件名に無く本文にある（10/21 の本文「■作業日程 : 2026年10月21日15時00分 - 2026年10月22日18時00分」）。そこで、絞り込みを通ったメールに限り本文の先頭 64KB を読み、「作業日程・作業日時・実施日時・メンテナンス日時・作業期間・日時」と「影響範囲」で始まる行を 1 行ずつだけ取り出して送る。→ 3-1 の「本文は読まない」を変更
  - 本文には会員 ID と契約者名が入っているため、取り出した行以外は Discord にもログにも出さない。行が見つからないときは「本文から読み取れませんでした。業務用メールで確かめてください」と送る。
- 通知の道: メールの知らせは Discord へ直接送る（review@ と同じ）。見張り（40 日届かない・読み取りが止まった）はルールにして Alertmanager に載せる。
  - 理由: ADR-1012 決定1（docs/adr/ADR-1012-ai-ops-247.md:31）が定めるのは見張りのルールの経路。メールの中継は見張りのルールではなく、review@ の通知と同じ「知らせ」。件名や作業日時は外の人が書く自由な文で、Alertmanager に載せるには指標の札に入れるか API で直接入れることになり、前者は札の種類が増え続け、後者は札・手順書の検査に乗らない（§3-2-1 理由2 と同じ）。
- 重複防止と検索の範囲: 鍵は `ops_mail:notified:<UIDVALIDITY>:<uid>`（30 日で消える）。検索は「7 日前の日付から後」に限る。
  - 理由: 今の review@ は受け箱の全部を毎回探すので、30 日たって鍵が消えると同じメールをもう一度送りうる。7 日に限れば鍵が消える前に検索から外れる。受け箱を作り直して UID が振り直されても、UIDVALIDITY が変わるので取りこぼさない。
  - review@ の同じ性質は本便では直さない（review@ を変えないため。対象外）。
- 見張り（転送切れ・読み取り停止）:
  - さくらの差出人のメールが届いた時刻を Redis に残し（消えない鍵）、backend の `/metrics` で指標にする（CELERY_HEARTBEAT_TS と同じ型。backend/app/metrics.py:33-36）。40 日届かなければ `OpsMailSilent`（warning・ticket）。→ 維持の仕組みの 30 日を 40 日に変更
    - 理由: 決済の案内は毎月 11 日の朝に届く（2026-05〜10 の 6 か月で毎月 1 通。Gmail で確認）。間隔は最大 31 日なので、30 日では空振りで鳴りうる。
  - 受け箱を読めた時刻も残し、3 時間読めなければ `OpsMailPollStale`（warning・ticket）。パスワードの誤りや受け箱の削除に 40 日待たずに気づくため。
  - 鍵が無い（設定前・Redis が消えた）ときは指標が 0 になり、どちらのルールも鳴らない（式に `> 0` を足す）。設定の後、初めて読めたときに「届いた時刻」の鍵が無ければ今の時刻を入れて 40 日を数え始める。
  - 時計ずれの抑止（§3-3）には足さない。閾値（3 時間・40 日）が 10/22 の実測のずれ（約 41 分）より十分大きいため。
- 送り先: 運用チャンネル（Alertmanager が警報を送るチャンネル）に新しい webhook を PO が作り、GitHub の secret `OPS_MAIL_DISCORD_WEBHOOK` に入れる。受け箱は review@ と同じさくらのレンタルサーバーに作り、接続先は `REVIEW_MAIL_IMAP_HOST`・`REVIEW_MAIL_IMAP_PORT` を使う。受け箱のアドレスとパスワードは secret `OPS_MAIL_IMAP_USER`・`OPS_MAIL_IMAP_PASSWORD` だけに置き、リポジトリには書かない（公開リポジトリで迷惑メールとなりすましを招かないため）。
  - Alertmanager の webhook（prod2 のファイル）を写して使わない。秘密を機体の間で写す操作が増えるため。
- 順番: 便2 の実装を本番で確かめてから便3 の実装を始める（変更は一度に 1 つ。どちらも alert_rules.yml・手順書の本数を変えるため）。

### 3-2. 対策2 復旧後点検 — 置き場は prod2（監視サーバー）

prod1 が止まっても動く必要があるため prod2 に置く（ADR-080 の分離方針に一致）。

- 新しい小さな点検係（prod2 の Docker 常駐・60秒ごと。prod2 に crontab は無い（docs/adr/ADR-153-data-durability.md:22）ため、同じ /opt/salesanchor-monitoring 配下で常駐する monitoring/github-collector の型に揃える）: API ヘルス（https://api.salesanchor.jp/api/health）を見て、前回「NG」→今回「OK」に変わった時だけ点検を1回実行。前回状態は prod2 のファイル1つに保存。型は mac-jobs-watch（docs/handoff/mac-jobs-watch/design.md）の「起動後点検・復旧通知」に揃える。→ 判定の仕方（応答したかで見る）は §3-2-1 で変更
- 点検項目（読み取りのみ）: ①App/API/LP の HTTP 200 ②health 本文の database/redis/celery が connected ③prod1 の時計ずれ（HTTP Date ヘッダーと prod2 時計の差 < 60秒）④Celery heartbeat が新しい（Prometheus の celery_heartbeat_last_success_timestamp_seconds）⑤container_state が新しい。→ 時計の見方（Prometheus の値）と項目の並びは §3-2-1 で変更
- 結果は Discord 運用チャンネルへ ✅/❌ ＋ NG 項目名。復帰後 15 分の間に NG があれば 5 分おきに最大3回まで再点検して結果を追記（一時的な NG で騒がない）。→ 点検の間隔（0・2・4・6 分、❌ の後は 5 分おき）は §3-2-1 で変更

#### 3-2-1. 便2 での確定（2026-10-22 Opus。KGI G2 は不変。詳細は card-bin2.md）

- 通知の道: 点検係は Discord へ直接送らず、Prometheus の指標 → ルール → Alertmanager → Discord の既存の道に載せる（U2 の残りを解消）。
  - 理由1: ADR-1012 決定1（docs/adr/ADR-1012-ai-ops-247.md:25「経路の正本は Alertmanager 1 本」）。
  - 理由2: ルールにすると札・手順書リンク・見出しの検査（monitoring/scripts/check_alert_rules.py）と promtool の単体試験（.github/workflows/monitoring-check.yml:70-75）に乗る。API で直接入れた警報はこの検査に乗らない（check_alert_rules.py は手順書の見出しにルールが無いと NG を出す）。
  - ✅ は新しい子ルート（matcher `alertname="RecoveryCheckPassed"`、continue なし）で Discord だけに送り、解決の通知は出さない（`send_resolved: false`。障害記録の保守 API には載せない）。❌ は既存の道のまま Discord と保守 API の両方に届き、全項目が直ると Discord に「解決」が届く。
- ③時計: HTTP の Date ヘッダーではなく Prometheus の `node_time_seconds{instance="app-vps"}` と読み取り時刻の差で見る（便1 の ClockSkew と同じ式）。理由: 公開 URL の応答は Cloudflare を通るため、Date ヘッダーは prod1 の時計ではない見込みが高い（未確認。確かめるより便1 で実測済みの式を使うほうが確実）。時計が NG の間は④⑤を判定しない（時刻の比較が狂うため。便1 と同じ考え方）。
- 再点検の間隔: 「15 分の間に 5 分おき最大3回」を「復帰を見つけた時から 0・2・4・6 分」に改める。全部 OK になった時点で ✅、6 分でまだ NG なら ❌。理由: 5 分おき3回では ❌ が確定するのが最大 15 分後になり、G2（復帰から 10 分以内に 1 件）を満たせない。❌ の後も 5 分おきに点検を続け、直れば「解決」が届く（打ち切ると ❌ が鳴りっぱなしになるため）。
- 「止まった」「戻った」の判定: 本文の値ではなく「本番の本体が応答したか」で見る（API が本文つきで応答した、またはアプリ画面が HTTP 200 を返した）。理由: 本文の値で見ると、裏方の処理だけが戻らない場合に「戻った」と判定されず ❌ が届かない（G2 違反）。逆に、止まっていないのに裏方の処理の応答確認が外れただけで ✅ が出てしまう（2026-10-22 設計審査の指摘1）。
- 点検係そのものの見張り: 点検係が止まると ServiceDown（alert_rules.yml の `up == 0`）が鳴る。点検の繰り返しが止まったら新しいルール RecoveryCheckStale が鳴る。
- 新しい ADR は作らない（ADR-1012 決定1 と ADR-080 の分離方針の範囲内）。

### 3-3. 時計ずれ警報と誤警報の抑止（Prometheus/Alertmanager）

- 新ルール ClockSkew: `abs(node_time_seconds{job="node-exporter"} - timestamp(node_time_seconds{job="node-exporter"})) > 60` が 2分続いたら critical（10/22 の実測に使った式と同じ。prod1=instance app-vps・prod2=mgmt-vps の両方を見る）。補助に `node_timex_sync_status == 0` が 10分続いたら warning（時刻合わせが止まった兆候）。U1 で3指標とも値が出ていることを確認済み。
- Alertmanager の inhibit: ClockSkew が鳴っている間、時刻比較型ルール（monitoring/prometheus/alert_rules.yml の式の行で :121 F2CleanupStale、:184 CeleryHeartbeatStale、:222 ViewerInventoryStale、:233 ViewerInventoryStaleOnHold、:248 BackupLocalStale、:261 BackupS3Stale、:327 ContainerStateStale の7本）を抑止。:300 MonitoringConfigCheckStale は GitHub Actions が書く時刻なので対象外。

## 外部・過去事例の参照と我々への応用

- 過去事例（社内）: 2026-10-22 の本件そのもの（予告メール未読→無告知停止、復帰後の時計ずれ→誤警報3件）→ 応用: G1〜G3 の各数値は本件の時間軸（予告は約20時間前着、時計補正まで約11分）から決めた。
- 過去事例（社内）: mac-jobs-watch の「起動後点検・✅復旧通知」→ 応用: 3-2 の状態ファイル＋変化時だけ通知の型をそのまま使う。
- 外部事例: 該当なし：理由 = さくらVPS固有の運用（予告メール・メンテ後の時刻ずれ）は、さくら自身の予告メール文面「メンテ完了後 ntpd が停止する可能性」が一次情報であり、他社事例の数値は本設計の判断材料にならないため。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| G1: さくら差出人のテストメールが10分以内に Discord 運用チャンネルに1件届く。差出人が他のメールは届かない | 本番で PO がさくら差出人を模したテスト転送を1通（または過去の予告メールを再転送）→ Discord の到着時刻を記録。差出人絞り込みは pytest（review_mail_notifier の新テスト）→ §3-1-1 で変更: Gmail の転送は過去のメールに効かないため、さくらの形の試験メールを受け箱に直接 1 通入れて到着までの分を測る（card-bin3.md §8）。転送そのものは、次にさくらから届くメール（毎月 11 日の決済の案内）で「届いた時刻」の指標が進むことで確かめる。絞り込みと作業日時の取り出しは pytest（ops_mail_notifier の新しい試験） |
| G2: prod1 の API を止めずに「NG→OK」を模擬して ✅ 通知が1件届く。NG 項目があれば ❌＋項目名 | prod2 の点検係を状態ファイル「NG」で1回動かす実機確認＋点検係の単体テスト（NG 判定の各項目） |
| G3: 時計ずれ 60秒超で ClockSkew が鳴り、その間時刻比較型の警報が抑止される | ClockSkew は promtool test rules を CI で実行。inhibit は promtool で試せないため、本番と同じ版の Alertmanager を手元で外部通信なしに起動して疑似警報で確かめ（便1 カード §5）、抑止対象の警報名が実在することを check_alert_rules.py で CI が毎回確かめる |
| 既存の review@ 通知が変わらない | 既存 pytest がそのまま通る |

## 技術 How・KPI

- KPI: G1 到着時間（分）、G2 到着時間（分）・誤 ❌ 件数、G3 誤警報件数（時計ずれ中の時刻比較型警報＝0件）
- 技術選択: 対策1は既存 IMAP 部品の拡張（理由: SSOT）。対策2は prod2 の Docker 常駐（理由: prod1 停止中も動く・ADR-080）。時計は Prometheus ルール（理由: 通知経路の正本=Alertmanager、ADR-1012）

## 弊害・トレードオフ

- 転送設定を誤るとさくら以外のメールが流れる → 差出人絞り込みをコード側でも二重に持つ
- 点検係の誤 ❌ で騒がしくなる → 復帰を見つけてから 0・2・4・6 分の 4 回の点検で確定させる（§3-2-1）。❌ の後は 5 分おきに点検を続け、直れば「解決」が届く。本番配置の前に、状態を変えない 1 回だけの点検で NG が 0 件であることを確かめる（card-bin2.md §8）
- ✅ の後に約 15 分以内でもう一度止まって戻ると、2 度目の ✅ が届かない見込みがある（未確認。Alertmanager が送った記録を片付ける時間。❌ は届く）→ 起きたら記録して見直す（card-bin2.md §7）
- inhibit で本物の停止を見逃す → 抑止は ClockSkew 発火中だけ。ServiceDown・KumaMonitorDown は抑止しない
- prod1 停止中は対策1が動かない → 予告メールは停止前に届くので許容。停止そのものは Kuma が既に知らせる
- 件名の言葉で絞るため、言葉に当たらない件名の点検の知らせを取りこぼす → 言葉は 8 つと広めにとる（§3-1-1）。取りこぼしに気づいたら、件名を記録して言葉を足す（言葉は ops_mail_notifier.py の 1 か所）
- 差出人は偽れるため、さくらを装ったメールが受け箱に届くと Discord に偽の知らせが出る → 受け箱のアドレスを公開しない（secret だけに置く）。知らせには「本文は業務用メールで確かめる」と書き、知らせだけで本番の操作をしない
- 本文の形が変わると作業日時が取れない → 「読み取れませんでした」と送り、件名は届く（G1 の半分は満たす）。起きたら行の言葉を足す
- さくらのレンタルサーバーの迷惑メールの仕分けが転送されたメールを受信箱の外へ移すと届かない（未確認）→ PO の手順で受け箱の迷惑メールの仕分けを確かめる（card-bin3.md §8）。外れても 40 日の見張りで気づく

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 0 | PO: KGI 承認・受け口ルート選択（済 2026-10-22・案M） | PO |
| 1 | 便1: 時計ずれ警報＋inhibit（Prometheus/Alertmanager、promtool テスト） | Sonnet（実装カード後） |
| 2 | 便2: 復旧後点検係（prod2 Docker 常駐・状態ファイル・Discord） | Sonnet（実装カード後） |
| 3 | 便3: メール見張り（review_mail_notifier の複数受け箱化＋差出人絞り込み）＋ PO の転送設定 → §3-1-1 で「運用の受け箱用の新しい部品＋件名の絞り込み＋作業日時の行の取り出し＋見張り 2 本」に変更（card-bin3.md） | Sonnet＋PO（GUI） |

便ごとに 変更→反映→測定。

## 継続

- 完了後の監視: 次のさくらメンテ予告で G1 の到着時間を記録。prod1 の次回停止・復帰で G2 を記録
- 次フェーズへの引き継ぎ: 点検項目の追加は 3-2 の項目表に足す

## 維持の仕組み

- 守り手: monitoring/prometheus/alert_rules.yml（ClockSkew は promtool テストが CI で守る）
- 守り手: 点検係の単体テストと review_mail_notifier の pytest（CI）
- 対象: 対策1の転送設定・受け箱、対策2の点検係、ClockSkew ルール
- 関所なしの場合: 転送設定は PO の Gmail 側にありリポジトリで検査できない。代わりに便3で「受け箱に30日メールが来ない」ときに Discord へ知らせる見張りを入れる（さくらは月数通の案内を送るため、30日無着信は転送切れの兆候）→ §3-1-1 で 40 日に変更（決済の案内の間隔が最大 31 日のため）。あわせて「3 時間受け箱を読めない」見張りを足す

## 未解決事項（実装カード発行前に解消する）

- U1（解消 2026-10-22）: node_time_seconds・node_timex_offset_seconds・node_timex_sync_status が app-vps / mgmt-vps とも値を返す。collector の無効化なし（docker-compose.exporters.yml:12-17）。promtool のルール試験は .github/workflows/monitoring-check.yml:70-75 で CI 実行済みの仕組みがある（monitoring/prometheus/tests/alert_rules_test.yml）。生出力 ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/prevention/u1u2/
- U2（一部解消 2026-10-22）: prod2 の設定は /opt/salesanchor-monitoring に repo と同じ相対パスで手作業コピー＋reload で反映する（前例 docs/handoff/ai-ops-247/card-stage1-bin7.md の §8。自動配置の workflow は無い）。ずれは monitoring-config-drift.yml が毎日検知する。Alertmanager の Discord 送り先はファイル参照（monitoring/alertmanager/alertmanager.yml:14、docker-compose.monitoring.yml:180）。残り: 便2 で点検係の通知を Alertmanager 経由にするか（ADR-1012 決定1）を便2カードで確定 → 確定（2026-10-22。§3-2-1。Alertmanager 経由）。prod2 への反映は無制限鍵を使うため、各便で PO の同意票が要る
- U3（解消）: PO が案M を選択（2026-10-22）。便3 では PO の転送設定・受け箱作成の手順書をカードに含める → card-bin3.md §8 に収めた（2026-10-23）
- U4（未確認・便3 の本番配置で確かめる）: PO の業務用メール（Google Workspace）で外への自動転送が管理者の設定で止められていないか。止められていれば、PO が管理者の設定で許すか、Opus が案G・案S を出し直す（card-bin3.md §8 の分岐）

## Architect 自己審査（同一AIによる自己審査）

- 判定: **APPROVE（条件付き）** — KGI・対象範囲・受入条件は○×で検証可能。U1〜U3 は各便のカード発行前の確認事項として切り出し済みで、設計の骨格を変えない
- 修正済み: ①recon に無いルール名を書いていた箇所を行番号参照に直した ②維持の仕組みで「半年に1回」と「週次」が矛盾していたのを30日無着信の見張りに一本化
- 2回目（reviewer REVISE 2026-10-22 への対応）: ③抑止対象に ViewerInventoryStaleOnHold を足し行番号を式の行に統一 ④実測値に生出力の出典を付け U1 と測り方の矛盾を解消 ⑤状態表示を承認済みに統一 ⑥区分=ai-ops-247 の延長と決め仕様書へリンク ⑦U1/U2 の確認結果で点検係の置き方を cron から Docker 常駐に変更（KGI は不変）
- 残る注意: 外部事例は「該当なし」（理由記載）。設計合格は PO 承認・実装開始の承認を兼ねない
