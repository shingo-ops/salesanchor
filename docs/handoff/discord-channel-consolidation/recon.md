# recon: Discord の知らせのチャンネルを種類別にまとめる

調べた日時: 2026-11-21 16:30〜17:35 JST（読むだけ。何も変えていない）。生の記録は Mac の `/tmp/CC報告ファイル/discord-channels/`（鍵の値は 0 件）。

## 1. 既存 ADR
- `git grep -i discord docs/adr/` と `docs/adr/FEATURE-INDEX.md` で探した。
- `docs/adr/ADR-1039-discord-pdca-agent-console.md:24` 不具合の受け口は「不具合受付」と「誤り報告」のチャンネルを読む。
- `docs/adr/ADR-1039-discord-pdca-agent-console.md:34` 前の受付（ADR-1009）はやめる。
- チャンネルの分け方を決めた ADR は無い。

## 2. Sales Anchor サーバー（guild 1515681337158271187）のアラート分類
Bot（Sales Anchor）で `/guilds/{id}/channels`・`/guilds/{id}/webhooks` を読んだ（guild-table.txt）。

| チャンネル | id | 送り口(webhook) | 30日の件数 |
|---|---|---|---|
| サーバー監視アラート | 1527986848490717245 | サーバー監視 1528064418448146552・さくらのお知らせ 1564456788999405721 | 1642 |
| approval-test | 1559254677768380537 | approval-test 1559254844735361134・Spidey Bot 1559254822434250852 | 905 |
| 運用アラート | 1560490429995294760 | 運用アラート 1560490555471827074 | 38 |
| 画面点検調査報告 | 1544914659595915325 | API接続障害 1544914720987807804 | 19 |
| 不具合受付 | 1562450200499593226 | なし | 2 |
| 不具合報告 | 1562448371875188736 | 不具合報告 1562448510849257612 | 0 |
| 検証用サーバーのテストチャンネル | 1559230296975474959 | Captain Hook 1559230387799068754 | 0 |

## 3. 送り手と送り口（webhook の GET で channel_id を確かめた）
- 監視サーバーの alertmanager（`monitoring/alertmanager/alertmanager.yml:17-34`・secret ファイル）→ サーバー監視。全部の見張りの発火と解消を 1 か所へ送る。
- 本番アプリ `DISCORD_WEBHOOK_URL`・`DISCORD_WEBHOOK_OPS` → サーバー監視。`OPS_MAIL` → さくらのお知らせ。`ADMIN_NOTIFICATION_DISCORD_WEBHOOK` → 運用アラート。`ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK` は空。
- GitHub の `DISCORD_WEBHOOK_SCHEDULED_REPORT`（週次・月次の 13 本。`.github/workflows/weekly-stale-pr.yml:19` ほか）→ サーバー監視に届いている（投稿の題で確認）。
- GitHub の `DISCORD_WEBHOOK_OWNER_PING` → API接続障害。使う所は失敗のときだけ: 画面点検の不合格 `.github/workflows/prod-ui-check.yml:134-135`、反映の止まり・戻し `.github/workflows/deploy.yml:211,986,999`。
- Mac の `~/.config/sa-ops-intake/watchdog-webhook` → approval-test。使う所: `scripts/mac-jobs-watch.sh:29`、前の受付の番人、kb 見回り。
- `DISCORD_WEBHOOK_PR`・`DISCORD_WEBHOOK_CI`・`DISCORD_WEBHOOK_PLAN_REVIEW`・本番の `REVIEW_MAIL_DISCORD_WEBHOOK`: Sales Anchor サーバーの送り口に無い。REVIEW_MAIL は別のサーバー（guild 1288437029213835356）と確認。Bot が入っていないので中は未確認。

## 4. 30 日の中身（hist30-summary.txt）
- サーバー監視アラート 1642: ログイン失敗の発火・解消 1442（88%）、他の見張り約 190、週次の報告 約 30、Uptime Kuma 8、さくら 1。
- approval-test 905: 「受付停止: tmux セッション sa-ops-intake がありません」716。前の受付の番人（`~/Library/LaunchAgents/jp.salesanchor.ops-intake-watchdog.plist`・5 分ごと・1 時間に 1 通）が、やめた受付を 37 日（heartbeat 3181361 秒）見張り続けている。残り: Mac の起動後の点検 129、Mac の異常と復旧 55、kb 見回り 4、その他 1。
- 運用アラート 38: アプリの毎日・毎週の点検。
- 画面点検調査報告 19: 画面点検の不合格 14、反映の前の点検で止めた 4、FedEx の失敗 1（全部失敗の知らせ）。

## 5. チャンネルを読む仕組み
- agent-console の不具合の受け口: `~/Library/Application Support/agent-console/discord-intake.config.json` は 不具合受付 1562450200499593226 だけを読む。
- 前の受付の設定 （Mac のホームの .claude/channels/discord-ops/access.json・リポジトリの外） はサーバー監視アラートの id を持つが、受付は動いていない（tmux に sa-ops-intake が無い）。
- id を変えなければ読む側は直さなくてよい。

## 6. Bot の権限（bot-perm.txt）
- Sales Anchor Bot: チャンネルの管理 ○、送り口の管理 ○、管理者 ×。チャンネルの名前の変更と送り口の付け替えは Bot でできる（チャンネルごとの上書きで止められる場合は実行時に分かる）。
