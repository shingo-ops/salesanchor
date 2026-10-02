# recon: 監視ディスクアラート（PO承認・再発防止策②）

- 対象PR: release/monitoring-disk-alerts（origin/main 由来、PR #3945 マージ後の最新main）
- 背景: 2026-10-02 prod1 ディスクフル障害。`HighDiskUsage` アラートは Prometheus 上で発火していたが、Discordへの通知到達が未確認だった。PO承認の再発防止項目②（監視強化）に対応する。
- 関連ADR: `docs/adr/ADR-080-monitoring-vps-separation.md`（監視スタックの管理室VPS=prod2分離）

## A. アラート配信経路（prod2, 49.212.160.98, 読み取り専用で確認）

### A-1. alertmanager status（webhook URLはマスク済み）

```
{"cluster":{"name":"01KXTZ3TANRW5Z2M5YCTX50P8G","peers":[{"address":"172.18.0.10:9094","name":"01KXTZ3TANRW5Z2M5YCTX50P8G"}],"status":"ready"},"config":{"original":"global:\n  resolve_timeout: 5m\n...\nroute:\n  receiver: discord-server-alerts\n  group_by:\n  - alertname\n  - job\n  - instance\n  continue: false\n  group_wait: 30s\n  group_interval: 5m\n  repeat_interval: 4h\nreceivers:\n- name: discord-server-alerts\n  discord_configs:\n  - send_resolved: true\n    http_config:\n      follow_redirects: true\n      enable_http2: true\n    webhook_url_file: /etc/alertmanager/secrets/discord-webhook\n    title: '{{ template \"discord.default.title\" . }}'\n    message: '{{ template \"discord.default.message\" . }}'\ntemplates: []\n"},"uptime":"2026-07-18T15:56:56.024Z",...}
```

【事実】route は単一（`discord-server-alerts` のみ）。`group_wait=30s` / `group_interval=5m` / `repeat_interval=4h`。inhibit_rules は定義なし（`monitoring/alertmanager/alertmanager.yml:1-11` に該当セクションなし）。

### A-2. 現在のアラート一覧（`/api/v2/alerts`）

```
[{"annotations":{"description":"f2-cleanup.shが8日以上完全成功していない。cron・スクリプト・textfile配線を確認。","summary":"F2掃除係の黒板が8日以上更新なし(app-vps)"},"endsAt":"2026-10-02T15:17:03.599Z","fingerprint":"59d53755e6a8aaa2","receivers":[{"name":"discord-server-alerts"}],"startsAt":"2026-09-21T16:33:03.599Z","status":{"inhibitedBy":[],"mutedBy":[],"silencedBy":[],"state":"active"},"updatedAt":"2026-10-02T15:13:03.604Z","labels":{"alertname":"F2CleanupStale","instance":"app-vps","job":"node-exporter","severity":"critical"}}]
```

【事実】現在発火中は `F2CleanupStale` のみ（`HighDiskUsage` は解消済みのため現在は非発火）。`inhibitedBy`/`mutedBy`/`silencedBy` は全て空配列 = 抑制・ミュート・サイレンスなし。

### A-3. silences（`/api/v2/silences`）

```
[]
```

【事実】サイレンス登録ゼロ。

### A-4. webhook secret ファイル確認

- ホスト（VPS直下）に `test -s /etc/alertmanager/secrets/discord-webhook` を実行 → `missing_or_empty`（host上に該当パスなし。alertmanagerはコンテナ内のため当然）。
- コンテナ内（`docker exec salesanchor-monitoring-alertmanager-1 ...`）で再確認 → `exists_nonempty`。`ls -la` 結果:
```
-rw-r--r--    1 1000     1000           122 Jul 18 15:56 discord-webhook
```
【事実】webhook secret ファイルはコンテナ内の正しいマウント先（`/etc/alertmanager/secrets/discord-webhook`、`docker-compose.monitoring.yml:178` で `./secrets/alertmanager-discord-webhook` をマウント）に存在し、サイズ非ゼロ。

### A-5. 通知メトリクス（`/metrics` 抜粋）

```
alertmanager_notifications_total{integration="discord"} 3077
alertmanager_notifications_failed_total{integration="discord",reason="clientError"} 0
alertmanager_notifications_failed_total{integration="discord",reason="contextCanceled"} 0
alertmanager_notifications_failed_total{integration="discord",reason="contextDeadlineExceeded"} 0
alertmanager_notifications_failed_total{integration="discord",reason="other"} 0
alertmanager_notifications_failed_total{integration="discord",reason="serverError"} 0
```

【事実】discord integration の通知試行は累計3077件、失敗カウンタは全reason=0。これはalertmanagerがDiscordのWebhookエンドポイントへのHTTP送信を試行し、HTTPレベルでエラー（クライアントエラー・サーバーエラー・タイムアウト等）を一度も検知していないことを示す。

### A-6. alertmanagerログ

```
$ docker logs salesanchor-monitoring-alertmanager-1 --since 2026-10-01T00:00:00Z 2>&1 | wc -l
0
```
【事実】2026-10-01以降のログは0行（起動時ログのみ、2026-07-18以降再起動なし）。alertmanagerはデフォルトで通知成功を個別にINFOログしないため、ログ0件は異常を意味しない。

### A-7. 結論（A）

【事実】
- silence/inhibitionによるブロックは無し。
- webhook secretファイルは存在し非ゼロ。
- alertmanager視点でのdiscord通知HTTP送信は過去に3077回試行し失敗0。

【未確認】[?] 2026-10-02 09:00〜11:20 UTCの`HighDiskUsage`発火時に実際にDiscordチャンネルへメッセージが表示されたか（Discord側の受信確認）。alertmanagerのメトリクス・ログからは「送信試行が成功ステータスで完了した」ことまでしか分からず、Discord側での表示・PO視認は本調査の読み取り専用コマンドでは確認不能。

【結論】alertmanager.yml の route/receiver 設定自体に起因する配信失敗の証跡は無い（A-7参照）。既存の単一route（discord-server-alertsのみ・inhibit無し）はCriticalDiskUsageにもそのまま適用されるため、ルーティング変更は不要と判断（design.md参照）。

## B. F2CleanupStale 長期発火の原因（prod1, 49.212.137.46）

### B-1. `/tmp/f2-cleanup.log` tail -60

```
[2026-09-27 04:00:01 JST] === F2 START age=168h target=both ===
[2026-09-27 04:00:01 JST] === F2 START age=168h target=both ===
[2026-09-27 04:00:01 JST] -- exited containers --
[2026-09-27 04:00:01 JST] -- exited containers --
[2026-09-27 04:00:01 JST] -- build cache (until=168h) --
[2026-09-27 04:00:01 JST] -- build cache (until=168h) --
ID						RECLAIMABLE	SIZE		LAST ACCESSED
kriy3ejcfh5b3my3ct038q7rw               	true 		12.74kB   	7 days ago
ID						RECLAIMABLE	SIZE		LAST ACCESSED
kriy3ejcfh5b3my3ct038q7rw               	true 		12.74kB   	7 days ago
Total:	12.74kB
Total:	12.74kB
[2026-09-27 04:00:02 JST] === F2 DONE (FAIL=0) ===
[2026-09-27 04:00:02 JST] === F2 DONE (FAIL=0) ===
```

【事実】直近の cron 実行（2026-09-27 04:00 JST、週次）は `FAIL=0` で正常終了している（ログは`tee`の仕様で各行2回出力されるが内容は同一）。

### B-2. `/home/ubuntu/node_exporter_textfile/` 一覧とファイル内容

```
$ ls -l /home/ubuntu/node_exporter_textfile/
total 4
-rw-r--r-- 1 ubuntu ubuntu 172 Jul 21 10:03 f2_cleanup.prom

$ cat /home/ubuntu/node_exporter_textfile/f2_cleanup.prom
# HELP f2_cleanup_last_success_timestamp F2 cleanup last full-success unix time
# TYPE f2_cleanup_last_success_timestamp gauge
f2_cleanup_last_success_timestamp 1784595829
```

【事実】`.prom`ファイルの最終更新は2026年7月21日10:03 JST（`date -u -d @1784595829` = `2026-07-21T01:03:49Z`）で、2026-09-27の正常終了後も更新されていない。

### B-3. crontab -l

```
# F2 Docker自動クリーンアップ（停止コンテナ＋buildキャッシュ週1）
0 4 * * 0  TZ=Asia/Tokyo bash /home/ubuntu/salesanchor/scripts/f2-cleanup.sh 168 both >> /tmp/f2-cleanup.log 2>&1
```

【事実】cronは `f2-cleanup.sh 168 both` で起動している（`TARGET=both`）。

### B-4. `scripts/f2-cleanup.sh`（origin/main、該当箇所）

```sh
case "$TARGET" in
  both) run_containers; run_cache ;;
  containers) run_containers ;;
  cache) run_cache ;;
  images) run_images ;;
  all) run_containers; run_cache; run_images; write_blackboard ;;
  *) log "UNKNOWN TARGET ${TARGET}"; exit 2 ;;
esac
```
（`scripts/f2-cleanup.sh:73-80`。`write_blackboard` 関数定義は `scripts/f2-cleanup.sh:59-71`）

【事実】`write_blackboard`（黒板=`.prom`ファイル更新）は `case` 文の `all)` 分岐でのみ呼ばれる。crontabが実行する `both` 分岐では `run_containers; run_cache` のみが実行され、`write_blackboard` は一度も呼ばれない。

### B-5. 結論（B）

【事実】`f2_cleanup.prom` が2026-07-21以降更新されない原因は、`scripts/f2-cleanup.sh` の `case "$TARGET"` 分岐バグ（`both`ターゲットでは`write_blackboard`が呼ばれない）であり、crontabが常に`both`で起動している以上、週次cronでは黒板メトリクスが永久に更新されない。2026-07-21以前に誰かが手動で`all`ターゲット（または直接`write_blackboard`相当の操作）を実行した時のタイムスタンプが残存していたと推測されるが、その手動実行の記録は本調査の範囲外。

【未確認】[?] アラートの`startsAt`が2026-09-21T16:33:03Zである理由（ファイル更新停止は7/21なのに発火開始が9/21）。可能性としてPrometheus/alertmanagerの再構築（ADR-080 管理室VPS分離）タイミングと一致する可能性があるが、本調査では確認していない。

【方針】本バグは本番運用スクリプト（`scripts/f2-cleanup.sh`）の修正が必要だが、このPRでは修正しない（別途GOが必要な本番スクリプト変更のため）。上記エビデンスを引き継ぎ資料として記録するのみ。
