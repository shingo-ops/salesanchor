"""Claude 用の閲覧者 Discord 受付の設定スクリプト（ADR-1019 段4c）。

SQL・コマンドを受け取らない。受け取るのは stdin の JSON {action, ...} だけ。
action は list-candidates（読み取りのみ）／set-config／post-button のみ。
"""
import asyncio
import json
import os
import re
import sys

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.discord_gateway import viewer_bot_texts as T
from app.services.discord_rest import DiscordAPIError, discord_api_request

_ACTIONS = ("list-candidates", "set-config", "post-button")
_ID_RE = re.compile(r"^[0-9]{1,32}$")
_CONFIG_KEYS = ("guild_id", "reception_channel_id", "ticket_category_id", "staff_role_id")


class ViewerDiscordError(Exception):
    """code: invalid_input | not_configured | discord_error | no_token"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise ViewerDiscordError("no_token")
    return token


async def _get(request, path: str):
    try:
        return await request(method="GET", path=path, bot_token=_token())
    except DiscordAPIError:
        raise ViewerDiscordError("discord_error") from None


async def _list_candidates(payload: dict, request) -> dict:
    guilds = await _get(request, "/users/@me/guilds") or []
    out: dict = {
        "guilds": [{"id": g["id"], "name": g["name"]} for g in guilds],
        "categories": [],
        "text_channels": [],
        "roles": [],
    }
    guild_id = payload.get("guild_id")
    if guild_id is not None:
        if not isinstance(guild_id, str) or not _ID_RE.match(guild_id):
            raise ViewerDiscordError("invalid_input")
        channels = await _get(request, f"/guilds/{guild_id}/channels") or []
        roles = await _get(request, f"/guilds/{guild_id}/roles") or []
        out["categories"] = [{"id": c["id"], "name": c["name"]} for c in channels if c.get("type") == 4]
        out["text_channels"] = [
            {"id": c["id"], "name": c["name"], "parent_id": c.get("parent_id")}
            for c in channels
            if c.get("type") == 0
        ]
        out["roles"] = [{"id": r["id"], "name": r["name"]} for r in roles]
    return out


async def _set_config(payload: dict, session_factory) -> dict:
    values = {}
    for key in _CONFIG_KEYS:
        v = payload.get(key)
        if not isinstance(v, str) or not _ID_RE.match(v):
            raise ViewerDiscordError("invalid_input")
        values[key] = v
    async with session_factory() as db:
        await db.execute(
            text(
                "INSERT INTO public.viewer_discord_config "
                "(id, guild_id, reception_channel_id, ticket_category_id, staff_role_id) "
                "VALUES (1, :guild_id, :reception_channel_id, :ticket_category_id, :staff_role_id) "
                "ON CONFLICT (id) DO UPDATE SET guild_id = EXCLUDED.guild_id, "
                "reception_channel_id = EXCLUDED.reception_channel_id, "
                "ticket_category_id = EXCLUDED.ticket_category_id, "
                "staff_role_id = EXCLUDED.staff_role_id, updated_at = now()"
            ),
            values,
        )
        await db.commit()
    return values


async def _post_button(session_factory, request) -> dict:
    async with session_factory() as db:
        row = (
            await db.execute(
                text("SELECT reception_channel_id FROM public.viewer_discord_config WHERE id = 1")
            )
        ).first()
    if row is None:
        raise ViewerDiscordError("not_configured")
    channel_id = row[0]
    messages = await _get(request, f"/channels/{channel_id}/messages?limit=50") or []
    for msg in messages:
        for comp_row in msg.get("components") or []:
            for comp in comp_row.get("components") or []:
                if comp.get("custom_id") == T.OPEN_BUTTON_CUSTOM_ID:
                    return {"posted": False, "reason": "exists"}
    try:
        sent = await request(
            method="POST",
            path=f"/channels/{channel_id}/messages",
            bot_token=_token(),
            json=T.reception_message_payload(),
        )
    except DiscordAPIError:
        raise ViewerDiscordError("discord_error") from None
    return {"posted": True, "message_id": (sent or {}).get("id")}


async def run(payload: dict, session_factory=AsyncSessionLocal, request=discord_api_request) -> dict:
    if not isinstance(payload, dict) or payload.get("action") not in _ACTIONS:
        raise ViewerDiscordError("invalid_input")
    action = payload["action"]
    if action == "list-candidates":
        return await _list_candidates(payload, request)
    if action == "set-config":
        return await _set_config(payload, session_factory)
    return await _post_button(session_factory, request)


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(run(json.loads(sys.stdin.read(4096))))))
    except ViewerDiscordError as exc:
        print(f"viewer discord failed: {exc.code}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:
        # 入力値・トークン・traceback を出さない
        print("viewer discord failed: invalid_input", file=sys.stderr)
        raise SystemExit(1) from None
