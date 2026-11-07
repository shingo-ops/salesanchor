"""Claude 用のスタッフ自己登録 Discord 受付の設定スクリプト（ADR-1068・設計 §4-3）。

viewer_discord_cli.py と同じ型。SQL・コマンドを受け取らない。受け取るのは stdin の JSON だけ:
  {"action": "post-staff-button", "tenant_id": <会社の番号>}
自社サーバー（purpose='own'）の「スタッフ受付」部屋（設計図の key staff_join_reception）にボタン付きの投稿を1回だけ置く。
"""
import asyncio
import json
import os
import sys

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.discord_gateway import staff_join_texts as T
from app.services.discord_rest import DiscordAPIError, discord_api_request
from app.services.staff_join import RECEPTION_CHANNEL_KEY, find_blueprint_channel_id

_ACTIONS = ("post-staff-button",)


class StaffJoinDiscordError(Exception):
    """code: invalid_input | not_configured | discord_error | no_token"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise StaffJoinDiscordError("no_token")
    return token


async def _post_staff_button(tenant_id: int, session_factory, request) -> dict:
    async with session_factory() as db:
        row = (
            await db.execute(
                text(
                    "SELECT guild_id FROM public.tenant_discord_config "
                    "WHERE tenant_id = :tid AND purpose = 'own' LIMIT 1"
                ),
                {"tid": tenant_id},
            )
        ).first()
    if row is None or not row[0]:
        raise StaffJoinDiscordError("not_configured")
    token = _token()
    try:
        channel_id = await find_blueprint_channel_id(str(row[0]), token, tenant_id, RECEPTION_CHANNEL_KEY, 0)
    except DiscordAPIError:
        raise StaffJoinDiscordError("discord_error") from None
    if channel_id is None:
        raise StaffJoinDiscordError("not_configured")
    try:
        messages = await request(method="GET", path=f"/channels/{channel_id}/messages?limit=50", bot_token=token) or []
    except DiscordAPIError:
        raise StaffJoinDiscordError("discord_error") from None
    for msg in messages:
        for comp_row in msg.get("components") or []:
            for comp in comp_row.get("components") or []:
                if comp.get("custom_id") == T.OPEN_BUTTON_CUSTOM_ID:
                    return {"posted": False, "reason": "exists"}
    try:
        sent = await request(
            method="POST",
            path=f"/channels/{channel_id}/messages",
            bot_token=token,
            json=T.reception_message_payload(),
        )
    except DiscordAPIError:
        raise StaffJoinDiscordError("discord_error") from None
    return {"posted": True, "message_id": (sent or {}).get("id")}


async def run(payload: dict, session_factory=AsyncSessionLocal, request=discord_api_request) -> dict:
    if not isinstance(payload, dict) or payload.get("action") not in _ACTIONS:
        raise StaffJoinDiscordError("invalid_input")
    tenant_id = payload.get("tenant_id")
    if isinstance(tenant_id, bool) or not isinstance(tenant_id, int) or tenant_id < 1:
        raise StaffJoinDiscordError("invalid_input")
    return await _post_staff_button(tenant_id, session_factory, request)


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(run(json.loads(sys.stdin.read(4096))))))
    except StaffJoinDiscordError as exc:
        print(f"staff join discord failed: {exc.code}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:
        # 入力値・トークン・traceback を出さない
        print("staff join discord failed: invalid_input", file=sys.stderr)
        raise SystemExit(1) from None
