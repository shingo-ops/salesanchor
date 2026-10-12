"""Discord リアクションイベントを DB に書き込むヘルパ。

Gateway の on_raw_reaction_add / on_raw_reaction_remove から呼ばれ、
meta_message_reactions テーブルへの INSERT / DELETE と SSE 通知を担う。
"""
from __future__ import annotations

import logging
from typing import Any

import asyncpg

from app.services import sse_pubsub

logger = logging.getLogger(__name__)


def _schema(tenant_id: int) -> str:
    return f"tenant_{tenant_id:03d}"


class ReactionWriter:
    """Discord リアクションイベントを meta_message_reactions テーブルに保存する。

    asyncpg を直接使用して Gateway プロセスからの書き込みを行う。
    (Gateway は SQLAlchemy AsyncSession ではなく asyncpg pool で動作する)
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """asyncpg コネクションプールを初期化する。"""
        self._pool = await asyncpg.create_pool(
            self._database_url,
            min_size=1,
            max_size=5,
        )
        logger.info("[reaction-writer] asyncpg pool initialized")

    async def close(self) -> None:
        """コネクションプールをクローズする。"""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("[reaction-writer] asyncpg pool closed")

    async def process_reaction(
        self,
        *,
        tenant_id: int,
        channel_id: str,
        message_id: str,
        user_id: str,
        emoji: Any,
        member: Any,
        action: str,
        is_bot_reaction: bool,
    ) -> None:
        """リアクションイベントを処理して DB に書き込む。

        Args:
            tenant_id: テナント ID
            channel_id: Discord チャンネル ID（文字列）
            message_id: Discord メッセージ ID（文字列）
            user_id: リアクションしたユーザーの Discord ID（文字列）
            emoji: discord.PartialEmoji オブジェクト
            member: discord.Member オブジェクト（on_raw_reaction_remove では None になりうる）
            action: "add" または "remove"
            is_bot_reaction: リアクションした主体が Bot 自身か（add 時に記録。remove では未使用）
        """
        if self._pool is None:
            logger.warning(
                "[reaction-writer] pool not initialized, skipping reaction tenant=%s msg=%s action=%s",
                tenant_id, message_id, action,
            )
            return

        schema = _schema(tenant_id)

        # emoji の種別判定
        is_custom = getattr(emoji, "id", None) is not None
        if is_custom:
            emoji_name: str = emoji.name or str(emoji.id)
            emoji_id: str | None = str(emoji.id)
            emoji_animated: bool = bool(getattr(emoji, "animated", False))
        else:
            emoji_name = emoji.name or ""
            emoji_id = None
            emoji_animated = False

        # reactor 表示名（member が None の場合は None）
        reactor_display_name: str | None = None
        if member is not None:
            reactor_display_name = (
                getattr(member, "display_name", None)
                or getattr(member, "name", None)
            )

        try:
            async with self._pool.acquire() as conn:
                # set_config(..., true) はトランザクション局所。明示トランザクション内で
                # set_config → SELECT → INSERT/DELETE を実行しないと RLS が空設定を見て失敗する
                # （ADR-072）。
                async with conn.transaction():
                    # テナントコンテキストをセット（RLS 用）
                    await conn.execute(
                        "SELECT set_config('app.tenant_id', $1, true)",
                        str(tenant_id),
                    )

                    # discord message_id から meta_message_id を特定
                    meta_message_row = await conn.fetchrow(
                        f"SELECT id FROM {schema}.meta_messages"
                        " WHERE message_id = $1 AND tenant_id = $2 LIMIT 1",
                        message_id,
                        tenant_id,
                    )
                    if meta_message_row is None:
                        logger.debug(
                            "[reaction-writer] meta_message not found tenant=%s msg=%s — skip",
                            tenant_id, message_id,
                        )
                        return

                    meta_message_id: int = meta_message_row["id"]

                    if action == "add":
                        await conn.execute(
                            f"""
                            INSERT INTO {schema}.meta_message_reactions
                                (tenant_id, meta_message_id, emoji_name, emoji_id,
                                 emoji_animated, reactor_discord_user_id,
                                 reactor_display_name, is_bot_reaction)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT ON CONSTRAINT uq_reaction_per_user_emoji DO NOTHING
                            """,
                            tenant_id,
                            meta_message_id,
                            emoji_name,
                            emoji_id,
                            emoji_animated,
                            user_id,
                            reactor_display_name,
                            is_bot_reaction,
                        )
                        logger.info(
                            "[reaction-writer] add tenant=%s meta_msg=%d emoji=%s user=%s",
                            tenant_id, meta_message_id, emoji_name, user_id,
                        )
                    elif action == "remove":
                        if emoji_id is not None:
                            await conn.execute(
                                f"""
                                DELETE FROM {schema}.meta_message_reactions
                                WHERE meta_message_id = $1
                                  AND emoji_name = $2
                                  AND emoji_id = $3
                                  AND reactor_discord_user_id = $4
                                """,
                                meta_message_id,
                                emoji_name,
                                emoji_id,
                                user_id,
                            )
                        else:
                            await conn.execute(
                                f"""
                                DELETE FROM {schema}.meta_message_reactions
                                WHERE meta_message_id = $1
                                  AND emoji_name = $2
                                  AND emoji_id IS NULL
                                  AND reactor_discord_user_id = $3
                                """,
                                meta_message_id,
                                emoji_name,
                                user_id,
                            )
                        logger.info(
                            "[reaction-writer] remove tenant=%s meta_msg=%d emoji=%s user=%s",
                            tenant_id, meta_message_id, emoji_name, user_id,
                        )
                    else:
                        logger.warning(
                            "[reaction-writer] unknown action=%s tenant=%s msg=%s",
                            action, tenant_id, message_id,
                        )
                        return

        except Exception:
            logger.warning(
                "[reaction-writer] DB 書き込み失敗 tenant=%s msg=%s action=%s",
                tenant_id, message_id, action, exc_info=True,
            )
            return

        # SSE で受信箱をリアルタイム更新
        await sse_pubsub.publish_inbox_update(tenant_id)
