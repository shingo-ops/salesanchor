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
                text(f"SELECT lead_code, customer_name FROM {leads_t} WHERE id = :lid"),
                {"lid": lead_id},
            )).mappings().first()
            if not lead_row:
                return

            name = " ".join(filter(None, [
                (staff_row or {}).get("surname_jp"), (staff_row or {}).get("given_name_jp")])) or ""
            did = str((staff_row or {}).get("discord_user_id") or "")
            mention = [did] if did.isdigit() else None       # 数字以外は渡さない

            # customer_name は SELECT 済みだが文面には使わない（案イ・PO 判断待ち）。
            # PO 判断待ち: 顧客名を出す場合はここに追加（design.md §3-7 案ア）。
            # 切替時は上の lead_row["customer_name"] を使う（SELECT 済みの列を使う）。
            title = "🤝 商談化：担当アサイン"
            message = f"リード: {lead_row['lead_code']}\n担当: {name}"

            await send_discord_notification(
                db=db, tenant_id=tenant_id,
                event_type=NotificationEventType.lead_assigned.value,
                title=title, message=message,
                mention_user_ids=mention,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[leads] アサイン通知失敗（商談化自体には影響なし）: lead=%s %s", lead_id, exc)
