"""スタッフ自己登録の招待（ADR-1068・設計 docs/handoff/staff-self-registration/design.md §3）。

- 招待リンクの鍵: "{tenant_id}.{secrets.token_urlsafe(32)}"。DB には sha256（32 バイト）だけを置く。期限は 72 時間。
- 鍵の形が合わないときは DB を引かずに無効として扱う（§3-3 R5）。
- 申込の後に出す Discord の招待は、自社サーバーの設計図の key staff_join_reception の部屋に作る（§3-4）。
ログには例外の種類だけを出す（鍵・登録番号・招待の文字列・メールは出さない）。
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.discord_blueprint import blueprint_path, load_blueprint
from app.services.discord_rest import discord_api_request
from app.services.viewer_invite import create_channel_invite

logger = logging.getLogger(__name__)

JOIN_LINK_TTL = timedelta(hours=72)  # backend/app/services/invite.py の INVITE_TTL と同じ値
REG_CODE_TTL = timedelta(days=7)  # Discord の招待の上限（viewer_invite.INVITE_MAX_AGE_SEC）に合わせる
RECEPTION_CHANNEL_KEY = "staff_join_reception"
ROOMS_CATEGORY_KEY = "staff_join_rooms"  # 個室を置くカテゴリ（type 4）
_DEFAULT_FRONTEND_BASE_URL = "https://app.salesanchor.jp"

# 会社番号（先頭 0 なし・最大 10 桁）. 鍵本体（token_urlsafe(32) は 43 文字）
_KEY_RE = re.compile(r"^([1-9][0-9]{0,9})\.([A-Za-z0-9_-]{43})$")


def new_join_key(tenant_id: int) -> str:
    """招待リンクの鍵を作る。生の値はこの1回だけ返す。"""
    return f"{int(tenant_id)}.{secrets.token_urlsafe(32)}"


def hash_join_key(key: str) -> bytes:
    """鍵全体の sha256（32 バイト）。DB に置くのはこれだけ。"""
    return hashlib.sha256(key.encode()).digest()


def parse_join_key(key: str) -> tuple[int, str] | None:
    """鍵の形を検査して (会社番号, 鍵) を返す。形が合わなければ None（DB は引かない）。"""
    if not isinstance(key, str):
        return None
    m = _KEY_RE.match(key)
    if m is None:
        return None
    tenant_id = int(m.group(1))
    if tenant_id > 2_147_483_647:  # INTEGER の上限
        return None
    return tenant_id, key


def join_url(key: str) -> str:
    """管理者が手で送る URL。鍵はフラグメントに置き、アクセスログや Referer に残さない。"""
    base = (os.getenv("FRONTEND_BASE_URL") or _DEFAULT_FRONTEND_BASE_URL).rstrip("/")
    return f"{base}/staff-join#k={key}"


def as_utc(value: datetime | str | None) -> datetime | None:
    """SQLite は日時を naive や文字列で返すため、比較の前に UTC の aware にそろえる。"""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def find_blueprint_channel_id(
    guild_id: str, token: str, tenant_id: int, key: str, channel_type: int
) -> str | None:
    """設計図の key の部屋（type 0）かカテゴリ（type 4）の番号。

    discord_id があればそれ。無ければ、名前が一致し type が channel_type の物が1つだけならその番号、他は None。
    discord_own_staff_sync._find_staff_role_id と同じ引き方。
    """
    path = blueprint_path(tenant_id)
    if not path.exists():
        return None
    bp = load_blueprint(path)
    items = bp.categories if channel_type == 4 else bp.channels
    item = next((c for c in items if c.key == key), None)
    if item is None:
        return None
    if item.discord_id:
        return str(item.discord_id)
    found = await discord_api_request(method="GET", path=f"/guilds/{guild_id}/channels", bot_token=token) or []
    hits = [str(c.get("id")) for c in found if c.get("name") == item.name and c.get("type") == channel_type]
    return hits[0] if len(hits) == 1 else None


async def _find_reception_channel_id(guild_id: str, token: str, tenant_id: int) -> str | None:
    """設計図の key staff_join_reception の部屋の番号（find_blueprint_channel_id を key・type 0 で呼ぶだけ）。"""
    return await find_blueprint_channel_id(guild_id, token, tenant_id, RECEPTION_CHANNEL_KEY, 0)


async def create_reception_invite(db: AsyncSession, tenant_id: int) -> str | None:
    """自社サーバーの「スタッフ受付」部屋の招待リンクを作る。作れなければ None（申込は成功のまま）。

    呼び出し側は、この関数を呼ぶ前に自分の書き込みを commit しておくこと（未 commit の変更は捨てられる）。
    """
    try:
        row = (await db.execute(
            text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
            {"tid": tenant_id},
        )).first()
        await db.rollback()  # 読み取りだけ。Discord を待つ間、トランザクションを開いたままにしない
        if row is None or not row[0]:
            return None
        token = os.environ.get("DISCORD_BOT_TOKEN")
        if not token:
            return None
        channel_id = await _find_reception_channel_id(str(row[0]), token, tenant_id)
        if channel_id is None:
            return None
        return await create_channel_invite(channel_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("staff join invite: 受付の招待を作れず kind=%s", type(exc).__name__)
        return None
