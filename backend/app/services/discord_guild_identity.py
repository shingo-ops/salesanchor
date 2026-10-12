"""サーバー（guild）の名前・アイコンを Discord から取得する（SSOT = Discord。DB には複製しない）。

ボタン案内・チケットのウェルカムを「サーバー名義」で投稿するために、送信のたびに解決する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.discord_rest import DiscordAPIError, discord_api_request

logger = logging.getLogger(__name__)

_CDN_BASE = "https://cdn.discordapp.com"
_ANIMATED_PREFIX = "a_"


@dataclass(frozen=True)
class GuildIdentity:
    name: str
    icon_url: str | None


def guild_icon_url(guild_id: str | int, icon_hash: str | None) -> str | None:
    """アイコン URL。ハッシュが a_ で始まるアニメーションは gif、それ以外は png。未設定は None。"""
    if not icon_hash:
        return None
    ext = "gif" if icon_hash.startswith(_ANIMATED_PREFIX) else "png"
    return f"{_CDN_BASE}/icons/{guild_id}/{icon_hash}.{ext}"


def build_guild_identity(guild_id: str | int, name: str | None, icon_hash: str | None) -> GuildIdentity | None:
    """名前が空なら None（名義にできない）。"""
    cleaned = (name or "").strip()
    if not cleaned:
        return None
    return GuildIdentity(name=cleaned, icon_url=guild_icon_url(guild_id, icon_hash))


async def fetch_guild_identity(guild_id: str, bot_token: str) -> GuildIdentity | None:
    """GET /guilds/{guild_id} で名前・アイコンを取得する。失敗時は None（呼び出し側が Bot 名義に戻す）。"""
    try:
        body = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}",
            bot_token=bot_token,
            expected_statuses=(200,),
        )
    except DiscordAPIError as exc:
        logger.warning("[discord_guild_identity] guild 取得失敗 guild=%s: %s", guild_id, exc)
        return None
    if not body:
        return None
    return build_guild_identity(guild_id, body.get("name"), body.get("icon"))
