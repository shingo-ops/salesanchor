from __future__ import annotations

"""channel_masters の共通定義。

リードの流入元統制で使う標準チャネルの seed と、互換用の正規化を集約する。
"""

from typing import Final

DEFAULT_CHANNEL_MASTERS: Final[tuple[tuple[str, str, str], ...]] = (
    ("messenger", "Messenger", "auto"),
    ("instagram", "Instagram", "auto"),
    ("discord", "Discord", "auto"),
    ("phone", "電話", "manual"),
    ("in_person", "対面", "manual"),
    ("whatsapp", "WhatsApp", "manual"),
)

ACTIVE_CHANNEL_PLATFORMS: Final[frozenset[str]] = frozenset(platform for platform, _, _ in DEFAULT_CHANNEL_MASTERS)

CHANNEL_TYPE_ALIASES: Final[dict[str, str]] = {
    "whatsapp_personal": "whatsapp",
    "whatsapp_business": "whatsapp",
}


def normalize_channel_type_value(value: str | None) -> str | None:
    """既知の別名だけ canonical 値へ寄せる。

    それ以外の値は現状互換のためそのまま返す。空文字は None 化する。
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return CHANNEL_TYPE_ALIASES.get(stripped, stripped)
