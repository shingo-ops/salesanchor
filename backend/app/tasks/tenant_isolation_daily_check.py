"""ADR-1063 便6（K9）: 会社の分け方（RLS）が本番で崩れていないかを毎日点検し、管理者用 Discord に送る。

見るもの（設計 docs/handoff/tenant-owner-login-approval/design.md「便6」）:
  1. アプリの接続している役が superuser でも BYPASSRLS でもない。
  2. RLS を飛び越せる役（BYPASSRLS・superuser）が、許可一覧 BYPASSRLS_ROLES に無いものを含まない。
     許可一覧が空の間は「黄（一覧未固定）」で、見つけた役の名前を書くだけ。
  3. public の tenant_id 付きで RLS の無い表が、許可一覧 PUBLIC_TABLES_WITHOUT_RLS に無いものを含まない。
緑のときも毎日 1 通送る（届かない＝止まっている、と区別するため）。鍵・接続の文字列は書かない。DB は読むだけ。
判定は CI の点検（scripts/check_public_tenant_rls.py）と同じ: 許可一覧に無いものが増えたら赤、減ったものは（参考）。
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from celery import shared_task
from sqlalchemy import text

from app.ops.tenant_rls_allowlist import BYPASSRLS_ROLES, PUBLIC_TABLES_WITHOUT_RLS
from app.ops.tenant_rls_checks import (
    CURRENT_ROLE_SQL,
    PUBLIC_TABLES_WITHOUT_RLS_SQL,
    RLS_BYPASS_ROLES_SQL,
)

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"

_HEAD = {
    "green": "✅ 会社の分け方の毎日点検（ADR-1063 K9）: 3 項目とも合格",
    "yellow": "🟡 会社の分け方の毎日点検（ADR-1063 K9）: 役の許可一覧が未固定（項目2 は名前を書くだけ）",
    "red": "🔴 会社の分け方の毎日点検（ADR-1063 K9）: 崩れあり",
}


async def collect(conn) -> dict:
    """DB から 3 項目の材料を読む。conn は SQLAlchemy の非同期接続。"""
    me = (await conn.execute(text(CURRENT_ROLE_SQL))).one()
    roles = [row[0] for row in (await conn.execute(text(RLS_BYPASS_ROLES_SQL))).all()]
    tables = [row[0] for row in (await conn.execute(text(PUBLIC_TABLES_WITHOUT_RLS_SQL))).all()]
    return {
        "current_role": me[0],
        "current_super": bool(me[1]),
        "current_bypass": bool(me[2]),
        "bypass_roles": roles,
        "tables": tables,
    }


def judge(
    facts: dict, role_allowlist: dict[str, str], table_allowlist: dict[str, str]
) -> tuple[str, list[str], list[str]]:
    """(色, 崩れた項目, 参考) を返す。色は green / yellow / red。"""
    broken: list[str] = []
    notes: list[str] = []
    if facts["current_super"] or facts["current_bypass"]:
        broken.append(f"項目1: アプリの接続している役 {facts['current_role']} が RLS を飛び越せる")
    unpinned = not role_allowlist
    if not unpinned:
        extra_roles = sorted(set(facts["bypass_roles"]) - set(role_allowlist))
        gone_roles = sorted(set(role_allowlist) - set(facts["bypass_roles"]))
        if extra_roles:
            broken.append("項目2: 許可一覧に無い RLS を飛び越せる役: " + ", ".join(extra_roles))
        if gone_roles:
            notes.append("（参考）許可一覧にあるが見つからない役: " + ", ".join(gone_roles))
    extra_tables = sorted(set(facts["tables"]) - set(table_allowlist))
    gone_tables = sorted(set(table_allowlist) - set(facts["tables"]))
    if extra_tables:
        broken.append("項目3: 許可一覧に無い RLS の無い表: " + ", ".join(extra_tables))
    if gone_tables:
        notes.append("（参考）許可一覧にあるが見つからない表: " + ", ".join(gone_tables))
    if broken:
        color = "red"
    elif unpinned:
        color = "yellow"
    else:
        color = "green"
    return color, broken, notes


def build_message(color: str, broken: list[str], notes: list[str], facts: dict) -> str:
    roles = facts["bypass_roles"]
    lines = [
        _HEAD[color],
        f"アプリの接続している役: {facts['current_role']}",
        f"RLS を飛び越せる役: {len(roles)} 件（{', '.join(roles) if roles else 'なし'}）",
        f"RLS の無い表: {len(facts['tables'])} 件（許可一覧 {len(PUBLIC_TABLES_WITHOUT_RLS)} 件）",
    ]
    lines.extend(broken)
    lines.extend(notes)
    return "\n".join(lines)


async def _post_discord(content: str) -> None:
    url = (os.getenv(_WEBHOOK_ENV) or "").strip()
    if not url:
        logger.warning("%s is not set; skip tenant isolation daily check report", _WEBHOOK_ENV)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json={"content": content[:1800], "username": "会社の分け方 毎日点検"})
        if res.status_code >= 400:
            logger.warning("tenant isolation daily check: discord status %s", res.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("tenant isolation daily check: discord error %s", type(exc).__name__)


async def _run_check() -> dict:
    from app.database import engine

    try:
        async with engine.connect() as conn:
            facts = await collect(conn)
    except Exception as exc:  # noqa: BLE001
        # 点検が動けなかったことも毎日の 1 通で知らせる（届かない日と区別するため）。中身の文は書かない。
        await _post_discord(f"🔴 会社の分け方の毎日点検（ADR-1063 K9）: 点検が動けなかった（{type(exc).__name__}）")
        raise
    color, broken, notes = judge(facts, BYPASSRLS_ROLES, PUBLIC_TABLES_WITHOUT_RLS)
    await _post_discord(build_message(color, broken, notes, facts))
    return {"color": color, "broken": broken, "notes": notes, "facts": facts}


@shared_task(name="app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check")
def run_tenant_isolation_daily_check() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_check())
    finally:
        asyncio.run(engine.dispose())
