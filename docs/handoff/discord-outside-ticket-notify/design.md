# 設計: Discord で、お客さんが自分の部屋の外に書いたとき担当者に知らせる

- 状態: PO 承認済みの方針で作った設計。方針は PO 2026-11-02 チャット「3」（お客さんには何も返さず、担当者にだけ Discord で知らせる）と「1」（担当者以外の全員の書き込みを知らせる）
- 調べた事実: docs/handoff/discord-outside-ticket-notify/recon.md（以下 recon）
- 対象 ADR: docs/adr/ADR-009-discord-gateway.md（受信の基盤。変えない）、docs/adr/ADR-091-discord-bot-scope-definition.md（チケット機能。変えない）、docs/adr/ADR-098-sa-multi-channel-identity-resolution.md（Discord の人は author id を正本とする）
- 既存 ADR の検索: `git grep -i discord docs/adr` と docs/adr/FEATURE-INDEX.md。部屋の外の書き込みを扱う ADR は無い（recon ④）

## 1. 目的と合格条件

PO にとって変わること: お客さんが共有のチャンネルに書いても、今は誰も気づけない。変更のあとは、会社の担当者用の Discord チャンネルに「誰が・どのチャンネルに書いたか」とその書き込みへのリンクが届く。お客さんの側には何も起きない。

| # | 基準 | 検証方法 | 合格ライン |
|---|---|---|---|
| K1 | 担当者以外の人が部屋の外に書くと、通知先に1件届く | 試験（偽の書き込み・偽の送信）と本番で1回 | 試験で送信1回。本番は担当者用チャンネルに1件届く（PO の目視） |
| K2 | 担当者の書き込みでは届かない | 試験 | 担当者として登録した人・担当者の役割を持つ人・サーバーの管理者、どれも送信0回 |
| K3 | 部屋の中の書き込みは今まで通り受信箱に入り、知らせない | 既存の試験 backend/tests/test_ticket_channel_translation.py と新しい試験 | 既存の試験が通る。部屋の中では送信0回 |
| K4 | 同じ人が同じチャンネルに続けて書いても、30分に1件まで | 試験 | 30分以内の2件目は送信0回。別の人・別のチャンネルは届く |
| K5 | 参加のお知らせなど Discord の自動の書き込みでは届かない | 試験 | 普通の書き込みと返信以外は送信0回 |
| K6 | お客さんへは何も送らない | 差分の検索 | 追加の行に、Discord の部屋への送信・名義送信・DM の呼び出しが0件 |
| K7 | 書き込みの本文は通知に載せない | 試験 | 送る文に本文の文字列が入らない |
| K8 | 通知先の設定画面で、この種類を選べる | 画面（日本語・英語） | 「部屋の外の書き込み（Discord）」の欄が出る。英語でも空欄にならない |
| K9 | 既存の試験を壊さない | CI | 失敗0 |

## 2. 対象と対象外

- 対象（backend）
  - backend/app/schemas/notification.py: 種類 `discord_outside_ticket_post` を足す
  - backend/app/discord_gateway/outside_ticket_notice.py（新規）: 知らせるかの判定・重複の抑え・送信
  - backend/app/discord_gateway/ticket_channel_writer.py: 185〜192行目の「部屋の持ち主が無い」枝から上を呼ぶ
  - backend/tests/test_discord_outside_ticket_notice.py（新規）
- 対象（frontend）
  - frontend/src/constants/notificationEventTypes.ts: 表示名キーを1行足す
  - frontend/api-contract/openapi.json: 種類の一覧が変わるため、`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で作り直す（2026-11-03 審査で入れ忘れを指摘され追記。CI「API contract is up to date」が守る）
  - backend/tests/test_notification_event_routing.py: 種類の一覧の試験の期待値に4つ目を足す（2026-11-03 追記）
  - frontend/src/i18n の ja.json・en.json: `notifications.eventType.discordOutsideTicketPost` を足す
- 対象（文書）: この設計、recon、作業の札
- 対象外: お客さんへの返事、受信箱への取り込み、DB の表の変更（migrations なし）、通知先の設定画面の作り（既存 frontend/src/pages/notifications/NotificationsPage.tsx をそのまま使う）、DM、閲覧者の部屋（別のサーバー。本番で3社とも閲覧者のサーバーと別と確認）

## 3. 本番で確かめた事実（2026-11-02、読み取り専用の道。値は出さず有無と件数だけ）

- Discord をつないでいる会社は3社（tenant 1・4・6）。3社とも担当者の役割・部屋のボタンのチャンネル・部屋の分類が設定済み
- 担当者のうち Discord の人を登録しているのは、tenant 1 が 2人中0人、tenant 4 が 2人中1人、tenant 6 が 4人中0人。**登録だけでは担当者を見分けられない** → 担当者の役割と管理者の権限も使う（§4-2）
- 通知先（notification_channels）は全社0件。**今のままでは誰にも届かない** → 合流後に、担当者用チャンネルの通知先を画面から登録する（§7）
- 閲覧者の部屋のサーバーは、3社のどのサーバーとも別
- 受信の入口は backend/app/discord_gateway/client.py:394 の1か所だけ（`git grep "def on_message"`）

## 4. 変更の中身

### 4-1. 種類（backend/app/schemas/notification.py）

`discord_outside_ticket_post = "discord_outside_ticket_post"` を足す。既存3つ（lead_assigned / meta_message_received / tcg_distribution_error）のどれの部分文字列でもなく、どれも含まない。試験 backend/tests/test_notification_event_routing.py:125 が守る。

### 4-2. backend/app/discord_gateway/outside_ticket_notice.py（新規）

`async def notify_outside_ticket_post(db, *, tenant_id: int, message) -> bool` を1つ作る。返り値は送ったら True。例外は外に出さない（受信の処理を止めない）。上から順に判定し、1つでも当たれば送らない。

1. 書き込みの種類が普通の書き込み（`discord.MessageType.default`）か返信（`discord.MessageType.reply`）でない
2. 書いた人が bot、または `message.webhook_id` がある
3. 書いた人が担当者。次のどれか
   - (a) その会社の staff 表の discord_user_id と一致（`SELECT 1 FROM staff WHERE tenant_id = :tid AND discord_user_id = :uid LIMIT 1`）
   - (b) 書いた人の役割に、public.tenant_discord_ticket_config の staff_role_id がある（`message.author.roles` の id と比べる。roles が無いときは当たらない扱い）
   - (c) `message.author.guild_permissions.administrator` が True
4. スレッドの中の書き込みで、親のチャンネルがその会社の部屋（leads.discord_guild_channel_id と一致）
5. 重複の抑え: Redis キー `discord_outside_ticket_notice:{tenant_id}:{channel_id}:{author_id}` を `SET NX EX 1800` で置けなかった（30分以内に送った）。Redis が無いとき（`app.cache.get_redis()` が None）や Redis の失敗のときは送らない（前例 backend/app/discord_gateway/viewer_interview_notice.py:67 と同じ。二重に送るより送らない方を選ぶ）

送る中身（`app.routers.notifications.send_discord_notification` を使う。mention_user_ids は渡さない）:
- title: 「部屋の外の書き込み（Discord）」
- message: 3行。「書いた人: <表示名>」「チャンネル: #<チャンネル名>」「<message.jump_url>」。本文・添付・Discord の id は載せない（前例 backend/app/routers/webhook.py:938-947 が送信者 id を伏せる）
- 文面は日本語の固定文。backend の通知文はこれまでも日本語の固定文（backend/app/services/lead_assign_notifier.py:50-56）なので、それに合わせる

send_discord_notification は最後に commit と reset_tenant_context をする（backend/app/routers/notifications.py:186-187）。呼んだあとはそのセッションで続きの処理をしない。

送れなかったとき（通知先が0件のときを含む）は Redis キーを消さない。通知先0件で毎回 DB を引かないためと、30分後にはまた試すため。

ログ: `[discord-gateway] outside-ticket notice tenant=%s result=%s`（result は sent / skipped_<理由>）。本文・表示名・id は出さない。

### 4-3. backend/app/discord_gateway/ticket_channel_writer.py

185〜192行目の `if lead is None:` の枝を次にする。warning は info に下げる（部屋の外は異常ではなくなるため）。

```python
        if lead is None:
            logger.info(
                "[discord-gateway] outside ticket channel tenant=%s ch=%s msg=%s",
                tenant_id,
                channel_id,
                message_id,
            )
            await outside_ticket_notice.notify_outside_ticket_post(
                db, tenant_id=tenant_id, message=message
            )
            return True
```

ほかの行は変えない。

### 4-4. 画面の表示名

- frontend/src/constants/notificationEventTypes.ts に `discord_outside_ticket_post: "notifications.eventType.discordOutsideTicketPost",`
- ja.json に「部屋の外の書き込み（Discord）」、en.json に「Post outside a ticket room (Discord)」。両方に同じキー（ADR-027）

## 5. 試験（backend/tests/test_discord_outside_ticket_notice.py）

偽の message（type・author.bot・author.roles・author.guild_permissions・webhook_id・channel・jump_url・content）、偽の Redis（SET NX を真似る）、送信は `send_discord_notification` を差し替えて呼び出しを数える。

- T1: 担当者でない人の普通の書き込み → 送信1回。title と3行の message。本文の文字列を含まない（K1・K7）
- T2: staff 表に一致 → 0回。T3: 担当者の役割 → 0回。T4: 管理者 → 0回（K2）
- T5: 同じ人・同じチャンネル2回 → 1回だけ。別の人 → 届く（K4）
- T6: 参加のお知らせの種類 → 0回。bot・webhook → 0回（K5）
- T7: Redis が None → 0回
- T8: スレッドの親が部屋 → 0回
- T9: process_ticket_channel_message で部屋の持ち主が無いとき notify が呼ばれ、部屋の中では呼ばれない（K3）
- 既存の backend/tests/test_notification_event_routing.py:125 の部分文字列の試験が新しい種類でも通る

## 6. 代替案

- bot が担当者に DM する: 担当者の Discord の人の登録がほぼ無い（§3）。採らない
- bot が担当者用チャンネルに書く: 送り先のチャンネルを持つ所が新しく要る（recon ③-2）。既存の通知先の画面で足りるので採らない
- 受信箱に「部屋の外」として取り込む: PO の方針（知らせるだけ）と違う。採らない
- 担当者の見分けを staff 表だけにする: 本番で登録がほぼ無く、担当者の書き込みでも毎回届いてしまう。採らない

## 外部・過去事例の参照と我々への応用

- 出典: Discord 公式「Message Resource」の Message Types 表（github.com/discord/discord-api-docs developers/resources/message.mdx、2026-11-02 参照。Context7 /discord/discord-api-docs で確認）。書き込みには種類がある。普通の書き込みは DEFAULT（0）、返信は REPLY（19）、参加のお知らせは USER_JOIN（7）、ピン留めのお知らせは CHANNEL_PINNED_MESSAGE（6）など。→ 0 と 19 だけを知らせれば、Discord の自動のお知らせで通知が届かない（§4-2 の1）。参加のお知らせの書き手がだれの扱いになるかは公式の表に書いておらず、まだ確かめていない。種類で絞るので、どちらでも結果は変わらない
- 出典: discord.py 公式（discordpy.readthedocs.io/en/latest/api.html、2026-11-02 参照。Context7 /websites/discordpy_readthedocs_io_en で確認）。`Message.jump_url` は書き込みへ飛ぶ URL。`Member.guild_permissions` はサーバーの持ち主と管理者を含めた権限。`Thread.parent_id` は親のチャンネルの id。`MessageType.new_member` は参加のお知らせ。→ リンク・管理者の判定・スレッドの親は、ライブラリの値で取れる
- 数値の事例は使わない。この変更の正しさは試験と本番の1回で確かめる。適用限界: 通知の件数がどれだけになるかは、本番の記録が残っていない（受信の入れ物が11/2 に入れ替わり、それより前の記録が無い）ので、まだ確かめていない

## 7. 危険と対処・戻し方・測り方

- 危険: 知らせが多すぎる → 1人・1チャンネル30分に1件（K4）。担当者は届かない（K2）。合流後1週間の通知の記録（notification_logs の件数）を見る
- 危険: お客さんの書き込みの中身が他社に漏れる → 本文を載せない（K7）。送り先は会社ごとの通知先だけ（既存の tenant_id 条件 notifications.py:159-163）
- 危険: 通知先0件のまま誰にも届かない → 合流後に、担当者用チャンネルの通知先を設定画面から登録する。Discord で通知用の接続先を作るのは Discord の画面の操作なので PO に頼む
- 戻し方: 設定画面で「部屋の外の書き込み（Discord）」の印を外す（その会社だけ止まる）。全体は本 PR を戻す。DB の変更が無いので戻すときの移行は無い
- 測り方: K1 は本番で、担当者でないアカウントで共有のチャンネルに1回書き、担当者用チャンネルに届くか

## 維持の仕組み

- 守り手: 試験 backend/tests/test_discord_outside_ticket_notice.py（T1〜T9）と backend/tests/test_notification_event_routing.py:125。CI の backend の試験で毎回動く

## 8. 設計審査（同じ AI による自己審査。独立した第二者審査ではない）

- 判定: APPROVE
- 根拠: 捨てている場所（ticket_channel_writer.py:185-192）、送る仕組み（notifications.py:153）、重複の抑えの前例（viewer_interview_notice.py）、担当者の見分けに使う値（staff 表・staff_role_id・管理者の権限）の4つが、コードと本番の有無で確認できている。DB の変更が無く、変える場所は1か所の枝と新しい部品1つ
- 未解決: 通知の件数の見込み（まだ確かめていない。合流後1週間で測る）。本番で届くかは通知先の登録が先に要る
