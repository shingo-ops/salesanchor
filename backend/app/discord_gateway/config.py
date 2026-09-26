import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SingleBotConfig:
    bot_token: str


def load_single_bot_config() -> SingleBotConfig:
    """環境変数から共通 Bot トークンをロードする (ADR-146 B方式)。

    形式: DISCORD_BOT_TOKEN=<token>

    未設定・空の場合は RuntimeError を送出する。
    """
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN が未設定です。"
            " B方式ではテナント共通の単一トークンが必須です (ADR-146)。"
        )
    return SingleBotConfig(bot_token=token)


def get_log_level() -> str:
    return os.environ.get("DISCORD_GATEWAY_LOG_LEVEL", "INFO").upper()
