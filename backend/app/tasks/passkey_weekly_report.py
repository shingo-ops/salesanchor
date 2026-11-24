"""ADR-1013 パスキーの週報: 全社の管理者のログイン成功を週1回数え、管理者用 Discord に送る。

設計: docs/handoff/passkey-autofill-first/sustain-design.md §5-1。
区切りは日本時間の暦日。月曜の回は、前の週の月曜 00:00〜日曜 24:00（7日）と、その日曜 24:00 までの30日。
数える人は public.users の is_super_admin が true の人だけ。通知には id だけを書く（名前・メール・IP・端末は書かない）。
割合はパスキー÷(パスキー＋パスワード)（docs/specs/auth-login/kgi.md の KPI の測り方）。知らない機械の確認や復旧を通ったログインは割合に入れず、件数だけ添える。
毎回送る（届かない＝止まっている）。DB は読むだけ。
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from celery import shared_task
from sqlalchemy import text

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"
_JST = ZoneInfo("Asia/Tokyo")

PASSKEY_PATH = "/api/v1/auth/passkey/login/verify"
LOGIN_PATH = "/api/v1/auth/login"
POLL_PATH = "/api/v1/auth/login-requests/poll"
RECOVERY_PATH = "/api/v1/auth/login-requests/recovery"
POLL_APPROVED = ("approved_admin", "approved_device")
KINDS = ("passkey", "password", "other")

ADMINS_SQL = "SELECT id FROM public.users WHERE is_super_admin ORDER BY id"
EVENTS_SQL = (
    "SELECT e.user_id, e.path, e.status_code, e.reason, e.created_at "
    "FROM public.auth_events e "
    "JOIN public.users u ON u.id = e.user_id "
    "WHERE u.is_super_admin "
    "AND e.created_at >= :start AND e.created_at < :end "
    "AND e.path IN ('/api/v1/auth/passkey/login/verify', '/api/v1/auth/login', "
    "'/api/v1/auth/login-requests/poll', '/api/v1/auth/login-requests/recovery')"
)


def windows(now: datetime) -> tuple[datetime, datetime, datetime]:
    """(30日の始め, 7日の始め, 終わり) を返す。終わり＝now 以前で最も近い日本時間の月曜 00:00。"""
    local = now.astimezone(_JST)
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = day - timedelta(days=local.weekday())
    return end - timedelta(days=30), end - timedelta(days=7), end


def classify(path: str, status_code: int, reason: str | None) -> str | None:
    """1件を passkey（パスキー）／password（パスワード）／other（確認・復旧）／None（数えない）に分ける。"""
    if path == PASSKEY_PATH and status_code == 200:
        return "passkey"
    if path == LOGIN_PATH and status_code == 200:
        return "password"
    if path == POLL_PATH and reason in POLL_APPROVED:
        return "other"
    if path == RECOVERY_PATH and status_code == 200:
        return "other"
    return None


def tally(
    admin_ids: list[int], rows: list[tuple], start30: datetime, start7: datetime, end: datetime
) -> dict[int, dict[str, dict[str, int]]]:
    """人ごとに 7日・30日の回数を数える。管理者でない人の行と数えない行は捨てる。"""
    out = {uid: {"7": dict.fromkeys(KINDS, 0), "30": dict.fromkeys(KINDS, 0)} for uid in admin_ids}
    for user_id, path, status_code, reason, created_at in rows:
        kind = classify(path, status_code, reason)
        if kind is None or user_id not in out:
            continue
        if start30 <= created_at < end:
            out[user_id]["30"][kind] += 1
        if start7 <= created_at < end:
            out[user_id]["7"][kind] += 1
    return out


def ratio(c: dict[str, int]) -> str:
    denom = c["passkey"] + c["password"]
    if denom == 0:
        return "-"
    return f"{round(c['passkey'] * 100 / denom)}%"


def build_message(
    counts: dict[int, dict[str, dict[str, int]]], start30: datetime, start7: datetime, end: datetime
) -> str:
    last = end - timedelta(days=1)
    lines = [
        f"🔑 パスキーの週報（ADR-1013）: 7日 {start7:%m/%d}〜{last:%m/%d}・30日 {start30:%m/%d}〜{last:%m/%d}（日本時間）",
        "割合＝パスキー÷(パスキー＋パスワード)。確認＝知らない機械の確認や復旧を通ったログイン（割合に入れない）",
    ]
    if not counts:
        lines.append("全社の管理者: 0 人")
    for uid in sorted(counts):
        c7, c30 = counts[uid]["7"], counts[uid]["30"]
        lines.append(
            f"id {uid}: 7日 パスキー {c7['passkey']}・パスワード {c7['password']}・割合 {ratio(c7)}・確認 {c7['other']}"
            f" ／ 30日 パスキー {c30['passkey']}・パスワード {c30['password']}・割合 {ratio(c30)}・確認 {c30['other']}"
        )
    return "\n".join(lines)


async def collect(conn, start30: datetime, end: datetime) -> tuple[list[int], list[tuple]]:
    """DB から管理者の id と、30日分の記録を読む。conn は SQLAlchemy の非同期接続。"""
    admin_ids = [row[0] for row in (await conn.execute(text(ADMINS_SQL))).all()]
    rows = [tuple(row) for row in (await conn.execute(text(EVENTS_SQL), {"start": start30, "end": end})).all()]
    return admin_ids, rows


async def _post_discord(content: str) -> None:
    url = (os.getenv(_WEBHOOK_ENV) or "").strip()
    if not url:
        logger.warning("%s is not set; skip passkey weekly report", _WEBHOOK_ENV)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json={"content": content[:1800], "username": "パスキーの週報"})
        if res.status_code >= 400:
            logger.warning("passkey weekly report: discord status %s", res.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("passkey weekly report: discord error %s", type(exc).__name__)


async def _run_report(now: datetime | None = None) -> dict:
    from app.database import engine

    start30, start7, end = windows(now or datetime.now(UTC))
    try:
        async with engine.connect() as conn:
            admin_ids, rows = await collect(conn, start30, end)
    except Exception as exc:  # noqa: BLE001
        # 数えられなかったことも1通で知らせる（届かない週と区別するため）。中身の文は書かない。
        await _post_discord(f"🔴 パスキーの週報（ADR-1013）: 数えられなかった（{type(exc).__name__}）")
        raise
    counts = tally(admin_ids, rows, start30, start7, end)
    await _post_discord(build_message(counts, start30, start7, end))
    return {
        "counts": counts,
        "start30": start30.isoformat(),
        "start7": start7.isoformat(),
        "end": end.isoformat(),
    }


@shared_task(name="app.tasks.passkey_weekly_report.run_passkey_weekly_report")
def run_passkey_weekly_report() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_report())
    finally:
        asyncio.run(engine.dispose())
