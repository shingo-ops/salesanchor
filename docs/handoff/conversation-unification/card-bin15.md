# 実装カード 便1.5: スマホのアプリから直接送った返信も受信箱に出す

> What this document is, in one line:
> A staff reply sent straight from the Messenger app, the Instagram app or Discord, without going through Sales Anchor, should be stored once in the inbox's conversation table so it shows in that customer's conversation flow. These are the instructions for that work.

- 親: design.md §便1.5（KGI K6〜K9 は PO 承認 2026-11-07「1」）。PO 2026-11-09「1」で「第1.5段を先に作る（Messenger・Instagram・Discord）。手動記録の廃止はその後」と決定
- 基準: origin/main 42802381b。行番号はすべて、この版で Opus が読んで確かめた。2026-11-09 10:2x JST に最新の origin/main ebfca4826 と比べ、対象の4ファイルに差が無いことも確かめた（webhook.py・meta_graph.py・leads.py・ticket_channel_writer.py の4つを `git diff --stat 42802381b ebfca4826 --` に渡して空）
- ブランチ: `release/conversation-unify-bin15`（`bash scripts/new-worktree.sh release/conversation-unify-bin15 --claude`）
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・04-worktree.md・05-pr.md・10-executor.md
- 受領確認: 着手の前に、§0 を満たしたかを1行で返してから始める
- 起票: Opus が手元で行う。担当は push までとする
  - Draft、`--base main`、`shingo-cc` 名義で起票する
  - `migrations/`・`deploy.yml`・本番 `scripts/` を含まないので、危険 PR ではない
  - マージと本番反映は担当が行わない

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

- origin/main の次の行が、下の表の「基準の中身」と同じであること
  - 確かめ方の例: `git show origin/main:backend/app/routers/webhook.py | sed -n '809p'`
  - 1つでも違えば、BLOCKED: で差を返す

| 場所 | 基準の中身（先頭の語） |
|---|---|
| `backend/app/routers/webhook.py:367` | `if msg.get("is_echo"):` |
| `backend/app/routers/webhook.py:420` | `if m.get("is_echo"):` |
| `backend/app/routers/webhook.py:535` | `async def _create_outbound_lead_for_echo(` |
| `backend/app/routers/webhook.py:809` | `if m.get("is_echo"):` |
| `backend/app/services/meta_graph.py:45` | `_DEFAULT_SUBSCRIBED_FIELDS = (` |
| `backend/app/routers/leads.py:2086` | `INSERT INTO {meta_messages_t} (` |
| `backend/app/routers/leads.py:2346` | `INSERT INTO {meta_messages_t}` |
| `backend/app/routers/leads.py:2533` | `INSERT INTO {meta_messages_t} (` |
| `backend/app/routers/leads.py:2844` | `INSERT INTO {meta_messages_t} (` |
| `backend/app/discord_gateway/ticket_channel_writer.py:208` | `inbound = bool(lead.discord_user_id) and author_id == str(lead.discord_user_id)` |

## 1. 事実（Opus が確かめたこと。担当は確かめ直さなくてよい）

- Meta の公式説明（Context7 `/websites/developers_facebook_business-messaging_messenger-platform` の message_echoes）には、次のことが書かれている:
  - Messenger の写しの形は `sender.id` = ページ、`recipient.id` = お客さんの PSID、`message.is_echo` = true、`message.app_id`、`message.mid`。
  - 写しを受けるには `message_echoes` を購読する必要がある。
  - 「Facebook Page inbox」から送った分の `app_id` は `26390203743090` になる。
  - `app_id` は、例では数字で、表では String と書かれている。そのため、必ず `str()` にしてから比べる。
- Instagram の公式説明（Context7 `/llmstxt/developers_facebook_instagram-platform_llms_txt` の webhooks/examples）:
  - 写しは `messaging[]` の中に `is_echo: true` 付きで届く（A 形式）。
  - 自分のアカウントが送ったとき、`recipient.id` はお客さんの IGSID、`sender.id` は自分のアカウントになる。
  - 自分宛ての試し送りには `is_self: true` が付く。
  - Instagram の写しに `app_id` が付くとは書かれていない。
  - `changes[]`（B 形式）で写しがどんな形で届くかは書かれていない。
- 本番の重複防止の索引:
  - `idx_meta_messages_message_id_unique`（`(message_id) WHERE message_id IS NOT NULL`）は、5社（001・003・004・005・006）すべてにある。
  - 2026-11-09 10:25 JST に読み取り専用の鍵で確かめた（`/tmp/CC報告ファイル/conv/card15/q-idx.txt`）。
  - 新しい会社の表も同じ索引を作る（`backend/app/services/tenant.py:1043-1045`）。
  - **migration は要らない。**
- `_create_outbound_lead_for_echo`（webhook.py:535-581）と `_find_lead_id_for_psid`（webhook.py:511-532）は、今どこからも呼ばれていない（`git grep` で呼び元 0）。
- Discord のチケットの部屋は非公開である。書けるのはお客さん・担当のロール・ボットだけ（`ticket_channel_creator.py:10-14`）。だから「ボットでもお客さんでもない人」は担当である。
- 未読の数は受信だけを数える（`backend/app/routers/meta_inbox.py:943` の `mm.direction = 'inbound' AND mm.seen_at IS NULL`、`leads.py:1211`）。送った行を足しても未読は増えない。
- `meta_messages` の RLS は `tenant_isolation_meta_messages`（`migrations/012_add_meta_tenant_tables.sql:34-35`、USING だけで FOR ALL）。アプリは既に同じ表を UPDATE している（`leads.py:1205`・`conv_logs.py:415` ほか）。だから §5 の `DO UPDATE` は、同じ会社の行に対して今の権限で通る。
- 会話の流れの API（`leads.py:1010-1018`）は `direction`・`sender_name`・`sent_by_staff_id` をそのまま返す。画面は direction で左右を分けるので、**画面の変更は要らない。**

## 2. 設計書からの2つの絞り込み（design.md §便1.5 にも同じ内容を書いた）

- (1) B 形式（`changes[]`）の写しは**今までどおり捨てる**。
  - 理由: 公式説明に B 形式の写しの形が無く、お客さんの id がどの項目に入るか分からないため。
  - Instagram の写しは A 形式で届くと公式に書かれているので、K7 はこれで満たせる。
  - 捨てたときは件数が分かるように、ログを1行残す。
- (2) アプリの送信の INSERT は `DO NOTHING` ではなく `DO UPDATE` にする。
  - 理由: 今のコードは `RETURNING` の行が無いと、古い SQLite 用の2回目の INSERT に進む（leads.py:2101-2121 ほか）。
  - そのため `DO NOTHING` にすると、写しが先に入っていたときに2回目の INSERT が重複で失敗し、送信が 500 になる。
  - `DO UPDATE` なら行が必ず返る。先に入った写しの行に、送った担当者（`sent_by_staff_id`）も書き足せる。

## 3. やること（この順）

1. クラウドの事前確認として、`git config user.name shingo-cc` と `git rev-parse --verify origin/main` を流す。どちらかが失敗したら BLOCKED: で返す。gh の確認と PR の起票は、Opus が手元で行う。
2. §4 Meta の写しを受ける
3. §5 アプリの送信の INSERT に重複のときの扱いを付ける
4. §6 購読の既定に `message_echoes` を足す
5. §7 Discord の担当者の直接の投稿を受ける
6. §8 試験を直す・足す
7. API の形の写しを作り直す: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`
   - API の形は変えないので、差は出ない見込み。
   - 差が出たら NEEDS_DECISION: で返す。
8. §9 の検索を流す

## 4. Meta の写しを受ける（`backend/app/routers/webhook.py`）

### 4-1. A 形式の写しの形をそろえる（:367-385）

変更前（:367-385）: 写しは `sender_id` = お客さん、`attachment_url`/`attachment_type` = None で yield している。

変更後:
```python
        if msg.get("is_echo"):
            # 便1.5: 自分宛ての試し送り（IG の is_self）と、消された文は受けない
            if msg.get("is_self") or msg.get("is_deleted"):
                continue
            recipient = messaging.get("recipient") or {}
            customer_psid = (
                str(recipient.get("id", ""))
                if recipient.get("id") is not None
                else ""
            )
            sender = messaging.get("sender") or {}
            business_id = (
                str(sender.get("id", "")) if sender.get("id") is not None else ""
            )
            if customer_psid:
                app_id_raw = msg.get("app_id")
                yield {
                    "sender_id": customer_psid,  # 顧客 PSID / IGSID（lead 検索に使用）
                    "business_id": business_id,  # 送った側（ページ / IG アカウント）
                    "app_id": str(app_id_raw) if app_id_raw is not None else None,
                    "message_text": msg.get("text", "") or "",
                    "message_id": msg.get("mid"),
                    "timestamp": messaging.get("timestamp"),
                    "has_attachments": bool(msg.get("attachments")),
                    "attachment_url": _extract_first_image_url(msg),
                    "attachment_type": _extract_first_image_type(msg),
                    "is_echo": True,
                }
            continue
```
- docstring（:329-336）のキーの一覧に `business_id`・`app_id`（写しのときだけ）を足す。

### 4-2. B 形式（:419-421）は捨てたままにし、ログを残す

変更後:
```python
                # 便1.5: B 形式の写しは公式に形の説明が無く、お客さんの id の場所が分からないため受けない。
                # IG の写しは A 形式（messaging[]）で届く（公式 webhooks/examples）。
                if m.get("is_echo"):
                    logging.info("[webhook] format-B echo not stored: mid=%s", m.get("id") or m.get("mid"))
                    continue
```

### 4-3. `_create_outbound_lead_for_echo`（:535-581）を窓口に合わせる

- 引数を `(db, *, tenant_id: int, psid: str, platform: str)` にする。使っていない `schema` は外す（呼び元は 0 件）。
- `platform` が `("messenger", "instagram")` でなければ `ValueError`。
- `customer_name` は `"Messenger User" if platform == "messenger" else "Instagram User"` にする（:642 の受信と同じ既定名）。
  - 理由: お客さんが次に書いたとき、:628-640 の名前の解決が働くようにする。
- `channel_type` と、lead_channels の `platform` を `platform` にする（:556 と :572 の `"messenger"` の決め打ちをやめる）。
- `notes` は `"[会話の一本化 便1.5] アプリ外の返信の写しで自動作成"` にする。
- commit の直後の `reset_tenant_context` は残す（ADR-072）。

### 4-4. 新しい関数 `_persist_echo_message`（`_persist_meta_message` の直後、関数の終わりの :744 の後に置く）

```python
async def _persist_echo_message(
    db: AsyncSession,
    *,
    tenant_id: int,
    platform: str,
    customer_id: str,
    business_id: str,
    message_text: str,
    message_id: Optional[str],
    timestamp: Any,
    has_attachments: bool,
    app_id: Optional[str],
    page_id: Optional[str] = None,
    attachment_url: Optional[str] = None,
    attachment_type: Optional[str] = None,
) -> Optional[int]:
    """アプリの外（スマホのアプリ・Business Suite）から送った返信の写しを outbound で保存する（会話の一本化 便1.5）。

    自社アプリから送った分は送信の処理が既に保存しているので入れない（app_id が META_APP_ID と同じとき）。
    app_id が無い写し（Instagram）は message_id の重複防止で二重を防ぐ。
    Returns: 新しく入れた meta_messages.id。入れなかったときは None。
    """
    if platform not in ("messenger", "instagram"):
        raise ValueError(f"unsupported platform: {platform}")
    own_app_id = os.getenv("META_APP_ID", "")
    if own_app_id and app_id and app_id == own_app_id:
        logging.info("[webhook] echo from own app not stored: mid=%s", message_id)
        return None
    if not message_id:
        logging.info("[webhook] echo without mid not stored: platform=%s", platform)
        return None

    lead_id = await _find_lead_id_for_psid(db, platform, customer_id)
    if lead_id is None:
        lead_id = await _create_outbound_lead_for_echo(
            db, tenant_id=tenant_id, psid=customer_id, platform=platform,
        )

    raw_payload = json.dumps({
        "timestamp": timestamp,
        "has_text": bool(message_text),
        "has_attachments": has_attachments,
        "is_echo": True,
        "app_id": app_id,
    })
    ins = await db.execute(
        text("""
            INSERT INTO meta_messages (
                tenant_id, lead_id, platform,
                sender_id, message_text, direction, raw_payload,
                message_id, recipient_id, page_id,
                attachment_url, attachment_type
            )
            VALUES (
                :tenant_id, :lead_id, :platform,
                :sender_id, :message_text, 'outbound', :raw_payload,
                :message_id, :recipient_id, :page_id,
                :attachment_url, :attachment_type
            )
            ON CONFLICT (message_id) WHERE message_id IS NOT NULL
            DO NOTHING
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "platform": platform,
            "sender_id": business_id,
            "message_text": message_text,
            "raw_payload": raw_payload,
            "message_id": message_id,
            "recipient_id": customer_id,
            "page_id": page_id,
            "attachment_url": attachment_url,
            "attachment_type": attachment_type,
        },
    )
    inserted_id = ins.scalar_one_or_none()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    return inserted_id
```
- `os` が import されていなければ足す。
- `sender_id` と `recipient_id` の向きは、アプリの送信（leads.py:2065・2078）と同じにする。`sender_id` が自社の側、`recipient_id` がお客さんの側。
- `sent_by_staff_id` は入れない（NULL）。アプリの外で送った人は分からないため。

### 4-5. 本体の分かれ目（:808-814）

変更前:
```python
                        # ── J1 エコー受信（アプリ外送信）: 便1 では何も書かない ──
                        if m.get("is_echo"):
                            logging.info(
                                "[webhook] echo skipped (conversation unification bin1): sender=%s",
                                m.get("sender_id"),
                            )
                            continue
```
変更後:
```python
                        # ── 便1.5 エコー受信（アプリ外送信）: outbound で meta_messages に書く ──
                        if m.get("is_echo"):
                            echo_id = await _persist_echo_message(
                                db,
                                tenant_id=tenant_id,
                                platform=platform,
                                customer_id=m["sender_id"],
                                business_id=m.get("business_id") or entry_id,
                                message_text=m["message_text"],
                                message_id=m["message_id"],
                                timestamp=m["timestamp"],
                                has_attachments=m["has_attachments"],
                                app_id=m.get("app_id"),
                                page_id=page_id_for_message,
                                attachment_url=m.get("attachment_url"),
                                attachment_type=m.get("attachment_type"),
                            )
                            if echo_id is not None:
                                try:
                                    from app.services.sse_pubsub import publish_inbox_update
                                    await publish_inbox_update(tenant_id)
                                except Exception:
                                    logging.warning(
                                        "[Meta] SSE publish 失敗（echo・Webhook 処理は継続）: tenant_id=%s",
                                        tenant_id,
                                    )
                            continue
```
- 写しでは、受信の訳・Discord への知らせ・お客さんの返信の知らせ・アバターの取得を**しない**。どれも受信のための処理なので、写しには要らない。
- 関数の docstring（:747-756）の手順に「写しは `_persist_echo_message` で outbound に書く」を1行足す。

## 5. アプリの送信の INSERT（`backend/app/routers/leads.py`）

次の4か所の**最初の INSERT だけ**で、`RETURNING id, created_at` の直前に重複のときの扱いを足す。

| 場所 | 送るもの | 足す行 |
|---|---|---|
| :2086-2098 | Messenger・IG の文 | `ON CONFLICT (message_id) WHERE message_id IS NOT NULL DO UPDATE SET sent_by_staff_id = EXCLUDED.sent_by_staff_id, lead_id = EXCLUDED.lead_id, messaging_type = EXCLUDED.messaging_type, message_tag = EXCLUDED.message_tag` |
| :2346-2354 | Discord の文 | `ON CONFLICT (message_id) WHERE message_id IS NOT NULL DO UPDATE SET sent_by_staff_id = EXCLUDED.sent_by_staff_id, lead_id = EXCLUDED.lead_id` |
| :2533-2545 | Discord の画像 | 2346 と同じ |
| :2844-2856 | Messenger・IG の画像 | 2086 と同じ |

- SQLite 用の2回目の INSERT（:2105・:2553・:2864）は**変えない**。`DO UPDATE` で行が必ず返るので、そこには進まない。
- `lead_id = EXCLUDED.lead_id` を入れる理由: 写しが先に届いて別のリードを作っていても、アプリで送った相手のリードにそろえるため。
- 送信に失敗したときは meta_messages の行が作られない（error_code は監査の記録にだけ残る）。だから、この変更の対象外になる。

## 6. 購読の既定（`backend/app/services/meta_graph.py:45-52`）

- `"messages",` の次の行に `"message_echoes",  # 会話の一本化 便1.5: アプリ外から送った返信の写しを受ける` を足す。
- `_DEFAULT_INSTAGRAM_SUBSCRIBED_FIELDS`（:58-62）は**変えない**。使われていない定数で、IG の写しは `messages` で届くため。
- 本番の Meta 接続は、今は全社で有効 0 件（HANDOFF 2026-11-07）。付け直すと新しい既定が使われる。

## 7. Discord の担当者の直接の投稿（`backend/app/discord_gateway/ticket_channel_writer.py`）

変更前（:208-216）: お客さんでない人の投稿を、ログだけ出して捨てている。

変更後:
- `lead.discord_user_id` が空のときは、**今までどおり捨てる**（ログも今のまま）。
  - 理由: 誰がお客さんか分からないまま担当の投稿として入れると、お客さんの文を送った側に置いてしまうため。
- それ以外は `direction = "inbound" if author_id == str(lead.discord_user_id) else "outbound"` とする。
- outbound にするのは、投稿の種類が普通の文か返信のときだけにする。
  - 書き方: `if direction == "outbound" and getattr(message, "type", None) not in outside_ticket_notice._ALLOWED_TYPES:` なら、ログを1行出して `return True`（commit しない）。
  - 前例: `outside_ticket_notice.py:26`・`:126` の同じ絞り込み。ピン留めや参加の知らせなどの仕組みの投稿を、担当の文として入れないため。
  - inbound（お客さんの投稿）には、この絞り込みを**足さない**（今の動きを変えない）。
- :221-233 の INSERT は、次のように直す:
  - `direction` を `:direction` にする。
  - 列に `recipient_id` を足す。outbound のときは `lead.discord_user_id`、inbound のときは None を入れる。アプリの Discord 送信（leads.py:2346-2363）と同じ向きにそろえる。
  - `sender_id` = `author_id`、`sender_name` = `author_name` は今のまま（担当の表示名が入る）。
  - `original_language` は今のまま。
- SSE（`publish_inbox_update`）は、この関数では今も呼んでいない。outbound でも**足さない**。
- outbound のときは、次のことを**しない**:
  - `customer_reply_notifier.schedule_customer_reply_notice`（:262-264）
  - `enqueue_inbound_translation`（:336-342）
- 添付の保存（:266-334）は、inbound・outbound のどちらでも同じように行う。
- ボット・webhook の投稿を捨てる処理（:199-206）は**変えない**。アプリから送った分はここで捨てられ、送信の処理が既に保存しているので、二重にならない。
- ファイル冒頭の docstring（:1-5）を「お客さんの投稿は inbound、担当がチケットの部屋に直接書いた投稿は outbound で保存する」に直す。

## 8. 試験（手元で回さない。CI の結果を読む）

### 8-1. 試験の表に重複防止の索引を足す（本番と同じ形）

`meta_messages` を SQLite で作っていて、§4・§5・§7 の INSERT を通す試験の DDL には、次の索引を足す（期待の数は変えない）。
```sql
CREATE UNIQUE INDEX idx_meta_messages_message_id_unique ON meta_messages (message_id) WHERE message_id IS NOT NULL
```
- SQLite は1回の execute で1つの文しか流せない。索引は表の DDL とは**別の定数**にし、表を作った後に別の execute で流す。
- 前例: `backend/tests/test_webhook_instagram.py:155-158`（`uq_meta_messages_message_id`）。`backend/tests/conftest.py:2168` も同じ索引を持つ。
- 少なくとも次に足す:
  - `backend/tests/test_message_send.py`
  - `backend/tests/test_message_image_send.py`（索引の定数をここに置く。`test_discord_staff_send.py:34` は DDL をここから import しているので、同じ定数も import して流す）
  - `backend/tests/test_discord_staff_send.py`
- 落ちたら足す候補: `test_outbound_draft_send.py`・`test_conversations.py`・`test_discord_inbox.py`・`test_messages.py`（どれも meta_messages の DDL を持ち、索引が無い）。
- ほかの試験が「ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint」で落ちたら、その試験の DDL にも同じ索引を足す。

### 8-2. 直す試験（写しを入れるようになった分の期待だけを変える）

- `backend/tests/test_conv_backbone_ben1b.py`:
  - `engine` に、meta_messages の DDL（`test_message_send.py:115-141` と同じ）と 8-1 の索引を足す。
  - `test_echo_unknown_psid_creates_outbound_lead`（:217-245）の期待を、次のとおりにする:
    - leads が 1 で、`channel_type='messenger'`・`initiative='outbound'`。
    - lead_channels が 1。
    - meta_messages が outbound で 1 行（`recipient_id='PSID-00001234'`）。
    - conversation_logs は 0 のまま。
  - `test_echo_known_psid_uses_existing_lead`（:248-）の期待を、次のとおりにする:
    - leads は 1 のまま。
    - meta_messages が `lead_id=42` の outbound で 1 行。
    - conversation_logs は 0 のまま。
  - 冒頭 docstring の2・3を「便1.5 以降は meta_messages に outbound で書く」に直す。
- `backend/tests/test_conversation_unify_bin1.py:347-370`:
  - 写しは `_persist_meta_message` を呼ばないので、`persist.assert_not_awaited()` は残す。
  - `leads` が 0 の期待は 1 に直す（写しが知らない相手のリードを作る）。
  - fixture の表に meta_messages が無ければ、8-1 と同じ形で足す。
  - conversation_logs が 0 の期待は変えない。
- `backend/tests/test_webhook_instagram.py`:
  - :610-635 と :921-944 の写しは recipient が無いので、今までどおり yield されない。**変えない。**
  - 落ちたら BLOCKED: で返す。
- `backend/tests/test_ticket_channel_translation.py`:
  - `_FakeMessage`（:40-48）に `type: object = discord.MessageType.default` を足す（`import discord` も足す）。今ある試験の動きは変わらない。
  - `test_ticket_channel_outbound_is_ignored_without_commit_or_translation`（:155-191）は、担当の投稿を入れるようになるので、次のとおりに直す:
    - 名前を `test_ticket_channel_staff_post_is_stored_outbound_without_translation` にする。
    - `session.execute` が呼ばれるのは2回（リードを探す文と INSERT）。返りは足さず、2つ目の `_mock_result((1,))` を INSERT の返りとして `_mock_result((99,))` に替える。
    - 期待: `handled is True`、`session.commit.await_count == 1`、`enqueue_mock.assert_not_called()`、`publish_mock.assert_not_called()`。
    - `customer_reply_notifier.schedule_customer_reply_notice` を MagicMock で差し替え、呼ばれないことも確かめる。
    - INSERT に渡した値で `direction == "outbound"`、`recipient_id == "1234567890"` を確かめる（`session.execute.call_args_list[1]`）。

### 8-3. 足す試験（新しい `backend/tests/test_conversation_unify_bin15.py`、SQLite）

| # | 試すこと | 期待 | KGI |
|---|---|---|---|
| 1 | Messenger の写し（app_id=`26390203743090`、知っている PSID） | meta_messages の outbound が1行、`sent_by_staff_id` が NULL、`sender_id`=ページ、`recipient_id`=PSID。リードは増えない | K6 |
| 2 | 1 と同じ写しを2回 | 行は1のまま | K9 |
| 3 | 写しの app_id が環境変数 `META_APP_ID` と同じ（数字で届くものも含む） | 0行 | K9 |
| 4 | Instagram の A 形式の写し（app_id なし、知らない IGSID） | outbound が1行。リードが `channel_type='instagram'`・名前 `Instagram User` で1件でき、lead_channels の platform が instagram | K7 |
| 5 | `is_self: true` の写し | 0行 | K7 |
| 6 | B 形式の `is_echo` | 0行 | — |
| 7 | 写しの後で受信の訳・Discord への知らせが呼ばれない | `enqueue_inbound_translation`・`send_discord_notification` が呼ばれない | — |
| 8 | 写しが**先**に入ってから、アプリが同じ mid で送信（Messenger・IG の文） | 行は1、`sent_by_staff_id`=送った担当、送信の応答は成功 | K9 |
| 9 | アプリの送信が**先**で、同じ mid の写しが後（app_id なし） | 行は1、`sent_by_staff_id` は送った担当のまま | K9 |
| 10 | Discord: 担当（お客さんでもボットでもない）がチケットの部屋に書く | outbound が1行、`sender_name`=表示名、`recipient_id`=お客さんの Discord id。返信の知らせ・訳が呼ばれない | K8 |
| 11 | Discord: 10 と同じ message id が2回届く | 行は1のまま | K8・K9 |
| 12 | Discord: お客さんの投稿・ボットの投稿・webhook の投稿・担当のピン留めの知らせ（`type=discord.MessageType.pins_add`） | お客さんは inbound で1行（今までどおり）。ボット・webhook・ピン留めの知らせは0行（commit 0） | K8 |
| 13 | Discord: `discord_user_id` が空のリードの部屋に、誰かが書く | 0行（INSERT が呼ばれず commit 0） | — |
| 14 | `meta_graph._DEFAULT_SUBSCRIBED_FIELDS` | `"message_echoes"` を含む | K6 |

- 10〜13（Discord）は、`test_ticket_channel_translation.py` と同じ組み方にする。
  - 書き込みの処理は `tenant_NNN.meta_messages` と会社名付きで書くので、SQLite の表では試さない。
  - `AsyncMock` のセッションに `execute.side_effect` で返りを並べ、`_DBContext` で包む。`set_tenant_context` は差し替える。
  - 1行入ったかは「INSERT の execute が呼ばれ、返りの行があり、commit が1回」で確かめる。
  - 11 は、関数を2回呼ぶ。1回目は返り2つ（リードの行・`(99,)`）のセッション、2回目は返り2つ（リードの行・`None`）の**新しい**セッションで組む。確かめるのは次の3つ: 2回とも `handled is True`。2回とも INSERT の文に `ON CONFLICT (message_id)` がある。2回目で例外が出ない。行が1つのままになることは、本番の索引（§1）と §13 の K9 で確かめる。
- 8・9 は、送信の試験（`test_message_send.py`）の土台と写しの処理（`webhook.process_messenger_event`）が、同じ DB を見るように組む（`test_conv_backbone_ben1b._patch_webhook_runtime` の差し替え方を使う）。
- どうしても同じ DB にできなければ、NEEDS_DECISION: で理由を返す。8・9 を外して進めない。
- 新しい試験ファイルは、移行の見張り（`test_tenant_loop_migration_guard` 等）の登録が要るなら登録する。

## 9. 終わったときの検索（PR の枝で流し、結果を PR 本文に貼る）

```bash
# 便1 の「写しを捨てる」ログ（0件）
git grep -n "echo skipped (conversation unification bin1)" -- backend/app
# Discord のお客さんでない人を捨てるログ（0件）
git grep -n "non-customer message ignored" -- backend/app
# 購読の既定（1件）
git grep -n '"message_echoes"' -- backend/app/services/meta_graph.py
# 送信の重複のときの扱い（4件）
git grep -n "DO UPDATE SET sent_by_staff_id" -- backend/app/routers/leads.py
# 対象の2ファイルが古い表を使っていない（0件）
git grep -n "conversation_logs" -- backend/app/routers/webhook.py backend/app/discord_gateway/ticket_channel_writer.py
```

## 10. 想定される分かれ道（こうなったらこうする）

| 起きたこと | どうする |
|---|---|
| §0 の行が基準と違う | BLOCKED: で差を返す |
| SQLite の試験で `ON CONFLICT ... WHERE ... DO UPDATE` が文法の誤りになる | 試験の DDL に 8-1 の索引があるか確かめる。あっても落ちる場合は、本番の SQL を変えずに BLOCKED: で生の出力を返す |
| 8-2 の外で、期待の数が変わる試験がある | 期待を書き換えない。BLOCKED: で差を返す |
| lint が「使われていない」と止める（`_find_lead_id_for_psid` など） | §4-4 で呼ぶので出ない見込み。出たら `# noqa` を付けず、NEEDS_DECISION: で返す |
| `_extract_first_image_url` が写しの添付で例外を出す | 写しの添付は None のまま（変更前と同じ）に戻し、PR 本文に書く |
| api-contract-check が赤 | §3 の 7 の命令で作り直したか確かめる。手で openapi.json を直さない |
| §4〜§7 の外で、写しや担当の投稿を捨てている所が見つかった | 足さずに、NEEDS_DECISION: で場所を返す |
| 手元で試験を回したくなる | 回さない。CI の結果を読む |

## 11. 触らない

- `conversation_logs` の表と行、既存の migration（便2・便3 の担当）
- `frontend/` 全部。画面は direction で左右を分けるので、変更は要らない（§1）
- `backend/app/discord_gateway/client.py` の DM の扱い（ADR-146。受信箱の窓口ではない）
- Meta の `standby`（引き継ぎの仕組み）で届く写し
- WhatsApp・電話・対面（自動の連携が無い）
- `public.channel_masters` の行（カード便1 §11）
- `.github/workflows/`、`migrations/`、`scripts/`
- `_DEFAULT_INSTAGRAM_SUBSCRIBED_FIELDS`

## 12. 終わりの報告

- `DONE`／`BLOCKED: 理由`／`NEEDS_DECISION: 問い` のどれかで始める
- 停止したときは、その場で手を止める。`BLOCKED:` で始めて、止まった手順・命令・生の出力を返す。自分で回り道を作らない
- 報告に入れるもの:
  - push した HEAD（40桁）
  - §9 の5つの検索の生の出力
  - 変えた試験の一覧
  - `git diff main...HEAD --name-only` の生の出力
- 推測で埋めない。読めなかった出力は「読めなかった」と書く

## 13. 反映の後（Opus と PO が行う。担当はしない）

- K8:
  - PO が本番の Discord のチケットの部屋に、担当として1通書く。
  - PO は、その相手の会話の流れに1件だけ出ることを目で見る（○×）。
  - Opus が読み取り専用の鍵で、反映時刻より後の `platform='discord' AND direction='outbound' AND sender_id NOT LIKE 'bot:%'` の行を数え、生の出力を残す。
- K9:
  - Opus が5社で `SELECT message_id, COUNT(*) FROM meta_messages WHERE message_id IS NOT NULL GROUP BY 1 HAVING COUNT(*) > 1` を流す。0行なら合格。
  - 索引があるので0になるのが当たり前だが、索引が消えていないことの確かめも兼ねる。
- K6・K7:
  - Meta の接続を付け直した後で、PO が Messenger と Instagram のアプリから1通ずつ送り、目で見る。
  - それまでは §8-3 の CI 試験を根拠にする。
  - 付け直しは Meta の会社確認の後になる（whatsapp-intake と同じ待ち）。

END OF CARD
