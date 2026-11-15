"""請求に使える通貨の一覧（invoice-create-portfolio 便B・design.md §3-2）。

正本は為替の履歴の表 public.app_fx_rate_history（ハードコードしない。PO 2026-11-13）。
円（JPY）は為替の表に行が無くても常に使えるので先頭に置く。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_invoice_currencies(db: AsyncSession) -> list[str]:
    result = await db.execute(
        text(
            "SELECT DISTINCT currency FROM public.app_fx_rate_history "
            "WHERE currency <> 'JPY' ORDER BY currency"
        ),
    )
    return ["JPY", *[str(r[0]) for r in result.all()]]
