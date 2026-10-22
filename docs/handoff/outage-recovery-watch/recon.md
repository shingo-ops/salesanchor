# Phase 2 recon — outage-recovery-watch（さくらメンテ予告の見張り＋復旧後点検）

この文書は何か(専門用語なしの1行): 本番が止まった件の再発防止を作る前に、今ある仕組みを調べた記録。

親: [docs/specs/ai-ops-247/README.md](../../specs/ai-ops-247/README.md)

基準: git fetch 後の origin/main 14b1b6d39（2026-10-22）。読み取りのみ。発端: 2026-10-22 12:02〜12:54 JST さくらVPS緊急メンテで prod1 一時停止、予告メール未読、復帰後に prod1 時計 約40分36.7秒遅れ（13:05頃自動補正）・誤警報3件（生出力 ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/cause.md・~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/timesync/impact/prom_skew.txt）。

# recon_raw: 止まったサーバーの再発防止（対策1 さくらメール通知 / 対策2 復旧後の自動確認）
基準: git fetch origin 後の worktree（origin/main = 14b1b6d39）。読み取りのみ。パスは worktree 相対。
worktree: ~/worktrees/salesanchor/release-outage-recovery-watch（ブランチ release/outage-recovery-watch）
preflight: PREFLIGHT OK（identity=shingo-cc）。警告2件: 本店が origin/main より4086コミット遅れ／本店に未保存31件。全文 ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/prevention/preflight.txt
worktree作成: 成功。最後に「claude 起動」で "Input must be provided either through stdin or as a prompt argument when using --print" のエラー（worktree自体は作成済み）。全文 ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/prevention/worktree.txt

## 1. 既存ADR
- ADR-069 (docs/adr/ADR-069-uptime-kuma-activation.md:13-21,47-57): Kuma有効化。App/API/LP/PG/Redis/Meta/Firebaseを監視。:44 「Discord Webhook 通知設定」は手動(UI)作業。
- ADR-080 (docs/adr/ADR-080-monitoring-vps-separation.md:14-36,105): 監視(prometheus/grafana/loki/uptime-kuma)は管理室VPS(prod2)に分離。「アプリVPSダウン時でも Uptime Kuma が検知・Discord 通知できる」(:105)。prod1に残るのは node-exporter 等のexporterとpromtail(:16-24)。:167-172 追記: prod2 の monitoring-tunnel.service(autossh) が prod2->prod1 のexporter転送。
- ADR-081: 入口制御(UFW等)・workers=1。時計/メール/復旧の記述なし(grep済み)。
- ADR-1012 (docs/adr/ADR-1012-ai-ops-247.md:25-31): 決定1「経路の正本は Alertmanager 1本。全ルールに札(page/auto/ticket)と手順書リンク」/決定2「障害記録の正本はアプリDBの障害記録の表(ops_incidents)。書込は保守APIだけ」/決定3 応急処置はprod1ホストの定期実行/決定5 ADR-1009(C)は予備。Status=Proposed(:5)。:16「過去障害4件のうち報知器が人より先に鳴ったのは0件」。
- ADR-1009 (docs/adr/ADR-1009-discord-ops-intake.md:36): 「受付はMacが起きている間だけ。停止は番人(launchd)が別のwebhookでPOに通知」。:26 監視側設定は変更しない。
- ADR-1011: 許可の自律保守。本件と無関係(読んだが該当なし)。
- docs/adr/FEATURE-INDEX.md:47 「24時間保守運用/障害記録/応急処置/routines/アラート札 -> ADR-1012(Proposed)/ADR-1009/ADR-115」。
- 「メンテ/メール/さくら予告/時刻ずれ/ntp/chrony/node_timex」を ADR・docs/runbooks・docs/handoff/ai-ops-247・mac-jobs-watch・docs/ops で grep: 該当なし(時刻関連は ADR-1016:48 のサーバー時計で画面更新、無関係)。=> 既存ADRに「さくらのメンテ予告」「時計ずれ」を扱うものは【未発見】。
- review@ メール通知は ADR 無し: docs/ 内に ADR は無く、導入コミット 0fcc532cf "feat(mail): review@salesanchor.jp 新着メール → Discord 通知" のみ(git log --diff-filter=A)。

## 2. 既存の通知経路
- Alertmanager: monitoring/alertmanager/alertmanager.yml:1-25
  - route 既定=discord-server-alerts、routes で discord-server-alerts(continue:true) と ops-api の2本(:7-10)
  - discord: webhook_url_file: /etc/alertmanager/secrets/discord-webhook, send_resolved:true (:12-15)
  - ops-api: https://api.salesanchor.jp/api/v1/ops/alertmanager (:16-25) ← prod1のbackendへ。prod1停止中は届かない。Bearer は /etc/alertmanager/secrets/ops-ingest-token
  - 秘密の置き場: docker-compose.monitoring.yml:180-181 ./secrets/alertmanager-discord-webhook, ./secrets/ops-ingest-token (prod2側)
- Prometheus: monitoring/prometheus/prometheus.yml:12-15 alertmanager:9093。scrape: node-exporter(mgmt-vps:node-exporter:9100 / app-vps:host-gateway:19100 =prod2->tunnel->prod1) :25-32、backend https://49.212.137.46:443/metrics :36-45、uptime-kuma :79-85。
- Kuma: monitoring/uptime-kuma-monitors.yml:9-55 に App本番/API ヘルスチェック/LP/基盤4本(60秒)。通知先(Discord)の設定自体はリポジトリに無い(ADR-069:44 UI作業)。Prometheusが monitor_status を取り KumaMonitorDown(alert_rules.yml:144-153, 2分, page)で再通知。
- ops_incidents: migrations/20261016_100000_create_ops_incident_tables.sql:5-34(1障害1行,fingerprint+starts_at)。書込は backend/app/routers/ops.py:213 POST /ops/alertmanager(Bearer=OPS_INGEST_TOKEN :97-99)。ops.py に Discord 送信は無い(grep: discord/webhook 該当なし)。Discordへの通知は Alertmanager 直。
- Discord webhook 名のみ(コード/CI内の環境変数・secret名): DISCORD_WEBHOOK_OWNER_PING, ADMIN_NOTIFICATION_DISCORD_WEBHOOK, DISCORD_WEBHOOK_PR, DISCORD_WEBHOOK_SCHEDULED_REPORT, DISCORD_WEBHOOK_PLAN_REVIEW, DISCORD_WEBHOOK_PERMISSION, DISCORD_WEBHOOK_URL(Grafana用: docker-compose.monitoring.yml:46), ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK, ROLLBACK_DISCORD_WEBHOOK, REVIEW_MAIL_DISCORD_WEBHOOK, QA_DISCORD_WEBHOOK_URL, DISCORD_WEBHOOK_OPS, DISCORD_WEBHOOK_CI, DISCORD_ERR_WEBHOOK_PERMISSION。Alertmanager用=prod2のファイル alertmanager-discord-webhook。Mac番人用=~/.config/sa-ops-intake/watchdog-webhook(docs/handoff/mac-jobs-watch/design.md:24)。値は一切確認していない。

## 3. メールを機械で読む既存の仕組み
- backend/app/services/review_mail_notifier.py(全文読了)
  - 方式: IMAP over SSL(imaplib.IMAP4_SSL :186)。Gmail API / GAS ではない。
  - 接続先: .env.example:107-116 REVIEW_MAIL_IMAP_HOST=salesanchor.sakura.ne.jp, PORT=993, USER=review@salesanchor.jp (さくらのレンタルサーバーのメールボックス)。POのGmail等 <POの業務用メール> ではない。
  - 取得: INBOX 全件 UID検索(:195)→ BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)] のみ(:209-213、本文・添付は読まない:docstring :8)。通知済UIDをRedisに30日(:47-48,102-114)。件名200字・差出人300字で切る(:49-50)。Redis不能時は全スキップ(:179-183)。
  - 通知: REVIEW_MAIL_DISCORD_WEBHOOK へ httpx.post(:147)、allowed_mentions parse:[] (:144)、メンション任意(REVIEW_MAIL_DISCORD_MENTION :43,54-70)。本文に「さくらWebメールで確認」URL。
  - 実行: backend/app/celery_app.py:139-143 task app.tasks.review_mail_monitor.check_review_mail_inbox を 300秒ごと(Celery beat)。task: backend/app/tasks/review_mail_monitor.py:18-38。未設定なら no-op(:139 コメント)。本番secretはdeploy.yml:341-346。
  - テスト: backend/tests/test_review_mail_notifier.py(存在確認のみ)。
- 流用の材料(事実):
  - 流用しやすい: IMAP取得・重複排除・Discord投稿の部品は再利用可能な形(関数単位)。
  - 差分/制約(事実): (a) 現在の宛先は review@salesanchor.jp。さくらの予告は support@sakura.ad.jp -> <POの業務用メール> 宛(PO申告)。メールボックスが違うため、そのままでは届かない。転送設定 or 別IMAP設定が必要。 (b) 現状は全メールを通知(送信元フィルタ無し)。差出人 sakura.ad.jp での絞り込みが無い。 (c) 実行場所が prod1 の Celery。prod1停止/不調時は走らない(メンテ中の通知は出せないが、予告メールは停止前に届くので予告の検知自体は可能)。
  - Gmail/Google系の他処理: backend/app/services/google_calendar.py, google_drive_oauth.py, auth_mail.py(認証メール送信)。メール受信のGmail API処理は【未発見】。GASでメールを読む処理: gas/ と scripts/ の grep では該当【未発見】(GASの在庫一覧系は別リポジトリの可能性。【未確認】)。
  - <POの業務用メール> は monitoring/prometheus/prometheus.yml:84 の Kumaログイン名として登場するのみ。

## 4. 復旧後確認の材料
- デプロイの確認(deploy.yml): トリガーは main への push のみ(.github/workflows/deploy.yml:3-6)。サーバー復帰では動かない。
  - Post-deploy smoke: deploy.yml:583-596 -> scripts/smoke_test_post_deploy.sh(195行): RLS/ポリシー/ロール/テナント分離/fail-close/[7]backend health 3回再試行(:107-110)/SA18時のDB接続/配送認証RLS。時計の検査は無い。
  - Verify deployment: deploy.yml:796-812 `curl -sf https://jarvis-claude.uk/api/health || echo warning`(失敗しても続行) + 以降 migration 055 検証・design-site smoke(:875-887)。
  - Finalize: deploy.yml:649-690 backend /api/health を待つ。
- ai-ops の healthcheck/container_state:
  - scripts/ops/container_state.py:1-60: prod1 の cron 毎分、docker状態を textfile(container_state.prom)に書く。SERVICES=celery-worker, celery-beat, discord-gateway, gemini-egress, backend(:18)。時計は見ない。
  - alert_rules.yml:310-347: ContainerUnhealthy(page)/ContainerStateStale(5分書かれない,page)/ContainerHealthcheckMissing(ticket)。
  - docker-compose.yml に healthcheck 9か所(grep: :21,154,188,282,322,373,409,456,490)。
- up==0 から復帰したとき: alert_rules.yml:58-67 ServiceDown(up==0, 2分, page)。復帰すると Alertmanager が send_resolved:true(alertmanager.yml:15)で「解決」をDiscordに送るだけ。復帰後にアプリ状態を確認する処理は【リポジトリ内に未発見】。
- 時計ずれ:
  - monitoring/ 全体・docs で node_timex_offset_seconds / node_time_seconds / ntp / chrony の参照は【なし】(grep済み)。時刻ずれ警報は【なし】。
  - node-exporter は prom/node-exporter:v1.11.1(docker-compose.exporters.yml:5, monitoring.yml:83)。起動引数に --no-collector.* の無効化指定は無い(exporters.yml:13-17)。よって既定で有効な time / timex コレクタのメトリクスは出ている【推測】(公式既定。実機の /metrics で node_timex_offset_seconds を確認していない=【未確認】)。
  - 今回の誤警報の仕組み(コードからの事実): CeleryHeartbeatStale は `time() - celery_heartbeat_last_success_timestamp_seconds > 600`(alert_rules.yml:183-185)。heartbeat値は prod1 の backend が time.time() で書く(backend/app/celery_health.py:51)。time() は Prometheus(prod2)の時計。prod1が約40分遅れなら差は40分超になり得る【推測:結論は実測要。10/22の時計の遅れ値と合わせて検証していない】。
  - 他の時刻比較型ルール(同じ誤警報の可能性): F2CleanupStale(:121), ViewerInventoryStale(:222), ViewerInventoryStaleOnHold(:233), BackupLocalStale(:248), BackupS3Stale(:261), ContainerStateStale(:327)（式の行）。prod1側で書いた時刻を使う点は同じ(確認は式のみ)。

## 5. Mac常駐・定期実行の同種見張り
- mac-jobs-watch: docs/handoff/mac-jobs-watch/design.md:1-12,20(scripts/mac-jobs-watch.sh と ops/launchd/jp.salesanchor.mac-jobs-watch.plist, 30分ごと+ログイン時)。Macの自動お手入れの停止/失敗をDiscord通知。通知先=watchdog-webhookファイル(:24)。起動直後の判定・復旧通知(「✅ 復旧」:3-1 ⑧)・起動後の点検(:6)の作りがあり、対策2の「復帰後の点検通知」の型の前例になる。ただし対象はMac、prod1ではない。
- ai-ops-247: docs/handoff/ai-ops-247/ (recon, design, stage1-3, card-*)。docs/specs/ai-ops-247/{README,ideal-state,kgi}.md。時計ずれ/メンテ予告/復帰後確認の語は grep で【なし】。
- discord-ops-intake: ADR-1009(Macの常駐受付。Macが起きている間だけ)。
- GitHub Actions の cron 一覧(.github/workflows の `cron:` を含む17本): brand-asset-monitor, monitoring-config-drift(毎日 pushgatewayへ) ほか。サーバー復帰検知用は【なし】。

## 6. 正式な様式
- docs/specs/README.md:3-5,102-105 「索引に載る領域に触れる開発は設計仕様書を先に読む(無ければ作る)。新しい設計仕様書を作ったら表に1行足す」。近い既存領域: 「AI 保守運用 24 時間化(ai-ops-247)」(:10) と「mac-jobs-watch」。
- docs/STANDARD-WORKFLOW.md:
  - :30-39 §1.5 設計仕様書は3ファイル標準: README.md / ideal-state.md(POの言葉のみ) / kgi.md。保存先 docs/specs/<テーマ>/。
  - :65-75 §1.8 区分判定: 新規テーマ=フルセット / 既存の延長=既存テーマの履歴に追記 / 軽微。本件は ai-ops-247 の延長にも新規にも読めるため区分は【PO/設計で判定】→ design.md で ai-ops-247 の延長と決定。
  - :77-82 §2 recon: docs/handoff/<仕事名>/recon.md、フルパス:行番号、既存ADR検索結果の明記。design: 各受入基準に検証方法リンク、recon/ADR 相互参照、「外部・過去事例の参照と我々への応用」欄(空欄不可)。
  - :55-63 §1.7 design.md 末尾「## 維持の仕組み」(守り手パス・対象・関所なしの場合)必須。
  - :43-51 §1.6 親子リンクと素人向け説明(1行説明)。例: docs/handoff/mac-jobs-watch/design.md:3。
  - CLAUDE.md(リポジトリ): recon.md と design.md は必ず git add。KGI/KPIは画面/出力で○×判定できる粒度。PR本文に「### 標準ワークフロー確認」。migrations/deploy.yml/本番scripts を含むと危険PR(ADR-136 GO)。
- 置き場の候補: docs/handoff/outage-recovery-watch/{recon.md,design.md}（worktree内。まだ作っていない）、docs/specs/outage-recovery-watch/（新規テーマの場合）。

## 要点(設計前にPOか設計で決めること)
1. 対策1のメール受け口: 既存IMAP部品は流用可だが、宛先メールボックス(review@ vs <POの業務用メール>)が違う。転送/別IMAP設定が要る。Gmail側の読み取りは本リポジトリに前例なし(IMAPなら Gmailもアプリパスワードで可能という点は【未確認】)。
2. 実行場所: 既存はprod1のCelery。対策1は prod1が落ちる前提の通知なので、prod1以外(prod2 / GitHub Actions cron / Mac)で動かすかを決める必要。
3. 対策2: 現在 up==0 復帰時は「解決」通知のみ。時計ずれの計測値(node_timex_offset_seconds等)は警報にも画面にも無い。実機で出ているか未確認。時刻比較型ルールは prod1 時計ずれで誤警報になりうる(式の事実)。
4. 様式: 新規テーマなら docs/specs/outage-recovery-watch/ 3ファイル+索引1行+docs/handoff recon/design。ai-ops-247 の延長なら既存に追記。
