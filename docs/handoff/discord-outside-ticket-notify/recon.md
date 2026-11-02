# Discord「チケット部屋の外の投稿」担当者通知 — 事前調査（recon）

この文書は何か: 顧客が自分のチケット部屋の外（共有チャンネル）に書いた投稿は受信箱に入らない。PO 決定は「顧客には何も返さず、担当者にだけ Discord で知らせる」。その設計の前提になる事実を集めた調査。製品コードは変えていない。
調査日: 2026-11-02 / 起点: origin/main b88ff157b
凡例: 【観測】= コードを読んで確認した事実 / 【未確認】= 読んでいない・本番の値に依存する。
注意: 顧客の投稿本文・チャンネル id・トークン・webhook URL は書いていない。パスは `backend/app/...` のリポジトリ相対（フルパスの根は作業場所 `/root/worktrees/salesanchor/release-discord-outside-ticket-recon/`）。

## ① チケット部屋か否かの判定と、外を捨てている箇所

【観測】
- 受信の入口は `backend/app/discord_gateway/client.py:394` `on_message`。bot 発言は :400-401 で捨てる。DM（guild なし）は :402-405 で捨てる（ADR-146 B方式の対象外と書いてある）。guild の発言は `_process_guild_message`（:408）へ。
- `_process_guild_message` は guild_id から tenant_id を逆引きし（:410-411。引けない guild は :412-417 でログだけ出して捨てる）、`ticket_channel_writer.process_ticket_channel_message` に渡す（:420）。例外は握ってログだけ（:427-434）。
- **「部屋の外を捨てている箇所」の正体**: `backend/app/discord_gateway/ticket_channel_writer.py:145` `process_ticket_channel_message` が、投稿のあったチャンネルを `leads.discord_guild_channel_id` と突き合わせる（`_lookup_ticket_channel_lead` :115-142、条件は :128）。該当 lead が無い（＝チケット部屋ではない）と :185-192 で warning を 1 行出して `return True`。**ここが捨てる点**。受信箱（meta_messages）にも何にも書かれない。
- 同関数内のそのほかの捨て方: bot/webhook 発言 :194-201、部屋の持ち主（lead の discord_user_id）以外の発言 :203-211（部屋の中の担当者発言など）。
- 「チケット部屋か」の判定は専用の関数ではなく、「そのチャンネル id を持つ lead が居るか」という引き当てそのもの。チケット部屋かどうかを持つ別の表・フラグは見つけていない。
- Gateway が受ける intent: guilds / guild_messages / message_content / members / reactions（`client.py:71-75`）。投稿本文を読める権限はすでに有効。

【未確認】
- 共有チャンネルの投稿が Discord 側で bot に届く権限（チャンネルごとの閲覧許可）が本番で付いているか。コード上は guild 全体の MESSAGE_CREATE が `on_message` に来る前提。
- 本番で :185 の warning がどれくらいの頻度で出ているか（ログ未確認）。

## ② 顧客かどうか（lead/顧客・サーバー参加者）の判定方法と正本

【観測】
- 顧客の正本は各テナント schema の `leads`（`tenant_NNN.leads`）。Discord の人との紐付け列は `leads.discord_user_id`（VARCHAR(50)。`migrations/091_add_leads_discord_messaging_columns.sql:30`、索引 :35-39）と、部屋の紐付け列 `leads.discord_guild_channel_id`（`migrations/20260602_120000_add_discord_ticket_config.sql:35`、索引 :39-41）。
- discord_user_id から lead を引く既存の関数: `backend/app/discord_gateway/ticket_channel_creator.py:90-110` `_get_lead_state`（SELECT は :96-102）、:65-87 `_get_existing_channel_id`。どちらも `WHERE discord_user_id = :uid LIMIT 1`。lead は部屋発行ボタン押下時に無ければ作られる（:461-531 付近）。
- つまり「共有チャンネルで書いた人が顧客か」は、投稿者の `author.id` を `leads.discord_user_id` で引ければ顧客（lead あり）、引けなければ未登録。ボタンを押して部屋を作った人だけが lead になる点に注意（ボタンを押さずに参加しただけの人は lead が無い）【観測】。
- 担当者側の正本: `tenant_NNN.staff.discord_user_id`（`migrations/019_create_staff_tables.sql:47`、UNIQUE(tenant_id, discord_user_id) :55）。担当者の投稿を顧客扱いしないための除外に使える。
- サーバー参加者そのものを入れた表は見つけていない。参加者の取得は Gateway の `guild.get_member`（`ticket_channel_creator.py:221`）や REST（`backend/app/services/discord_role_sync.py:219`）を都度呼ぶ形。
- テナントの逆引き: `public.tenant_discord_config`（tenant_id PK・guild_id、`migrations/099_add_discord_guild_config.sql:6-11`、guild_id UNIQUE は `migrations/20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql`）。引く処理は `client.py:101-127`。
- チケット設定: `public.tenant_discord_ticket_config`（ticket_category_id / ticket_button_channel_id / staff_role_id / welcome_template、`migrations/20260602_120000_add_discord_ticket_config.sql:5-12`）。

【未確認】
- 共有チャンネルの投稿者が lead でも staff でもない人（顧客候補・閲覧者・外部の人）の扱い。閲覧者（viewer）アカウントは別系統（ADR-1019、`backend/app/discord_gateway/viewer_trial.py`）で、`leads` とは別の表と思われるが、判定に使う列は読んでいない。
- 1 人の discord_user_id が複数 lead に紐付く場合の挙動（`LIMIT 1` で任意の 1 件になる。UNIQUE かは確認していない）。

## ③ 担当者へ Discord で知らせる既存の仕組み

【観測】3 系統ある。
1. **テナント別 webhook（受信箱運用向けの本命候補）**: 表 `tenant_NNN.notification_channels`（`migrations/009_add_phase4_tenant_tables.sql:8-18`。列: channel_name / webhook_url / event_types（JSON 配列の文字列）/ is_active）。ログは `notification_logs`（同 :22 以降）。登録・更新・削除は `backend/app/routers/notifications.py:83` / :106 / :139、種類の一覧は :67。
   - 送信関数 `backend/app/routers/notifications.py:153` `send_discord_notification(db, tenant_id, event_type, title, message, mention_user_ids)`。照合は `tenant_id` 条件 + `is_active` + `event_types LIKE '%種類%'`（:160-163）。メンションは content に置き `allowed_mentions` で指定した人だけ鳴らす（:170-175）。結果は notification_logs に残す（:178-185）。
   - 種類の SSOT は `backend/app/schemas/notification.py:8-22` の `NotificationEventType`（現在 lead_assigned / meta_message_received / tcg_distribution_error）。**部分一致で照合するため、新しい種類は既存の値の部分文字列にしない**（同ファイルの docstring に明記。試験 `backend/tests/test_notification_event_routing.py:125`）。
   - 既存の使い手: 担当アサイン通知 `backend/app/services/lead_assign_notifier.py:22-63`（staff.discord_user_id で担当者にメンション :43-45、顧客名で知らせる :50-56）、Meta 新着通知 `backend/app/routers/webhook.py:938-947`（送信者 ID を伏せる作法あり）。
   - webhook_url は notification_channels に平文の VARCHAR(500) で保存【観測】（暗号化の記述なし）。AI 向けビューでは伏せ対象（`migrations/20261024_100300_create_ai_cloud_views.sql:454-456`）。
   - テナント別の扱い: テナント schema の表のため、テナントごとに別 webhook を持てる。呼ぶ側は `set_tenant_context` 必須（`lead_assign_notifier.py:25-28` が手本）。
2. **Bot 経由で部屋に送る**: `backend/app/services/viewer_room_notice.py:30` `send_room_notice(channel_id, text)`（環境変数の Bot トークンで REST 送信。失敗しても例外を外に出さない）。REST の共通層は `backend/app/services/discord_rest.py`（429/5xx の再試行）。**送り先チャンネルを DB に持つ仕組みは別途必要**（既存の保存先は上記 1 の webhook か、チケット設定の部屋 id のみ）。
3. **担当者名義の webhook 送信（ADR-159）**: `backend/app/services/discord_webhook_sender.py`。チャンネルごとの webhook を作って暗号化（Fernet）して保管し、担当者名・アイコンで送る。顧客への返信用で、**担当者への社内通知用ではない**。顧客に何も返さない今回の方針とは用途が違う。
4. 中央運用者向け（テナントではない）: `backend/app/services/discord_notifier.py`（環境変数の webhook。予算超過など）。テナント別ではない。

【未確認】
- 本番で `notification_channels` に Discord 通知先が登録済みのテナントがあるか、どの種類を受けているか。
- 画面側（frontend）の通知先登録 UI の有無・場所（今回は frontend を読んでいない）。
- 「担当者」を誰にするか（lead の担当 `assigned_to` は ③-1 の lead_assigned で使っている。共有チャンネルの投稿者が lead でない場合は担当が無い。staff_role_id へのロールメンションが使えるかは未確認）。

## ④ 関連 ADR と docs/specs

【観測】
- `docs/adr/ADR-009-discord-gateway.md`（Gateway・受信箱の基盤）、`docs/adr/ADR-091-discord-bot-scope-definition.md`（Bot の権限範囲・ticket-start・チケット機能。KPI3 でチケット設定表を追加）、`docs/adr/ADR-098-sa-multi-channel-identity-resolution.md`（Discord は guild_id / channel_id を ID の正本とする）、`docs/adr/ADR-159-staff-identity-on-discord.md`（担当者名義の送信）、`docs/adr/ADR-1009-discord-ops-intake.md`（運用者向けの監視通知。顧客投稿とは別件）、`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md`（閲覧者の別アカウント）。
- `docs/adr/FEATURE-INDEX.md:18-20,49` に Discord 関連の行（在庫の Discord 収集 ADR-100 / ADR-1050、担当者名義 ADR-159）。「チケット部屋の外」を直接扱う行は見つけていない。
- ADR-146（B方式・共通 bot 1 台＋guild_id 振り分け）はコードのコメント（`client.py:1`）には出るが、`docs/adr/` に ADR-146 のファイルは見つからなかった。`git grep -i discord docs/adr` の一覧にも出ない【観測】。
- docs/specs: `docs/specs/discord-ops-intake/`（README / kgi / ideal-state / delegation）、`docs/specs/discord-reaction/`、`docs/specs/inbox/ideal-state.md`（受信箱の理想形。Discord は連携対象に挙がる）。部屋の外の投稿を扱う spec は見つけていない。
- 手引き: `docs/handoff/discord-guild-channel-only/recon.md`・`design.md`（受信箱の Discord 送信先をチケット専用チャンネルのみに絞った経緯。「受信箱に入るのは部屋の中だけ」の土台）、`docs/handoff/discord-ticket-gateway-visibility/`。

【未確認】
- 「部屋の外は受信箱に入れない」を PO が明文化した ADR があるか（FEATURE-INDEX・ADR 本文ともに該当行は見つからず）。新規 ADR が要るかは設計担当の判断。

## ⑤ 既存の試験

【観測】
- 部屋の書き込み: `backend/tests/test_ticket_channel_translation.py:116`（部屋の顧客投稿が保存され翻訳が積まれる）、:156（顧客以外の発言は commit も翻訳もしない）。**部屋の外（lead 無し）を直接検査する試験は見つけていない**。
- 部屋の発行・復旧: `backend/tests/test_discord_ticket_channel.py`、`test_discord_ticket_channel_delete_restore.py`、添付 `test_discord_ticket_attachment.py`。
- 通知: `backend/tests/test_notification_event_routing.py`（種類が互いに部分文字列でない :125、tenant 別に 1 件だけ送る :365、担当アサイン通知の中身・メンション :313-472）。
- webhook 名義送信: `backend/tests/test_discord_webhook_sender.py`（再試行・token をログに出さない等）。
- そのほか Discord 全般: `test_discord_inbox.py`、`test_discord_d2.py`、`test_discord_gateway_alive.py`、`test_discord_gateway_reconnect.py`。
- on_message / `_process_guild_message`（`client.py:394,408`）自体を直接叩く試験は見つけていない【未確認。上記 grep 範囲では未検出】。

## ⑥ 重複通知・連投の抑止の既存例

【観測】3 通りの前例がある。
1. **DB の時刻列＋1 文の UPDATE（競合しない）**: `backend/app/services/discord_notifier.py:146-148`（1 時間の窓）と :212-235 `_try_debounce_acquire`（`UPDATE ... WHERE last_hard_stop_notified_at IS NULL OR < NOW() - 窓 RETURNING`、返った行があれば今回が通知の番）。送信失敗時は :208 で解除して再試行可能に戻す。docstring :18 は「本サービス内では rate limit を入れない」と呼び出し側責務を明記。
2. **クールダウン列**: `backend/app/services/buyback_scraper/alert_checker.py:29,44-48,124-128`（`last_notified_at` と `cooldown_minutes`）。
3. **Redis のキー＋TTL**: `backend/app/discord_gateway/viewer_interview_notice.py:4,38,84-86,102`（キー `viewer_interview_notice:{id}:{日付}`、送れたときだけ TTL 30 日で置く。Redis が使えないときは誰にも送らない :67）。Gateway プロセス内から使える形の前例。
- メッセージ単位の重複排除（同じ投稿を二重に取り込まない）は `meta_messages.message_id` の `ON CONFLICT DO NOTHING`（`ticket_channel_writer.py:225-226`、重複時の分岐 :246-253）。再接続や再送で同じ MESSAGE_CREATE が来ても二重に保存されない。通知側にはこの仕組みは無い。

【未確認・設計で決める点】
- 共有チャンネルは投稿者ごとに連投されうる。抑止の単位（投稿者ごと／チャンネルごと／テナントごと）と窓の長さは未決。1 の方式は tenant 単位の列しか持たないため、投稿者単位にするなら新しい置き場（表または Redis キー）が要る。
- Gateway 再起動・再接続時に直近の投稿が再配信されるかは未確認（保存側は message_id で守られているが、通知側は別途要る）。

## 設計担当への要点（事実からの示唆。判断は設計担当）
- 差し込み位置の候補は `ticket_channel_writer.py:185-192`（lead 無し＝部屋の外の分岐）。ここは今、warning だけで抜けている。
- 担当者への通知は既存の `send_discord_notification`（③-1）を使えば、テナント別・メンション・ログ・テナント越境の防御がそのまま付く。新しい種類は `NotificationEventType` へ追加し、既存値の部分文字列にしないこと（試験 :125 が守る）。
- 通知文に顧客の投稿本文を載せるかは未決。Meta 通知は送信者 ID を伏せる作法（`webhook.py:938-947`）で本文は載せていない。
- 顧客へは何も返さないので、送信系（③-2・③-3）は使わない。
