"""ops_control（id=1 の 1 行）を触る試験を直列にする。pytest は --dist=loadfile で別ファイルが並行に走るため。"""

from contextlib import asynccontextmanager

from sqlalchemy import text

_LOCK_KEY = 1012002  # ADR-1012 段階2


@asynccontextmanager
async def ops_control_lock(admin_engine):
    async with admin_engine.connect() as conn:
        await conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _LOCK_KEY})
        try:
            yield
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _LOCK_KEY})
