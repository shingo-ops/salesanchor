"""商談の担当アサインを Discord に通知する（fire-and-forget）。

呼び出しは leads.update_lead の commit 後（ADR-072: 新しいセッションを開き、
notification_channels / staff はテナントスキーマのため set_tenant_context が必須）。
作法は services/discord_role_sync.py:59-60 に倣う。
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from app.auth.dependencies import set_tenant_context, tenant_table_ref
from app.routers.notifications import send_discord_notification
from app.schemas.notification import NotificationEventType

logger = logging.getLogger(__name__)


async def notify_lead_assigned(tenant_id: int, lead_id: int, assigned_to_user_id: int) -> None:
    try:
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tenant_id)          # ADR-072（生 SET は CI がブロック）
            staff_t = tenant_table_ref(db, tenant_id, "staff")
            leads_t = tenant_table_ref(db, tenant_id, "leads")

            # design.md のサンプルは last_name/first_name だが、実スキーマ
            # （migrations/019_create_staff_tables.sql:40-41）は surname_jp/given_name_jp。
            staff_row = (await db.execute(
                text(f"SELECT discord_user_id, surname_jp, given_name_jp FROM {staff_t} "
                     f"WHERE user_id = :uid"),
                {"uid": assigned_to_user_id},
            )).mappings().first()
            lead_row = (await db.execute(
                text(f"SELECT customer_name FROM {leads_t} WHERE id = :lid"),
                {"lid": lead_id},
            )).mappings().first()
            if not lead_row:
                return

            name = " ".join(filter(None, [
                (staff_row or {}).get("surname_jp"), (staff_row or {}).get("given_name_jp")])) or ""
            did = str((staff_row or {}).get("discord_user_id") or "")
            mention = [did] if did.isdigit() else None       # 数字以外は渡さない

            # PO が 2026-10-29 に「お客さんの名前で知らせる」と決めた（リード番号は画面・通知に出さない）。
            # 名前の出どころは受信箱の見出しと同じ leads.customer_name
            # （frontend/src/pages/inbox/InboxMessageThread.tsx:437 の lead.customer_name）。
            # 名前が空のときも番号には戻さず、固定の文言を出す。
            customer = (lead_row.get("customer_name") or "").strip() or "名前の無いリード"
            title = "🤝 商談化：担当アサイン"
            message = f"お客さん: {customer}\n担当: {name}"

            await send_discord_notification(
                db=db, tenant_id=tenant_id,
                event_type=NotificationEventType.lead_assigned.value,
                title=title, message=message,
                mention_user_ids=mention,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[leads] アサイン通知失敗（商談化自体には影響なし）: lead=%s %s", lead_id, exc)
