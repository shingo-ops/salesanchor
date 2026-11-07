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
