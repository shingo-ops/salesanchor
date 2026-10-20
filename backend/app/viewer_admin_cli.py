"""Claude 用の閲覧者の状態変更スクリプト（ADR-1019 段4a-2）。

SQL・コマンドを受け取らない。受け取るのは stdin の JSON {action, email, days?} だけ。
action は activate / suspend / unsuspend / extend のみ。
"""
import asyncio
import json
import sys

from app.database import AsyncSessionLocal
from app.services import viewer_admin, viewer_room_notice

_ACTIONS = ("activate", "suspend", "unsuspend", "extend")


async def run(payload: dict, session_factory=AsyncSessionLocal) -> dict:
    if not isinstance(payload, dict):
        raise viewer_admin.ViewerAdminError("invalid_input")
    action = payload.get("action")
    email = payload.get("email")
    days = payload.get("days")
    if action not in _ACTIONS or not isinstance(email, str) or not 3 <= len(email) <= 254:
        raise viewer_admin.ViewerAdminError("invalid_input")
    async with session_factory() as db:
        item = await viewer_admin.change_status_by_email(
            db, email, action, actor=viewer_admin.ACTOR_CLAUDE, days=days
        )
        await db.commit()
    # commit の後に部屋へ送る（文面なしの unsuspend は None）
    room_notice, _ = await viewer_room_notice.notify_status_change(action, item)
    return {
        "id": item["id"],
        "status": item["status"],
        "trial_expires_at": item["trial_expires_at"].isoformat()
        if item["trial_expires_at"] is not None
        else None,
        "room_notice": room_notice,
    }


if __name__ == "__main__":
    try:
        result = asyncio.run(run(json.loads(sys.stdin.read(2048))))
        print(json.dumps(result))
    except viewer_admin.ViewerAdminError as exc:
        print(f"viewer admin failed: {exc.code}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:
        # 入力値・traceback を出さない
        print("viewer admin failed: invalid_input", file=sys.stderr)
        raise SystemExit(1) from None
