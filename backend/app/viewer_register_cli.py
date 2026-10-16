"""閲覧者の初期登録スクリプト（ADR-1019 段4a-2）。

SQL・コマンドを受け取らない。受け取るのは stdin の JSON {rows: [{applied_at, line_name, email, status}]} だけ。
メール・名前は出力しない。
"""
import asyncio
import json
import sys

from app.database import AsyncSessionLocal
from app.services import viewer_admin


async def run(payload: dict, session_factory=AsyncSessionLocal) -> dict:
    rows = payload["rows"]
    if not isinstance(rows, list):
        raise ValueError("rows")
    async with session_factory() as db:
        result = await viewer_admin.register_initial(db, rows)
        await db.commit()
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(run(json.loads(sys.stdin.read(65536))))))
    except Exception:
        # 入力値・traceback を出さない
        print("viewer register failed", file=sys.stderr)
        raise SystemExit(1) from None
