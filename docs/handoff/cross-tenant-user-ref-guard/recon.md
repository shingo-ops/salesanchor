# recon: 他社の人の番号が入る道と、会社番号を設定する全呼び出しの確かめ

- 基準: origin/main c481f5e7d（git archive で取り出した写しを読んだ）
- 調べた日: 2026-11-06
- 前段: docs/handoff/master-shared-tenant-rule/recon.md「追記: 他社に届く道 1件の確かめ」「追記2: 全体の洗い出し」（PR #5155 のブランチ）

## 0. 既存 ADR の検索

- ADR-1008（会社に属さない担当者を入れない。前例: backend/app/routers/companies.py:357 `_ensure_sales_rep_in_tenant`）
- ADR-072（commit 後に reset_tenant_context を呼ぶ）
- ADR-146（Discord は共通 bot 1台・guild_id から会社を引く）
- 前例2: backend/app/routers/notice_fallback_recipients.py:94-101（受け取る人の番号を `tenant_id = :tid AND is_active` で照合してから保存）

## 1. 他社に届く道（確定 1件。2件目は 6-1 で取り消し）

| # | 場所 | 何が起きるか | 見えるもの |
|---|---|---|---|
| 1 | backend/app/routers/leads.py:405-459（作成）・:578-596（更新）の assigned_to | 会社の照合なしで任意の人の番号を保存できる。本番の leads は外部キー0件（AUDIT ts=2026-11-06T06:40:42Z sha=ad3eddf9b8d9 rows=0） | backend/app/routers/analytics.py:110-119 が public.users を結ぶため、他社の人のユーザー名が集計に出る |
| ~~2~~（取り消し・6-1） | backend/app/routers/badges.py:99-117（付与・badges.manage 権限）→ :82-95（順位表 `LEFT JOIN public.users u ON u.id = ub.user_id`） | 会社の照合なしで任意の人の番号にバッジを付けられる。user_badges の user_id は5区画とも外部キーなし（読み取りの道で確認） | 順位表に他社の人のユーザー名が出る |

1件目で見えるのは他社の人のユーザー名だけで、他社の商談・顧客・金額は出ない。

## 2. 届かないと確かめた候補（4件）

- backend/app/routers/tenant_policy.py:104-127: 書ける項目は backend/app/schemas/tenant_policy.py:26-34 の8項目だけ
- backend/app/routers/meta.py:225-270: 返すのは状態だけ。番号は token_hex(4)
- backend/app/routers/webhook.py:265-294: 処理の前に署名を照合（:270-284）
- backend/app/services/inventory_movements.py:23: 呼び出し元0件

## 3. 会社番号を設定する全呼び出し（「約50か所」の確かめ）

### 3-1. 数え方

- 道具: tenant-context-calls.tsv を作った scan_tenant_context.py（Python の構文木で数える。文字の検索では reset_tenant_context を重ねて数えたため使わない）
- 対象: backend/app の set_tenant_context・set_tenant_context_sync・reset_tenant_context の呼び出し全部
- 最初の「約50か所」は、クラウドの調査が set_tenant_context だけを文字で数えた数。数え直すと全部で 268 件

| 区分 | 件数 | 判定 |
|---|---|---|
| A: 会社番号がログインの札から来る（引数が Depends(get_current_tenant)、または Depends(get_current_user) の current_user.tenant_id） | 186（戻す呼び出し 176・設定 10） | 機械で判定済み。他社の番号は入らない |
| B: 機械では判定できない（下の 3-2 で1件ずつ読んだ） | 82 | 3-2 の表 |
| 合計 | 268 | 全件の一覧は tenant-context-calls.tsv |

### 3-2. B の 82 件の判定（全件）

結論: 82 件すべて、会社番号は「ログインの会社」「署名や合言葉を照合した外部の通知」「一意の対応表」「全社を1社ずつ回す定期作業」「運営だけの窓口」のどれかから来る。依頼の中身から他社の番号を選べる呼び出しは 0 件。

確かめの方法: 各呼び出しの関数を構文木で特定し、会社番号の変数がどこで作られるか、引数なら呼び出し元を全部（grep・作業名の文字列も含む）たどった。

| 記号 | 件数 | 会社番号の出どころ |
|---|---|---|
| login | 8 | ログインの入口: 会社番号は、合言葉・パスキー・再設定の鍵・待ち札で見つけた本人の行から取る（auth.py の各関数） |
| superadmin | 3 | 運営だけの窓口: require_super_admin（会社を選ぶのは運営） |
| oauth | 6 | 外部連携の戻り口: 開始時に Depends(get_current_tenant) で決め、Redis に1回だけ使える札で保存 |
| paypal | 6 | PayPal の戻り口・通知: Fernet 署名札、または会社ごとの鍵で署名を照合してから設定 |
| regtoken | 7 | 顧客登録の札: 会社番号は public.registration_tokens の行（札は HMAC の写しで照合・期限・使用済みを確認。発行はログインの会社） |
| meta | 9 | Meta の通知: HMAC-SHA256 署名を先に照合し、ページ番号→会社の対応表で決める |
| gcal_hook | 3 | Google 予定: 通知は X-Goog-Channel-Token の sha256 を会社ごとの行と照合（verify_channel）。定期取り込みは全社を1社ずつ回す |
| discord | 9 | Discord の受信: guild_id→会社の対応表（guild_id は一意制約付き）で決める（client._resolve_tenant_id） |
| unused | 2 | 呼び出し元0件（関数名・作業名とも app 内に呼ぶ所なし） |
| loop | 9 | 定期作業: 全社の一覧を読み、1社ずつその会社の番号を設定して回す |
| login_arg | 20 | 引数で受ける部品: 呼び出し元を全部たどった。どれもログインの会社（Depends(get_current_tenant)・current_user.tenant_id）か、上の署名・対応表で決めた会社か、運営向け通知の固定の会社4 |

合計 82 件

#### 全件

| # | 場所（backend/app/） | 呼び出し | 関数 | 会社番号 | 判定の根拠 |
|---|---|---|---|---|---|
| 1 | routers/auth.py:294 | set_tenant_context | _record_auth_audit | tenant_id | login |
| 2 | routers/auth.py:313 | set_tenant_context | _count_login_failure | user_row.tenant_id | login |
| 3 | routers/auth.py:475 | set_tenant_context | self_login | user_row.tenant_id | login |
| 4 | routers/auth.py:686 | set_tenant_context | password_reset_confirm | user_row.tenant_id | login |
| 5 | routers/auth.py:784 | set_tenant_context | password_change | user_row.tenant_id | login |
| 6 | routers/auth.py:1171 | set_tenant_context | passkey_login_verify | cred.tenant_id | login |
| 7 | routers/auth.py:1356 | set_tenant_context | _complete_pending_login | user_row.tenant_id | login |
| 8 | routers/auth.py:1498 | set_tenant_context | login_request_ask_admin | info.tenant_id | login |
| 9 | routers/auth.py:124 | set_tenant_context | register_user | tenant.id | superadmin |
| 10 | routers/auth.py:153 | set_tenant_context | register_user | tenant.id | superadmin |
| 11 | routers/tcg_product_import.py:498 | reset_tenant_context | delete_product_detail | (なし) | superadmin |
| 12 | routers/discord_oauth.py:215 | set_tenant_context | discord_oauth_callback | tenant_id | oauth |
| 13 | routers/discord_oauth.py:249 | reset_tenant_context | discord_oauth_callback | tenant_id | oauth |
| 14 | routers/google_calendar.py:126 | set_tenant_context | connect_callback | tenant_id | oauth |
| 15 | routers/google_calendar.py:147 | reset_tenant_context | connect_callback | tenant_id | oauth |
| 16 | routers/integrations.py:128 | set_tenant_context | connect_callback | result['tenant_id'] | oauth |
| 17 | routers/integrations.py:157 | reset_tenant_context | connect_callback | result['tenant_id'] | oauth |
| 18 | routers/integrations.py:771 | set_tenant_context | paypal_return | tenant_id | paypal |
| 19 | routers/integrations.py:816 | reset_tenant_context | paypal_return | tenant_id | paypal |
| 20 | routers/integrations.py:926 | set_tenant_context | _handle_invoice_paid | tenant_id | paypal |
| 21 | routers/integrations.py:965 | reset_tenant_context | _handle_invoice_paid | tenant_id | paypal |
| 22 | routers/integrations.py:1015 | set_tenant_context | _handle_dispute | matched_tenant | paypal |
| 23 | routers/integrations.py:1048 | reset_tenant_context | _handle_dispute | matched_tenant | paypal |
| 24 | routers/registration_tokens.py:186 | set_tenant_context | verify_registration_token | tenant_id | regtoken |
| 25 | routers/registration_tokens.py:235 | set_tenant_context | register_customer | tenant_id | regtoken |
| 26 | routers/registration_tokens.py:352 | reset_tenant_context | register_customer | tenant_id | regtoken |
| 27 | routers/registration_tokens.py:388 | set_tenant_context | add_address | tenant_id | regtoken |
| 28 | routers/registration_tokens.py:441 | reset_tenant_context | add_address | tenant_id | regtoken |
| 29 | routers/registration_tokens.py:483 | set_tenant_context | change_billing | tenant_id | regtoken |
| 30 | routers/registration_tokens.py:563 | reset_tenant_context | change_billing | tenant_id | regtoken |
| 31 | routers/webhook.py:638 | reset_tenant_context | _persist_meta_message | tenant_id | meta |
| 32 | routers/webhook.py:676 | reset_tenant_context | _persist_meta_message | tenant_id | meta |
| 33 | routers/webhook.py:690 | reset_tenant_context | _persist_meta_message | tenant_id | meta |
| 34 | routers/webhook.py:701 | reset_tenant_context | _persist_meta_message | tenant_id | meta |
| 35 | routers/webhook.py:743 | reset_tenant_context | _persist_meta_message | tenant_id | meta |
| 36 | routers/webhook.py:805 | set_tenant_context | process_messenger_event | tenant_id | meta |
| 37 | routers/webhook.py:844 | reset_tenant_context | process_messenger_event | tenant_id | meta |
| 38 | routers/webhook.py:889 | reset_tenant_context | process_messenger_event | tenant_id | meta |
| 39 | tasks/avatar.py:232 | set_tenant_context_sync | fetch_avatar_for_lead | tenant_id | meta |
| 40 | services/google_webhook.py:255 | set_tenant_context | sync_tenant_from_google | tenant_id | gcal_hook |
| 41 | services/google_webhook.py:278 | set_tenant_context | sync_tenant_from_google | tenant_id | gcal_hook |
| 42 | services/google_webhook.py:362 | reset_tenant_context | sync_tenant_from_google | tenant_id | gcal_hook |
| 43 | discord_gateway/outside_ticket_notice.py:85 | reset_tenant_context | _recover_session | tenant_id | discord |
| 44 | discord_gateway/outside_ticket_notice.py:104 | reset_tenant_context | _create_bell | tenant_id | discord |
| 45 | discord_gateway/ticket_channel_creator.py:259 | set_tenant_context | _clear_lead_channel_id | tenant_id | discord |
| 46 | discord_gateway/ticket_channel_creator.py:292 | set_tenant_context | restore_after_ticket_deleted | tenant_id | discord |
| 47 | discord_gateway/ticket_channel_creator.py:362 | set_tenant_context | reconcile_deleted_ticket_channels | tenant_id | discord |
| 48 | discord_gateway/ticket_channel_creator.py:423 | set_tenant_context | _send_welcome | tenant_id | discord |
| 49 | discord_gateway/ticket_channel_creator.py:467 | set_tenant_context | get_or_create_ticket_channel | tenant_id | discord |
| 50 | discord_gateway/ticket_channel_creator.py:507 | set_tenant_context | get_or_create_ticket_channel | tenant_id | discord |
| 51 | discord_gateway/ticket_channel_writer.py:180 | set_tenant_context | process_ticket_channel_message | tenant_id | discord |
| 52 | discord_gateway/dm_writer.py:94 | set_tenant_context | upsert_lead_and_message | tenant_id | unused |
| 53 | discord_gateway/dm_writer.py:133 | set_tenant_context | upsert_lead_and_message | tenant_id | unused |
| 54 | services/google_webhook.py:404 | set_tenant_context | renew_expiring_webhooks | tenant_id | loop |
| 55 | services/translation_monitor.py:59 | set_tenant_context | check_translation_health | tenant_id | loop |
| 56 | tasks/avatar.py:301 | set_tenant_context_sync | refresh_all_avatars | tenant_id | loop |
| 57 | tasks/dashboard.py:51 | set_tenant_context_sync | _compute_kpis | tenant_id | loop |
| 58 | tasks/google_calendar_sync.py:44 | set_tenant_context | _run_all | tenant_id | loop |
| 59 | tasks/maintenance.py:127 | set_tenant_context_sync | archive_audit_logs | tenant_id | loop |
| 60 | tasks/refresh_meta_tokens.py:381 | set_tenant_context_sync | _process_tenant | tenant_id | loop |
| 61 | tasks/sa02_recon_monitor.py:70 | set_tenant_context | _run_daily_recon | tenant_id | loop |
| 62 | tasks/verify_meta_subscriptions.py:251 | set_tenant_context_sync | _process_tenant | tenant_id | loop |
| 63 | routers/conv_logs.py:152 | set_tenant_context | _fire_translation | tenant_id | login_arg |
| 64 | routers/conv_logs.py:175 | reset_tenant_context | _fire_translation | tenant_id | login_arg |
| 65 | routers/notice_fallback_recipients.py:116 | reset_tenant_context | put_notice_fallback_recipients | tenant_id | login_arg |
| 66 | routers/notifications.py:198 | reset_tenant_context | send_discord_notification | tenant_id | login_arg |
| 67 | routers/tenant_commission_settings.py:106 | reset_tenant_context | _create_default | tenant_id | login_arg |
| 68 | services/calendar_service.py:272 | reset_tenant_context | create_event | tenant_id | login_arg |
| 69 | services/calendar_service.py:366 | reset_tenant_context | update_event | tenant_id | login_arg |
| 70 | services/calendar_service.py:405 | reset_tenant_context | update_event | tenant_id | login_arg |
| 71 | services/calendar_service.py:413 | reset_tenant_context | update_event | tenant_id | login_arg |
| 72 | services/calendar_service.py:425 | reset_tenant_context | _save_meet_url | tenant_id | login_arg |
| 73 | services/calendar_service.py:488 | reset_tenant_context | delete_event | tenant_id | login_arg |
| 74 | services/discord_webhook_sender.py:175 | reset_tenant_context | _store_webhook | tenant_id | login_arg |
| 75 | services/discord_webhook_sender.py:185 | reset_tenant_context | _delete_webhook | tenant_id | login_arg |
| 76 | services/google_calendar.py:294 | reset_tenant_context | _refresh_if_needed | tenant_id | login_arg |
| 77 | services/google_drive_oauth.py:319 | reset_tenant_context | _refresh_if_needed | tenant_id | login_arg |
| 78 | services/google_webhook.py:139 | reset_tenant_context | register_webhook | tenant_id | login_arg |
| 79 | services/google_webhook.py:195 | reset_tenant_context | stop_webhook | tenant_id | login_arg |
| 80 | services/lead_assign_notifier.py:25 | set_tenant_context | notify_lead_assigned | tenant_id | login_arg |
| 81 | tasks/reports.py:204 | set_tenant_context_sync | export_csv | tenant_id | login_arg |
| 82 | tasks/translation.py:79 | set_tenant_context | _run_translate_inbound_message | tenant_id | login_arg |


補足:
- unused の2件は backend/app/discord_gateway/dm_writer.py:94・:133。Discord の個別メッセージは ADR-146 で対象外となり、呼ぶ所が無い
- backend/app/tasks/dashboard.py の refresh_tenant_kpi（作業名 app.tasks.dashboard.refresh_tenant_kpi）も、app 内に呼ぶ所が無い。会社番号を引数で受けるので、将来呼ぶときは呼び出し元の確かめが要る
- backend/app/routers/tcg_product_import.py:498 は会社番号を渡さずに戻す（＝空にする）。運営だけの窓口で、共用の商品を消した後の片付け
- backend/app/routers/auth.py:124・:153 register_user は運営だけ。会社を選ぶのは運営
- 運営向け通知の固定の会社4: backend/app/tasks/viewer_inventory_cache.py:63・backend/app/services/tcg_distribution_svc.py:1159（どちらも send_discord_notification を tenant_id=4 で呼ぶ）

## 4. 対応表を書く窓口の確かめ（3-2 の前提）

3-2 の「一意の対応表」が正しいのは、対応表に他社の外部アカウントを書けないときだけ。書く窓口を読んだ。

| 対応表 | 書く窓口 | 会社番号 | 外部の番号の出どころ | 判定 |
|---|---|---|---|---|
| public.tenant_discord_config（Discord のサーバー番号） | backend/app/routers/discord_oauth.py:215-235（連携の戻り口） | Redis の1回札（開始は Depends(get_current_tenant)） | Discord の連携の応答 | 持ち主の証明あり |
| 同上 | backend/app/routers/discord_guild_config.py:108-145 PUT /admin/discord-config（tenant.profile.edit 権限） | Depends(get_current_tenant) | **依頼の本文の guild_id をそのまま保存**。持ち主の照合なし | **新しい候補（3件目）** |
| tenant_meta_config（Meta のページ番号） | backend/app/routers/meta_inbox.py:190-250 | ログインの会社 | Meta の連携で受け取ったページの鍵 | 持ち主の証明あり |

本番の一意の決まり（読み取りの道 AUDIT ts=2026-11-06T07:31:38Z sha=8568fb4efa3c rows=6）: `uq_tenant_discord_config_guild_id UNIQUE (guild_id)`・主キー (tenant_id, purpose)。

新しい候補の中身:
- 他社が既に登録したサーバー番号は、一意の決まりで登録できない（取り上げはできない）
- まだ誰も登録していないサーバー番号は、持ち主でなくても先に登録できる。その後に本当の持ち主が共通 bot を入れると、そのサーバーの書き込みは先に登録した会社へ届く（backend/app/discord_gateway/client.py:101-125 は guild_id だけで会社を決める）
- 起きる条件: 管理者の権限を持つ人が、他社のサーバー番号を事前に知っていること。本番でこの窓口が使われた記録は、まだ確かめていない

## 5. 未確認

- 4. の新しい候補が本番で使われたか。読み取りの道では数えられなかった: tenant_NNN.audit_logs（AUDIT ts=2026-11-06T07:33:47Z sha=e43a68a81e6c result=db_error:InsufficientPrivilege）・public.tenant_discord_config（AUDIT ts=2026-11-06T07:34:06Z sha=8c32c81ca020 result=db_error:InsufficientPrivilege）とも読み取りの鍵に権限が無い
- Meta のページ番号は会社をまたいで一意の決まりがあるか（2社が同じページを連携したとき、どちらに届くか）
- 3-2 は「会社番号がどこから来るか」の確かめ。会社番号が正しくても、その会社の中で他社の人の番号を保存できる道（1. の2件と同じ型）は別の観点。設計で、人の番号を受け取る全入口を数える

## 6. 追記: 人の番号を受け取る全入口（2026-11-06）

5 の3つ目「人の番号を受け取る全入口を数える」の結果。

### 6-1. 取り消し: バッジとバディは本番で動いていない

- backend/app/routers/badges.py・backend/app/routers/buddy.py はファイルが残っているが、backend/app/main.py に登録が無い（`grep -n "buddy\|badges" backend/app/main.py` が0件。backend/app 内で2ファイルを読み込む所も0件）
- migrations/079_remove_buddy_badges.sql:6 で権限 buddy・badges を消している
- 本番の確かめ（ログインなし）: `/api/v1/badges/leaderboard` → 404、`/api/v1/buddy/pairs` → 404。比べる相手 `/api/v1/shifts` → 401（登録されていてログインを求める）
- よって 1. の2件目（バッジ）は他社に届かない。表から取り消す

### 6-2. 数え方

- 依頼の形（スキーマ）の欄で人の番号を持つもの 63件（scratchpad の uscan.py の出力）と、窓口の引数で人の番号を持つもの 15件（pscan.py の出力）を全部読んだ
- 読み出しの窓口（GET の絞り込み）は、その会社の表の行を絞るだけなので、他社の行は出ない。対象外
- Discord の利用者番号（discord_user_id 等）は public.users の番号ではないので対象外

### 6-3. 書く入口の判定（全件）

| 入口 | 欄 | 会社の照合 | 判定 |
|---|---|---|---|
| backend/app/routers/companies.py:391・:543 | sales_rep_id | あり（:357 `_ensure_sales_rep_in_tenant`） | 済み |
| backend/app/routers/teams.py:266 add_team_member | user_id | あり | 済み |
| backend/app/routers/roles.py:536 set_user_roles | user_id | あり | 済み |
| backend/app/routers/notice_fallback_recipients.py:94-101 | user_ids | あり | 済み |
| backend/app/routers/bots.py:122 `_ensure_owner_user_exists` | owner_staff_id | あり | 済み |
| backend/app/routers/order_commissions.py:241 `_validate_staff` | staff_id | あり | 済み |
| backend/app/routers/staff.py create/update | user_id | 依頼で受け取らない（指定すると拒否。番号は内部で作る） | 済み |
| backend/app/routers/calendar.py:225 update_calendar_owner | 窓口の user_id | その会社の staff 表で引く（`FROM staff s ... WHERE s.user_id = :user_id`） | 届かない |
| backend/app/routers/leads.py:806 convert_lead | （LeadConvertRequest.assigned_to） | 使っていない（:806-866 で読まない） | 届かない |
| **backend/app/routers/leads.py:411 create_lead** | assigned_to | **なし** | **ふさぐ** |
| **backend/app/routers/leads.py:499 update_lead** | assigned_to | **なし** | **ふさぐ** |
| **backend/app/routers/shifts.py:79 create_shift** | user_id | **なし**（表に外部キーなし: migrations/011_add_phase5_tenant_tables.sql:11） | **ふさぐ** |
| **backend/app/routers/goals.py:111 create_goal** | user_id | **なし**（外部キーは public.users だけで会社は見ない: migrations/075_create_goals.sql:55） | **ふさぐ** |
| **backend/app/routers/teams.py:102 create_team** | leader_id | **なし**（外部キーなし: migrations/003_add_phase1_tenant_tables.sql:108） | **ふさぐ** |
| **backend/app/routers/teams.py:147 update_team** | leader_id | **なし** | **ふさぐ** |

ふさぐ入口は 6件（4ファイル）。名前が見えるのは leads の1件（analytics.py:110-119）。ほかの5件は番号が保存されるだけで、名前は出ない（shifts・goals・teams の読み出しは public.users を結ばない。teams.py:234・:295 の結びはメンバーの表で、メンバー追加は照合済み）。

goals.py:111 の team_id は会社ごとの表 teams を指す。別の会社の表は search_path で見えないので、他社の番号を入れても他社のチームには結びつかない。対象外。

### 6-4. 本番に既に入っている他社の番号（読み取りの道）

AUDIT ts=2026-11-06T07:54:29Z sha=bd4cfa3fd323 rows=20 result=ok。5社（tenant_001・003・004・005・006）× 4欄で、自社の人でない番号の数を数えた。

| 欄 | 入っている数（5社合計） | 自社の人でない数 |
|---|---|---|
| leads.assigned_to | 0 | 0 |
| shifts.user_id | 0 | 0 |
| goals.user_id | 6（tenant_006） | 0 |
| teams.leader_id | 0 | 0 |

照合を足しても、今あるデータで保存が止まる行は無い。

### 6-5. Discord のサーバー番号を手で打つ欄（4. の3件目）の使われ方

- 画面 frontend/src/pages/admin/DiscordConfigPage.tsx:197-219 `handleGuildSave` が PUT /admin/discord-config を呼ぶ。:411-433 に番号を打つ欄と「接続」ボタンがある
- 持ち主の証明がある道（連携ボタン）は frontend/src/pages/channels/ChannelsPage.tsx:191-194 `handleDiscordConnect` → POST /discord/oauth/start
- 試験 backend/tests/test_discord_d2.py・backend/tests/test_discord_own_server.py が `/admin/discord-config` を参照する（PUT を使うかは実装時に読む）
