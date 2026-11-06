# 実装カード: 第2段 2d お客さんの返信を「返信連絡」の知らせで担当者に届ける

- 設計: docs/handoff/discord-server-management/design.md D2-5・D2-9・D2-10（S2-5 の 2d）
- PO 承認: 第2段 KGI 8〜16 と設計を承認（2026-11-06）。マージ・デプロイまでの完走（2026-11-06）。このカードは移行を含まない（DB の形は変えない）
- このカードで満たす KGI: 13（担当のいるお客さんが返信すると、`customer_reply_received` を選んだ送り先に、担当者をメンションした知らせが 1 件届く。重なった受信では送らない）
- ブランチ: release/discord-own-server-s2-2d（実際の先頭は Opus が依頼文で伝える）
- 触ってよいファイル（この 12 個と報告書 docs/handoff/discord-server-management/impl-report-s2-2d.md だけ）:
  - backend/app/schemas/notification.py（§1）
  - backend/app/services/staff_mention.py（新規・§2）
  - backend/app/services/lead_assign_notifier.py（§3）
  - backend/app/services/customer_reply_notifier.py（新規・§4）
  - backend/app/discord_gateway/ticket_channel_writer.py（§5）
  - backend/app/routers/webhook.py（§6）
  - backend/tests/conftest.py（§7。fixture を 1 つ足すだけ）
  - backend/tests/test_notification_event_routing.py（§8。1 か所だけ）
  - backend/tests/test_customer_reply_notifier.py（新規・§9）
  - frontend/src/constants/notificationEventTypes.ts（§10）
  - frontend/src/locales/ja.json・frontend/src/locales/en.json（§10。`notifications.eventType` の中に 1 行ずつ足すだけ）
  - frontend/api-contract/openapi.json（§11。コマンドで作り直すだけ。手で書かない）
- 触らない: migrations・scripts・backend のほかのファイル（ほかの試験ファイルを含む）・docs/adr・.github・deploy.yml・docker-compose.yml・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の 12 個と報告書だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0
- ADR-027（画面の文字は t() 経由・ja と en は同じキー）→ §10 は鍵を 1 つずつ足すだけ。画面の部品・CSS は触らない（ADR-144）
- ADR-072（commit のあと reset_tenant_context）→ 新しい commit は足さない。知らせを送る関数（send_discord_notification）が中で commit と reset をする今の作りのまま。失敗したときは §4 で rollback と reset をする

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-s2-2d-customer-reply-notice.md を読んだ
- origin/release/discord-own-server-s2-2d の先頭 sha（git rev-parse の生出力）
- 触るファイルは 12 個と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドで動かすとき: [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] git config user.name と [4/4] origin/main が OK でなければ停止して BLOCKED
- `git fetch origin` のあと `release/discord-own-server-s2-2d` を取り出す（新しく作らない）
- 次の「変更前」の行が今の実物と同じことを `grep -n` で確かめ、生出力を貼る。違えば「想定分岐」に従う
  - backend/app/schemas/notification.py `    discord_outside_ticket_post = "discord_outside_ticket_post"`
  - backend/app/services/lead_assign_notifier.py `            staff_row = (await db.execute(` と `            mention = [did] if did.isdigit() else None`
  - backend/app/discord_gateway/ticket_channel_writer.py `from app.discord_gateway import outside_ticket_notice` と `        if inserted_row is None:` と `        if attachment_url:`
  - backend/app/routers/webhook.py `from app.routers.notifications import send_discord_notification` と `                            event_type="meta_message_received",` と `                    await clear_tenant_context(db)`
  - backend/tests/conftest.py `def _no_own_staff_sync_task(monkeypatch):`（2b で入った fixture。無ければ BLOCKED: 2b が main に入る前の土台）
  - backend/tests/test_notification_event_routing.py `        "discord_outside_ticket_post",`
  - frontend/src/constants/notificationEventTypes.ts `  discord_outside_ticket_post: "notifications.eventType.discordOutsideTicketPost",`
  - frontend/src/locales/ja.json と en.json `      "discordOutsideTicketPost":`
- 大事: Bash の命令の文字に「DELETE」と「FROM」を続けた語を書かない（クラウドの見張りが不可逆操作として止める）

## 決まり（このカード全体）

- 知らせの種類の文字 `customer_reply_received` は §1 の enum 1 か所だけに書く。backend のほかのファイルは `NotificationEventType.customer_reply_received.value` を使う（同じ文字を 2 か所に書かない。画面の表の鍵は今の 4 つと同じ作法で §10 に書く）
- 知らせに載せるのは「お客さんの名前・どこから・アプリの商談の場所」の 3 つだけ。お客さんの書いた本文・送った人の Discord / Meta の番号は載せない。ログにも載せない（失敗のログは例外の型の名前だけ）
- 知らせを送るのは、受信を新しい行として保存できたときだけ。重なって保存しなかった受信では送らない
- 知らせの失敗で、受信の保存や今の知らせ（meta_message_received）を失敗させない
- 担当者へのメンションは、今の担当決定の知らせ（lead_assign_notifier）と同じ引き方を §2 の 1 つの関数にまとめて、両方から使う（同じ SQL を 2 か所に書かない）
- アプリの場所の頭は環境変数 `FRONTEND_BASE_URL`、無ければ `https://app.salesanchor.jp`（先例 `backend/app/routers/discord_oauth.py:84` と同じ）。ALLOWED_ORIGINS は使わない（先頭が旧ドメイン）。場所は `{頭}/lead-chat?lead_id={商談の番号}`
- Discord の DM には送る所を作らない（今の受信が DM を読まない＝ADR-146 F7。design.md D2-10）

## §1 backend/app/schemas/notification.py

`    discord_outside_ticket_post = "discord_outside_ticket_post"  # Discord: 部屋の外の書き込み` の次の行に 1 行足す:

```python
    customer_reply_received = "customer_reply_received"  # お客さんの返信（第2段 2d）
```

## §2 backend/app/services/staff_mention.py（新規）

次の中身で作る（1 文字も変えない）:

```python
"""担当者（users.id）の名前と Discord のメンション先を引く（第2段 2d・design.md D2-5）。

担当決定の知らせ（lead_assign_notifier）とお客さんの返信の知らせ（customer_reply_notifier）が
同じ引き方を使う。呼ぶ側が先に set_tenant_context を済ませておく（ADR-072）。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.auth.dependencies import tenant_table_ref


async def assignee_name_and_mention(db: Any, tenant_id: int, user_id: int | None) -> tuple[str, list[str] | None]:
    """(名前, メンション先) を返す。担当がいない・番号が数字でないときはメンション先を None にする。"""
    if user_id is None:
        return "", None
    staff_t = tenant_table_ref(db, tenant_id, "staff")
    # 実スキーマ（migrations/019_create_staff_tables.sql:40-41）は surname_jp/given_name_jp
    staff_row = (await db.execute(
        text(f"SELECT discord_user_id, surname_jp, given_name_jp FROM {staff_t} "
             f"WHERE user_id = :uid"),
        {"uid": user_id},
    )).mappings().first()
    name = " ".join(filter(None, [
        (staff_row or {}).get("surname_jp"), (staff_row or {}).get("given_name_jp")])) or ""
    did = str((staff_row or {}).get("discord_user_id") or "")
    mention = [did] if did.isdigit() else None       # 数字以外は渡さない
    return name, mention
```

## §3 backend/app/services/lead_assign_notifier.py

（１）import に 1 行足す（`from app.schemas.notification import NotificationEventType` の次）:

```python
from app.services.staff_mention import assignee_name_and_mention
```

（２）`            staff_t = tenant_table_ref(db, tenant_id, "staff")` の 1 行を消す。

（３）`            # design.md のサンプルは last_name/first_name だが、実スキーマ` から `            )).mappings().first()`（staff_row の SELECT の終わり。lead_row の SELECT の前）までの 6 行を消す。

（４）`            name = " ".join(filter(None, [` から `            mention = [did] if did.isdigit() else None       # 数字以外は渡さない` までの 4 行を、次の 1 行に置き換える:

```python
            name, mention = await assignee_name_and_mention(db, tenant_id, assigned_to_user_id)
```

- 結果: set_tenant_context・tenant_table_ref（leads 用）・send_discord_notification の import と呼び方は今のまま（今の試験が `app.services.lead_assign_notifier.set_tenant_context` と `app.services.lead_assign_notifier.send_discord_notification` を差し替えているため。動かさない）
- 並びが変わる: 今は staff → leads の順に読んでいる。直したあとは leads を読み、無ければ戻り、あれば staff を読む。知らせの中身は変わらない

## §4 backend/app/services/customer_reply_notifier.py（新規）

次の中身で作る（1 文字も変えない）:

```python
"""お客さんの返信を「返信連絡」の送り先に知らせる（第2段 2d・design.md D2-5・D2-9・D2-10）。

送るのは受信を新しい行として保存できたときだけ（呼ぶ側が決める）。
中身はお客さんの名前・どこから・アプリの商談の場所だけ。本文・送った人の番号は載せない。
失敗しても受信の保存は失敗させない（例外は飲み込み、ログには型の名前だけ）。
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable

from sqlalchemy import text

from app.auth.dependencies import reset_tenant_context, set_tenant_context, tenant_table_ref
from app.schemas.notification import NotificationEventType
from app.services.staff_mention import assignee_name_and_mention

logger = logging.getLogger(__name__)

SOURCE_LABELS = {"discord": "Discord", "messenger": "Messenger", "instagram": "Instagram"}
NOTICE_TITLE = "💬 お客さんの返信"
NO_NAME = "名前の無いリード"
_DEFAULT_BASE_URL = "https://app.salesanchor.jp"
# 試験では conftest が False にする（裏の送信が本物の DB・Discord へ行かないように）
SCHEDULE_ENABLED = True
_pending: set[asyncio.Task[Any]] = set()


def _frontend_base_url() -> str:
    # 先例 backend/app/routers/discord_oauth.py:84 と同じ
    return (os.getenv("FRONTEND_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")


async def send_customer_reply_notice(db: Any, *, tenant_id: int, lead_id: int, source: str) -> bool:
    """知らせを 1 件送る。送る処理まで進めたら True、送らなかった・失敗したら False。"""
    label = SOURCE_LABELS.get(source)
    if label is None:
        return False
    try:
        # 循環 import を避けるため関数の中で読む（先例 backend/app/discord_gateway/outside_ticket_notice.py）
        from app.routers import notifications  # noqa: PLC0415

        await set_tenant_context(db, tenant_id)
        leads_t = tenant_table_ref(db, tenant_id, "leads")
        lead_row = (await db.execute(
            text(f"SELECT customer_name, assigned_to FROM {leads_t} WHERE id = :lid"),
            {"lid": lead_id},
        )).mappings().first()
        if not lead_row:
            return False
        _name, mention = await assignee_name_and_mention(db, tenant_id, lead_row.get("assigned_to"))
        customer = (lead_row.get("customer_name") or "").strip() or NO_NAME
        message = (
            f"お客さん: {customer}\n"
            f"どこから: {label}\n"
            f"{_frontend_base_url()}/lead-chat?lead_id={lead_id}"
        )
        await notifications.send_discord_notification(
            db=db, tenant_id=tenant_id,
            event_type=NotificationEventType.customer_reply_received.value,
            title=NOTICE_TITLE, message=message,
            mention_user_ids=mention,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[customer-reply-notice] 失敗（受信の保存には影響なし）: tenant=%s %s",
                       tenant_id, type(exc).__name__)
        try:
            await db.rollback()
            await reset_tenant_context(db, tenant_id)
        except Exception as exc2:  # noqa: BLE001
            logger.warning("[customer-reply-notice] 片付け失敗: tenant=%s %s",
                           tenant_id, type(exc2).__name__)
        return False


async def _run(db_factory: Callable[[], Any], tenant_id: int, lead_id: int, source: str) -> None:
    try:
        async with db_factory() as db:
            await send_customer_reply_notice(db, tenant_id=tenant_id, lead_id=lead_id, source=source)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[customer-reply-notice] 失敗: tenant=%s %s", tenant_id, type(exc).__name__)


def schedule_customer_reply_notice(db_factory: Callable[[], Any], *, tenant_id: int, lead_id: int, source: str) -> None:
    """受信の保存の commit のあとに呼ぶ。待たずに裏で 1 件送る（先例 backend/app/routers/leads.py:728 の create_task）。"""
    if not SCHEDULE_ENABLED:
        return
    try:
        task = asyncio.create_task(_run(db_factory, tenant_id, lead_id, source))
    except RuntimeError as exc:
        logger.warning("[customer-reply-notice] 予約できない: tenant=%s %s", tenant_id, type(exc).__name__)
        return
    _pending.add(task)
    task.add_done_callback(_pending.discard)
```

## §5 backend/app/discord_gateway/ticket_channel_writer.py

（１）import に 1 行足す（`from app.discord_gateway import outside_ticket_notice` の次）:

```python
from app.services import customer_reply_notifier
```

（２）`        if inserted_row is None:` から始まる重なりの戻り（`            return True` まで）の直後、`        if attachment_url:` の前に、空行を 1 つ挟んで次を足す（字下げは `        if attachment_url:` と同じ 8 つ）:

```python
        # 第2段 2d: 新しい行で commit できたときだけ、担当者にお客さんの返信を知らせる（待たない）
        customer_reply_notifier.schedule_customer_reply_notice(
            db_factory, tenant_id=tenant_id, lead_id=lead.lead_id, source="discord",
        )
```

- お客さんでない人（担当者など）の書き込みは、今の作りで保存の前に戻っている（`test_ticket_channel_outbound_is_ignored_without_commit_or_translation`）。足す所はその後ろなので、担当者の書き込みでは送らない

## §6 backend/app/routers/webhook.py

（１）import に 1 行足す（`from app.services.conv_log_writer import write_conversation_log` の前）:

```python
from app.services.customer_reply_notifier import send_customer_reply_notice
```

（２）今の `await send_discord_notification(` の呼び出し（`event_type="meta_message_received",` を含むもの）の閉じかっこ `                        )` の直後に、次を足す（字下げは `await send_discord_notification(` と同じ 24）:

```python
                        # 第2段 2d: 担当者へお客さんの返信の知らせ（今の meta_message_received は変えない）
                        await send_customer_reply_notice(
                            db, tenant_id=tenant_id, lead_id=lead_id, source=platform,
                        )
```

- 重なりで `continue` した受信（`if msg_id is None:`）はここまで来ないので送らない
- platform は "messenger" か "instagram"。§4 の SOURCE_LABELS に無い値なら何もしない

## §7 backend/tests/conftest.py

2b で入った `def _no_own_staff_sync_task(monkeypatch):` の fixture の直後（空行 2 つを挟む）に、次を足す:

```python
@pytest.fixture(autouse=True)
def _no_customer_reply_notice_task(monkeypatch):
    """第2段 2d: お客さんの返信の知らせを試験では裏で動かさない（本物の DB・Discord へ行かないように）。"""
    from app.services import customer_reply_notifier

    monkeypatch.setattr(customer_reply_notifier, "SCHEDULE_ENABLED", False)
```

## §8 backend/tests/test_notification_event_routing.py

`test_list_event_types_returns_all_codes` の一覧の `        "discord_outside_ticket_post",` の次の行に `        "customer_reply_received",` を足す。ほかは触らない。

## §9 backend/tests/test_customer_reply_notifier.py（新規）

作法は `backend/tests/test_notification_event_routing.py` の `_SessionCtx`・`_insert_channel`・`_insert_staff`・`_insert_lead`・`_FakeDiscordAsyncClient`（`app.routers.notifications.httpx.AsyncClient` を差し替える）・`FAKE_DISCORD_ID` の作り方（実行時に組み立てる）を写して使う（import でなく、このファイルの中に同じ小さな助けを書く）。送り先の行は event_types=["customer_reply_received"]、tenant_id=999 で置く。

次の試験を全部作る（名前もこのとおり）:

1. `test_notice_mentions_assignee_with_numeric_discord_id`: 担当あり・番号あり → 送信 1 件、content が `<@{FAKE_DISCORD_ID}>`、allowed_mentions が `{"parse": [], "users": [FAKE_DISCORD_ID]}`、戻り値 True
2. `test_notice_without_assignee_has_no_mention`: assigned_to なし → 送信 1 件、content にメンションが無い（payload に "content" が無いか、`<@` を含まない）
3. `test_notice_without_discord_id_has_no_mention`: 担当あり・番号なし → 送信 1 件、メンションなし
4. `test_notice_empty_customer_name_uses_fixed_text`: customer_name が空 → 知らせの本文（embed の description）に `お客さん: 名前の無いリード`
5. `test_notice_missing_lead_sends_nothing`: 無い lead_id → 送信 0 件、戻り値 False
6. `test_notice_unknown_source_sends_nothing`: source="line" → 送信 0 件、戻り値 False
7. `test_notice_message_has_only_name_source_link`: 本文が `お客さん: 山田商事\nどこから: Messenger\nhttps://app.salesanchor.jp/lead-chat?lead_id=10` と完全に同じ（FRONTEND_BASE_URL を monkeypatch.delenv で消して確かめる）。本文に受信の文字・送った人の番号が入る道が無いこと（関数の引数に本文が無い）を確かめる
8. `test_notice_uses_frontend_base_url_env`: FRONTEND_BASE_URL="https://example.test/" → 本文の最後の行が `https://example.test/lead-chat?lead_id=10`
9. `test_notice_swallows_errors_and_returns_false`: `app.routers.notifications.send_discord_notification` を例外を出す AsyncMock に差し替え → 例外が外に出ず False
10. `test_notice_goes_only_to_customer_reply_channel`: 送り先を 2 行（customer_reply_received と lead_assigned）置き → 送るのは customer_reply_received の行の 1 件だけ
11. `test_schedule_does_nothing_when_disabled`: conftest の fixture のまま（SCHEDULE_ENABLED=False）→ `asyncio.create_task` が呼ばれない（`patch("app.services.customer_reply_notifier.asyncio.create_task")` で数える）
12. `test_schedule_runs_send_once_when_enabled`: monkeypatch で SCHEDULE_ENABLED=True、`send_customer_reply_notice` を AsyncMock に差し替え → 予約のあと `_pending` の task を await し、AsyncMock が 1 回、tenant_id・lead_id・source が渡したとおり
13. `test_ticket_writer_schedules_notice_for_new_row`: `backend/tests/test_ticket_channel_translation.py` の `test_ticket_channel_message_enqueues_translation_task_after_save` と同じ作り（_DBContext・_mock_result・_FakeMessage 等をこのファイルに写す）で、`app.discord_gateway.ticket_channel_writer.customer_reply_notifier.schedule_customer_reply_notice` を MagicMock に差し替え → 1 回呼ばれ、kwargs が tenant_id=4・lead_id=45・source="discord"
14. `test_ticket_writer_does_not_schedule_for_duplicate`: 13 と同じで INSERT の結果を `_mock_result(None)`（重なり）にする → 0 回
15. `test_ticket_writer_does_not_schedule_for_staff_message`: 13 と同じで書いた人を担当者の番号（`test_ticket_channel_outbound_is_ignored_without_commit_or_translation` と同じ形）にする → 0 回
16. `test_webhook_new_message_calls_notice_once` と 17. `test_webhook_duplicate_message_does_not_call_notice`: `backend/tests/test_webhook_instagram.py` の `webhook_env` と `_insert_tenant_meta_config` と同じ作り（このファイルに写す）で、`app.routers.webhook.send_customer_reply_notice` を AsyncMock に差し替え、同じ Messenger の受信を 2 回 `process_messenger_event` に渡す → 1 回目の後に 1 回、2 回目の後も合計 1 回のまま。1 回目の kwargs が tenant_id=999・source="messenger"、lead_id が作られた leads の id
   - 13〜15 で写す助けの形が今の実物と合わないときは「想定分岐」に従う

## §10 画面の表示名

- frontend/src/constants/notificationEventTypes.ts: `  discord_outside_ticket_post: "notifications.eventType.discordOutsideTicketPost",` の次の行に `  customer_reply_received: "notifications.eventType.customerReplyReceived",`
- frontend/src/locales/ja.json: `notifications.eventType` の `"discordOutsideTicketPost": "部屋の外の書き込み（Discord）"` の行末に `,` を足し、次の行に `      "customerReplyReceived": "お客さんの返信"`
- frontend/src/locales/en.json: 同じ場所に `      "customerReplyReceived": "Customer reply"`

## §11 frontend/api-contract/openapi.json

手で書かない。`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で作り直し、`git diff --stat frontend/api-contract/openapi.json` の生出力を貼る（変わるのは NotificationEventType の enum に 1 つ足す所だけのはず。ほかが変われば止めて NEEDS_DECISION）

## 確かめ（全部の生出力を報告書に貼る）

1. `cd backend && python -m pytest tests/test_customer_reply_notifier.py tests/test_notification_event_routing.py tests/test_ticket_channel_translation.py tests/test_webhook_instagram.py -q`
2. `cd backend && python -m pytest tests/ -q -x -k "notification or webhook or ticket or lead_assign or discord"`
3. `cd backend && ruff check app/services/staff_mention.py app/services/customer_reply_notifier.py app/services/lead_assign_notifier.py app/discord_gateway/ticket_channel_writer.py app/routers/webhook.py app/schemas/notification.py tests/test_customer_reply_notifier.py`
4. `cd backend && python ../scripts/check_test_schema_dup.py` が今のリポジトリにあれば流す（無ければ「無い」と書く）
5. `cd frontend && npm run generate:api-types && npx tsc --noEmit && npx eslint src/constants/notificationEventTypes.ts`
6. ja と en の `notifications.eventType` の鍵が同じことを python で比べた結果（両向きの差が空）
7. `git diff --name-only origin/release/discord-own-server-s2-2d` が触ってよい 12 個と報告書の中だけであること
8. 本文・番号を載せていないこと: `grep -n 'message_text\|sender_id\|author' backend/app/services/customer_reply_notifier.py` が 0 件

## 保存

- 1 つの commit にまとめる。文は `feat(discord): お客さんの返信の知らせ（第2段 2d）`、最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- `git push origin release/discord-own-server-s2-2d`（force は使わない）。PR は作らない（Opus が作る）

## 想定分岐

- §0 の「変更前」の行が違う: 行番号だけのずれなら、同じ中身の行を探して報告書に新しい行番号を書いて進める。中身が違えば止めて NEEDS_DECISION（違う行の生出力を貼る）
- conftest に `_no_own_staff_sync_task` が無い: BLOCKED（土台が古い）
- §3 のあと今の lead_assign の試験が落ちる: 試験は直さず止めて NEEDS_DECISION（落ちた試験名と生出力）
- §9 の 13〜17 で写す助けの形が合わない（引数・戻り値の作りが違う）: 今の実物に合わせて写してよい。合わせた所を報告書に 1 行ずつ書く。確かめる中身（回数と kwargs）は変えない
- webhook の試験で、1 回目の lead_id を読めない: leads の表から `channel_type = 'messenger'` の id を SELECT して比べる
- openapi.json の差が enum の 1 行以外にも出る: 止めて NEEDS_DECISION
- 確かめの 1・2 で、このカードと関係なく今も落ちる試験がある: origin のまま（変更前）でも落ちることを `git stash` で確かめ、両方の生出力を貼って先へ進む

## 報告

報告書 docs/handoff/discord-server-management/impl-report-s2-2d.md に、受領確認・§0 の生出力・各 § で何をしたか・確かめ 1〜8 の生出力・push した sha を書き、commit に含める。最後の行は次のどれか 1 つ:
- `DONE: <push した sha>`
- `BLOCKED: <理由>`
- `NEEDS_DECISION: <決めてほしいこと>`

END OF CARD

---

## 追補 A（2026-11-06・CI「test-schema-dup gate」の赤の直し）

### なぜ
CI の test-schema-dup gate（`scripts/check_test_schema_dup.py`）が赤。実測（PR #5201 head 4396dd9ff の CI ログ）:
`backend/tests/test_customer_reply_notifier.py (0 -> 5)`。§9 の webhook の試験のために、`test_webhook_instagram.py` の表の定義（leads・meta_messages・tenant_meta_config・tenants・lead_channels の 5 つの CREATE TABLE）を新しい試験ファイルに写したのが原因。テストに表の定義の新しい写しを増やすことは決まりで禁止（docs/specs/process-hardening/design-pillar3.md 柱3-a/b）。

### やること（これだけ）
1. `backend/tests/test_customer_reply_notifier.py` から、見出し `# webhook（test_webhook_instagram.py の webhook_env と _insert_tenant_meta_config を写す）` の区切り線から**ファイルの終わりまで**を消す（`_LEADS_DDL`〜`_LEAD_CHANNELS_DDL`・`webhook_engine`・`webhook_db`・`_insert_tenant_meta_config`・`_wrap_session_for_set_noop`・`webhook_env`・`_messenger_body`・試験 `test_webhook_new_message_calls_notice_once`・`test_webhook_duplicate_message_does_not_call_notice`）。その結果使われなくなった import（`event`・`create_async_engine`・`AsyncSession`・`sessionmaker`・`ExitStack` 等）は ruff が言うものだけ消す。他の試験は 1 文字も変えない。
2. `backend/tests/test_webhook_instagram.py` の**ファイルの最後**に、次の 2 つの試験と助けを足す（既存の `db_session`・`webhook_env`・`_insert_tenant_meta_config` をそのまま使う。既存の行は 1 行も変えない・消さない）。

```python
# ---------------------------------------------------------------------------
# 第2段 2d: お客さんの返信の知らせ（新しい受信のときだけ 1 回）
# ---------------------------------------------------------------------------


def _customer_reply_messenger_body(mid: str) -> dict:
    return {
        "object": "page",
        "entry": [{
            "id": "PAGE-A",
            "messaging": [{
                "sender": {"id": "PSID-100"},
                "timestamp": 1714400000,
                "message": {"mid": mid, "text": "Hello"},
            }],
        }],
    }


@pytest.mark.asyncio
async def test_webhook_new_message_calls_customer_reply_notice_once(db_session, webhook_env):
    from app.routers import webhook as wh

    await _insert_tenant_meta_config(db_session, tenant_id=999, page_id="PAGE-A")
    notice_mock = AsyncMock(return_value=True)

    with patch("app.routers.webhook.enqueue_inbound_translation"), \
            patch("app.routers.webhook.send_customer_reply_notice", new=notice_mock):
        await wh.process_messenger_event(_customer_reply_messenger_body("mid-notice-1"))

    assert notice_mock.await_count == 1
    res = await db_session.execute(text("SELECT id FROM leads WHERE channel_type = 'messenger'"))
    lead_id = res.scalar()
    assert lead_id is not None
    assert notice_mock.await_args.kwargs == {
        "tenant_id": 999, "lead_id": lead_id, "source": "messenger",
    }


@pytest.mark.asyncio
async def test_webhook_duplicate_message_does_not_call_customer_reply_notice(db_session, webhook_env):
    from app.routers import webhook as wh

    await _insert_tenant_meta_config(db_session, tenant_id=999, page_id="PAGE-A")
    notice_mock = AsyncMock(return_value=True)

    with patch("app.routers.webhook.enqueue_inbound_translation"), \
            patch("app.routers.webhook.send_customer_reply_notice", new=notice_mock):
        await wh.process_messenger_event(_customer_reply_messenger_body("mid-notice-2"))
        assert notice_mock.await_count == 1
        await wh.process_messenger_event(_customer_reply_messenger_body("mid-notice-2"))

    assert notice_mock.await_count == 1
```

3. 上の docstring の「対象」に `app.routers.webhook.process_messenger_event` が書いてあれば、その行は消し、代わりに `（webhook の 2 件は test_webhook_instagram.py の末尾）` と 1 行書く。

### 触らない
- `backend/app/` の全ファイル・conftest.py・他の試験・design.md。§1〜§11 で作ったものは変えない。

### 確かめ（生出力を impl-report-s2-2d.md の末尾「追補 A」に貼る）
1. `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD python3 scripts/check_test_schema_dup.py` → 最後の行が `テストへの新規スキーマ複製なし(pass)`、rc=0
2. `cd backend && python -m pytest tests/test_customer_reply_notifier.py tests/test_webhook_instagram.py -q` → 0 failed（件数を貼る。test_customer_reply_notifier は 2 件減り、test_webhook_instagram は 2 件増える）
3. `cd backend && ruff check tests/test_customer_reply_notifier.py tests/test_webhook_instagram.py` → rc=0
4. `git diff origin/main...HEAD -- backend/tests/test_webhook_instagram.py | grep '^-' | grep -v '^---'` → 0 行（既存行を消していない）

### 保存
- 1 つの commit。文は `test(discord): 2d の webhook 試験を既存の試験ファイルへ移す（表の定義の写しをなくす）`、最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- `git push origin release/discord-own-server-s2-2d`（force は使わない）

### 想定分岐
- 確かめ 1 が pass にならない: 止めて NEEDS_DECISION（生出力）
- 確かめ 2 で移した 2 件が落ちる: 既存の webhook_env が `send_discord_notification` も止めていることを確かめ、落ちた理由の生出力を貼って NEEDS_DECISION（試験の中身は変えない）
- 確かめ 4 が 0 行でない: 止めて NEEDS_DECISION

### 報告
impl-report-s2-2d.md の末尾に「追補 A」の節を足して commit に含める。最後の行は `DONE: <sha>` / `BLOCKED: <理由>` / `NEEDS_DECISION: <内容>` のどれか 1 つ。
