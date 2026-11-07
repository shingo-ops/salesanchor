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
