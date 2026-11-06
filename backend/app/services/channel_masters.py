from __future__ import annotations

"""channel_masters の共通定義と、名簿（全社1つの表）の読み口。

名簿は `public.channel_masters` 1つ。tenant_id が NULL の行は共用（運営が管理）、
値がある行はその会社専用。会社ごとの「隠す」設定は
`public.channel_master_tenant_settings` に1行で持つ。

名簿の表を読み書きする SQL はこのファイルだけに置く（他のファイルは関数を呼ぶ）。
表名の文字列も、下の定数2つにだけ書く。
"""

from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CHANNEL_MASTERS_TABLE: Final[str] = "public.channel_masters"
CHANNEL_SETTINGS_TABLE: Final[str] = "public.channel_master_tenant_settings"
CONVERSION_ITEM_VALUES: Final[frozenset[str]] = frozenset({"baseline", "channel_whatsapp", "channel_instagram"})

CHANNEL_TYPE_ALIASES: Final[dict[str, str]] = {
    "whatsapp_personal": "whatsapp",
    "whatsapp_business": "whatsapp",
}

_COLUMNS = "id, tenant_id, platform, display_name, connection_type, is_active"


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


def _row_to_dict(row: Any, hidden_ids: set[int]) -> dict[str, Any]:
    return {
        "id": row[0],
        "platform": row[2],
        "display_name": row[3],
        "connection_type": row[4],
        "is_active": bool(row[5]),
        "is_shared": row[1] is None,
        "is_hidden": row[0] in hidden_ids,
    }


async def _hidden_ids(db: AsyncSession, tenant_id: int) -> set[int]:
    """自社が隠している名簿の行の番号。設定の行が無ければ空。"""
    result = await db.execute(
        text(
            f"SELECT channel_master_id FROM {CHANNEL_SETTINGS_TABLE} "
            f"WHERE tenant_id = :tenant_id AND is_hidden = true"
        ),
        {"tenant_id": tenant_id},
    )
    return {r[0] for r in result.fetchall()}


async def list_channels(db: AsyncSession, tenant_id: int, *, active_only: bool = True) -> list[dict[str, Any]]:
    """共用行＋自社行。各行に is_shared と is_hidden を付ける。ORDER BY platform。"""
    active_clause = " AND is_active = true" if active_only else ""
    result = await db.execute(
        text(
            f"SELECT {_COLUMNS} FROM {CHANNEL_MASTERS_TABLE} "
            f"WHERE (tenant_id IS NULL OR tenant_id = :tenant_id){active_clause} "
            f"ORDER BY platform"
        ),
        {"tenant_id": tenant_id},
    )
    rows = result.fetchall()
    hidden = await _hidden_ids(db, tenant_id)
    return [_row_to_dict(r, hidden) for r in rows]


async def get_channel(db: AsyncSession, tenant_id: int, platform: str) -> dict[str, Any] | None:
    """platform が一致し is_active の行（共用か自社）。無ければ None。"""
    result = await db.execute(
        text(
            f"SELECT {_COLUMNS} FROM {CHANNEL_MASTERS_TABLE} "
            f"WHERE platform = :platform AND is_active = true "
            f"AND (tenant_id IS NULL OR tenant_id = :tenant_id) "
            f"ORDER BY tenant_id IS NULL DESC, id"
        ),
        {"platform": platform, "tenant_id": tenant_id},
    )
    row = result.first()
    if row is None:
        return None
    hidden = await _hidden_ids(db, tenant_id)
    return _row_to_dict(row, hidden)


async def list_channels_for_picker(
    db: AsyncSession, tenant_id: int, *, keep_platform: str | None = None
) -> list[dict[str, Any]]:
    """list_channels から is_hidden の行を外す。ただし platform == keep_platform の行は残す。"""
    rows = await list_channels(db, tenant_id)
    return [r for r in rows if not r["is_hidden"] or (keep_platform is not None and r["platform"] == keep_platform)]


async def get_channel_by_id(db: AsyncSession, tenant_id: int, channel_master_id: int) -> dict[str, Any] | None:
    """id が一致し、共用か自社の行。他社行は None（＝404 にする）。"""
    result = await db.execute(
        text(
            f"SELECT {_COLUMNS} FROM {CHANNEL_MASTERS_TABLE} "
            f"WHERE id = :id AND (tenant_id IS NULL OR tenant_id = :tenant_id)"
        ),
        {"id": channel_master_id, "tenant_id": tenant_id},
    )
    row = result.first()
    if row is None:
        return None
    hidden = await _hidden_ids(db, tenant_id)
    return _row_to_dict(row, hidden)


async def set_hidden(
    db: AsyncSession, tenant_id: int, channel_master_id: int, is_hidden: bool, user_id: int
) -> None:
    """自社の「隠す」設定を UPSERT する。"""
    await db.execute(
        text(
            f"INSERT INTO {CHANNEL_SETTINGS_TABLE} "
            f"(tenant_id, channel_master_id, is_hidden, updated_at, updated_by_user_id) "
            f"SELECT :tenant_id, id, :is_hidden, CURRENT_TIMESTAMP, :user_id "
            f"FROM {CHANNEL_MASTERS_TABLE} "
            f"WHERE id = :channel_master_id AND (tenant_id IS NULL OR tenant_id = :tenant_id) "
            f"ON CONFLICT (tenant_id, channel_master_id) DO UPDATE SET "
            f"is_hidden = :is_hidden, updated_at = CURRENT_TIMESTAMP, updated_by_user_id = :user_id"
        ),
        {
            "tenant_id": tenant_id,
            "channel_master_id": channel_master_id,
            "is_hidden": is_hidden,
            "user_id": user_id,
        },
    )


async def conversion_items(db: AsyncSession) -> dict[str, str]:
    """共用行の {platform: conversion_item}。"""
    result = await db.execute(
        text(
            f"SELECT platform, conversion_item FROM {CHANNEL_MASTERS_TABLE} "
            f"WHERE tenant_id IS NULL AND conversion_item IS NOT NULL AND is_active = true"
        )
    )
    return {r[0]: r[1] for r in result.fetchall()}


async def platforms_by_store(db: AsyncSession, store: str) -> list[str]:
    """分析用。共用行で conversion_item があり、会話の置き場が store の platform。"""
    result = await db.execute(
        text(
            f"SELECT platform FROM {CHANNEL_MASTERS_TABLE} "
            f"WHERE tenant_id IS NULL AND conversion_item IS NOT NULL AND is_active = true "
            f"AND conversation_store = :store ORDER BY platform"
        ),
        {"store": store},
    )
    return [r[0] for r in result.fetchall()]
