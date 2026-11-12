"""会社・連絡先の状態の表（public.customer_statuses）の定数と読み口。

状態の記号（code）と名前（name_ja / name_en）の正本は DB の表。
表名の文字列と記号の定数は、このファイルにだけ書く。他のファイルは記号を直書きせず、ここの定数を使う。
表を読む SQL もこのファイルに置く。
（サーバーの列挙 app/schemas/company.py・app/schemas/contact.py は残す。値の集合が表の code と
 一致することは backend/tests/test_customer_statuses_pg.py が毎回確かめる。）
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CUSTOMER_STATUSES_TABLE: Final[str] = "public.customer_statuses"

STATUS_ACTIVE: Final[str] = "active"
STATUS_INACTIVE: Final[str] = "inactive"
STATUS_ARCHIVED: Final[str] = "archived"
STATUS_PENDING_DEDUP_REVIEW: Final[str] = "pending_dedup_review"

_COLUMNS = "code, name_ja, name_en, sort_order, is_active, selectable_on_create"


async def list_customer_statuses(db: AsyncSession) -> list[dict[str, Any]]:
    """状態の表を sort_order 順に全行返す。"""
    result = await db.execute(
        text(f"SELECT {_COLUMNS} FROM {CUSTOMER_STATUSES_TABLE} ORDER BY sort_order")
    )
    return [dict(row) for row in result.mappings().all()]
