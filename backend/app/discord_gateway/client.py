"""Discord Bot Gateway client — B方式: 共通bot1台 + guild_id振り分け (ADR-146).

A方式（テナント別bot）から B方式（共通bot + guild_id → tenant_id 逆引き）へ移行。

受信フロー:
  on_message(guild) → _resolve_tenant_id(guild_id) → ticket_channel_writer(tenant_id)

DM は B方式の対象外（guild_id を持たないため逆引き不能 — ADR-146 F7/PO決定）。

在庫受信コード（_process_message / _resume_missed_messages / _process_dm_message）は
ADR-146 案ア により削除せず休眠のまま残す。在庫移行プロジェクトで後日再設計する。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import discord
from sqlalchemy import text

from app.discord_gateway import (
    ticket_channel_creator,
    ticket_channel_writer,
)
from app.discord_gateway.config import SingleBotConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JarvisDiscordClient (ADR-146 B方式)
# ---------------------------------------------------------------------------


class JarvisDiscordClient(discord.Client):
    """ADR-146 B方式: 共通bot1台で全テナントのguildを受信し guild_id でテナントを振り分ける。

    - on_message(guild):  _resolve_tenant_id(guild_id) → ticket_channel_writer
    - on_message(DM):     スキップ（B方式対象外 — F7/PO決定）
    - on_resumed:         no-op（在庫補完は案ア休眠中 — ADR-146）
    - on_interaction:     guild_id → tenant_id 逆引き → ticket_channel_creator
    """

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any] | None = None,
    ) -> None:
        """Args:
            db_factory: AsyncSession factory（テスト時に差し込み可能）。
                None なら `app.database.AsyncSessionLocal` を遅延 import。
        """
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True
        intents.members = True
        # DM は B方式対象外のため dm_messages intent は不要
        super().__init__(intents=intents)
        self._db_factory_override = db_factory
        self._resumed_completed: set[str] = set()

    # --- helpers ---------------------------------------------------------

    def _db_factory(self) -> Any:
        if self._db_factory_override is not None:
            return self._db_factory_override
        from app.database import AsyncSessionLocal
        return AsyncSessionLocal

    async def _resolve_tenant_id(self, guild_id: str) -> int | None:
        """guild_id から tenant_id を逆引きする (ADR-146 K2/K3).

        public.tenant_discord_config.guild_id → tenant_id の1対1マッピング。
        UNIQUE(guild_id) 制約はマイグレーション 20260626_120000 で付与済み。
        未登録 guild は None を返す（ログのみ・例外なし）。
        """
        db_factory = self._db_factory()
        try:
            async with db_factory() as session:  # type: ignore[misc]
                result = await session.execute(
                    text(
                        "SELECT tenant_id FROM public.tenant_discord_config"
                        " WHERE guild_id = :gid LIMIT 1"
                    ),
                    {"gid": guild_id},
                )
                row = result.fetchone()
                return int(row[0]) if row else None
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "[discord-gateway] tenant_id 逆引き失敗 guild_id=%s: %s",
                guild_id,
                exc,
            )
            return None

    # --- event handlers --------------------------------------------------

    async def on_ready(self) -> None:
        user = self.user
        logger.info(
            "[discord-gateway] READY (ADR-146 B方式) bot=%s#%s id=%s guilds=%d",
            user.name if user else "?",
            user.discriminator if user else "?",
            user.id if user else "?",
            len(self.guilds),
        )

    async def on_resumed(self) -> None:
        """在庫補完は ADR-146 案ア により休眠中。no-op."""
        logger.info(
            "[discord-gateway] RESUMED — 在庫 missed-message 補完は休眠中 (ADR-146 案ア)"
        )

    async def on_disconnect(self) -> None:
        logger.warning("[discord-gateway] DISCONNECT")

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """ボタン押下: ticket_open ボタンでプライベートチャンネルを自動発行する。

        B方式: guild_id → _resolve_tenant_id() でテナントを動的に解決する。
        custom_id が "ticket_open" で始まるボタン操作のみ処理する。
        """
        if interaction.type != discord.InteractionType.component:
            return
        custom_id: str = (interaction.data or {}).get("custom_id", "")  # type: ignore[arg-type]
        if not custom_id.startswith("ticket_open"):
            return

        # 3 秒以内に応答しないと Discord がタイムアウトするため先に defer
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            return

        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.followup.send(
                "サーバー内でのみ利用できます。", ephemeral=True
            )
            return

        # B方式: guild_id から tenant_id を動的解決
        tenant_id = await self._resolve_tenant_id(str(guild.id))
        if tenant_id is None:
            logger.warning(
                "[ticket] unknown guild_id=%s — tenant 未登録のため ticket 発行スキップ",
                guild.id,
            )
            await interaction.followup.send(
                "このサーバーは未登録です。管理者にお問い合わせください。",
                ephemeral=True,
            )
            return

        db_factory = self._db_factory()
        async with db_factory() as session:
            config = await ticket_channel_creator.get_ticket_config(
                session, tenant_id
            )

        if config is None:
            logger.warning(
                "[ticket] config not set tenant_id=%d guild_id=%s", tenant_id, guild.id
            )
            await interaction.followup.send(
                "チケット機能が設定されていません。管理者にお問い合わせください。",
                ephemeral=True,
            )
            return

        channel = await ticket_channel_creator.get_or_create_ticket_channel(
            guild=guild,
            config=config,
            member=member,
            tenant_id=tenant_id,
            db_factory=db_factory,
        )

        if channel is None:
            await interaction.followup.send(
                "チャンネルの作成に失敗しました。管理者にお問い合わせください。",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"We've set up a private channel just for you → {channel.mention}",
            ephemeral=True,
        )
        logger.info(
            "[ticket] interaction handled tenant_id=%d guild_id=%s user=%s channel=%s",
            tenant_id,
            guild.id,
            member.id,
            channel.id,
        )

    async def on_message(self, message: discord.Message) -> None:  # type: ignore[override]
        """MESSAGE_CREATE: guild メッセージのみ処理する (ADR-146 B方式).

        DM (guild=None): B方式対象外のためスキップ（F7/PO決定）。
        Guild メッセージ: guild_id → tenant_id 逆引き → ticket_channel_writer。
        """
        if getattr(message.author, "bot", False):
            return
        if message.guild is None:
            # DM は B方式対象外（guild_id を持たないため逆引き不能）
            logger.debug("[discord-gateway] DM skipped (B方式対象外 ADR-146 F7)")
            return
        await self._process_guild_message(message)

    async def _process_guild_message(self, message: discord.Message) -> None:
        """guild メッセージを guild_id → tenant_id 逆引きして ticket_channel_writer に委譲する."""
        guild_id = str(message.guild.id)  # type: ignore[union-attr]
        tenant_id = await self._resolve_tenant_id(guild_id)
        if tenant_id is None:
            logger.info(
                "[discord-gateway] unknown guild_id=%s — 未登録 guild のため無視",
                guild_id,
            )
            return

        try:
            await ticket_channel_writer.process_ticket_channel_message(
                self._db_factory(),
                tenant_id=tenant_id,
                message=message,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[discord-gateway] ticket channel routing failed tenant_id=%d msg=%s: %s",
                tenant_id,
                getattr(message, "id", "?"),
                exc,
                exc_info=True,
            )

    # --- 案ア 休眠スタブ（在庫移行プロジェクトで再設計予定 ADR-146）----------

    async def _process_dm_message(self, message: discord.Message) -> None:  # noqa: ARG002
        """DM 受信箱記録 — 休眠中 (ADR-146 案ア)."""
        logger.debug("[discord-gateway] _process_dm_message: 休眠中 (ADR-146 案ア)")

    async def _process_message(self, message: discord.Message) -> None:  # noqa: ARG002
        """在庫受信 inbound_writer 経路 — 休眠中 (ADR-146 案ア)."""
        logger.debug("[discord-gateway] _process_message: 休眠中 (ADR-146 案ア)")

    async def _resume_missed_messages(self) -> None:
        """missed messages 補完 — 休眠中 (ADR-146 案ア)."""
        logger.debug("[discord-gateway] _resume_missed_messages: 休眠中 (ADR-146 案ア)")


_MAX_RECONNECT_ATTEMPTS = 10


async def run_gateway(config: SingleBotConfig) -> None:
    """共通 Gateway 接続を維持する (ADR-146 B方式).

    reconnect=False で discord.py 内部の無制限再接続を無効化し、
    外側の while ループが指数バックオフで再接続を管理する。
    """
    backoff = 5
    max_backoff = 60
    reconnect_count = 0
    while True:
        client = JarvisDiscordClient()
        try:
            await client.start(config.bot_token, reconnect=False)
        except discord.LoginFailure:
            logger.critical(
                "[discord-gateway] LoginFailure — Token 不正/失効。"
                "Discord Developer Portal で Token を再発行し GitHub Secrets を更新すること"
            )
            raise
        except asyncio.CancelledError:
            logger.info("[discord-gateway] CancelledError — shutdown")
            await client.close()
            raise
        except Exception as exc:
            reconnect_count += 1
            logger.exception(
                "[discord-gateway] 例外発生 exc_type=%s, %d 秒後に再起動 (attempt %d/%d)",
                type(exc).__name__,
                backoff,
                reconnect_count,
                _MAX_RECONNECT_ATTEMPTS,
            )
            if reconnect_count >= _MAX_RECONNECT_ATTEMPTS:
                logger.critical(
                    "[discord-gateway] 最大再接続回数 (%d) を超えました — "
                    "手動で Bot Token を確認し再起動してください",
                    _MAX_RECONNECT_ATTEMPTS,
                )
                raise RuntimeError(
                    "Discord gateway max reconnect attempts reached"
                ) from exc
            try:
                await client.close()
            except Exception:
                pass
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
        else:
            reconnect_count = 0
            logger.info(
                "[discord-gateway] 正常切断 — %d 秒後に再接続",
                backoff,
            )
            try:
                await client.close()
            except Exception:
                pass
            await asyncio.sleep(backoff)
