"""ADR-1058: AI の担当表を読む所（ここ1か所だけ。design.md §4-3）。

行が無ければ AiAssignmentMissing を上げる（既定値に逃げない）。sync 版は段1b-2 で同じ SQL から足す。
app.database は読まない（読むとエンジンを作るため。セッションは呼び手から受け取る）。
"""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SELECT_ASSIGNMENT_SQL = """
    SELECT c.provider, c.model
    FROM public.ai_job_assignments a
    JOIN public.ai_job_choices c ON c.id = a.choice_id AND c.job_key = a.job_key
    WHERE a.job_key = :job_key
"""


class AiAssignment(NamedTuple):
    provider: str
    model: str


class AiAssignmentMissing(LookupError):
    """担当表に job_key の行が無い。"""


async def get_ai_assignment(db: AsyncSession, job_key: str) -> AiAssignment:
    """job_key の今の担当（provider・model）を返す。行が無ければ AiAssignmentMissing。"""
    row = (await db.execute(text(_SELECT_ASSIGNMENT_SQL), {"job_key": job_key})).first()
    if row is None:
        raise AiAssignmentMissing(job_key)
    return AiAssignment(provider=row[0], model=row[1])


__all__ = ["AiAssignment", "AiAssignmentMissing", "get_ai_assignment"]
