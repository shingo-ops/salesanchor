"""コードが求めるのに権限の一覧（public.permissions）に無いキーを数える（design.md §5-2）。

一覧の正は DB。ここに一覧の写しは置かない。
"""
from __future__ import annotations

from sqlalchemy import text

from app.auth.dependencies import REGISTERED_PERMISSION_KEYS

# 既知の欠け。キー: 残す理由。PO が扱いを決めたら、その PR でここから消し、
# backend/tests/test_permission_catalog.py の上限の数字を下げる（design.md §5-3）。
KNOWN_MISSING: dict[str, str] = {
    "companies.view": "PO 判断待ち: duplicates.py の経路。一覧に足すか、別のキーへ付け替えるか",
    "customers.edit": "PO 判断待ち: contacts.py の経路。一覧に足すか、別のキーへ付け替えるか",
    "leads.edit": "PO 判断待ち: discord_channel_invite.py・discord_role_resync.py の経路。一覧に足すか、別のキーへ付け替えるか",
}


async def count_missing_permission_keys(db) -> list[str]:
    """コードが求めるキーのうち、一覧にも KNOWN_MISSING にも無いものを名前順で返す。"""
    result = await db.execute(text("SELECT key FROM public.permissions"))
    in_catalog = {row[0] for row in result.fetchall()}
    return sorted(REGISTERED_PERMISSION_KEYS - in_catalog - set(KNOWN_MISSING))
