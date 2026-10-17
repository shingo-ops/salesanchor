"""閲覧者（社外の在庫閲覧専用アカウント）の管理（ADR-1019 段4a-2）。

状態の変更・一覧・ログイン記録・初期登録。raw SQL（text()）で public.viewer_accounts 等を扱う。
commit はしない（呼び出し側が commit する）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.viewer_email import normalize_viewer_email

ACTOR_PO = "po"
ACTOR_CLAUDE = "claude"

_ACTIONS = ("activate", "suspend", "unsuspend", "extend")
_JST = timezone(timedelta(hours=9))
_TRIAL_DAYS = 14
_LOGIN_LIST_LIMIT = 500


class ViewerAdminError(Exception):
    """code: "not_found" | "conflict" | "invalid_days"。"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(timezone.utc)


# 目印①: ある時点から遡って24時間以内に、成功ログインの IP が3種類以上
# 目印②: 成功ログインの IP が別の閲覧者の成功ログインにもある
_LIST_SQL = """
SELECT v.id, v.email, v.line_name, v.inventory_issue, v.status, v.trial_expires_at,
       v.created_at, v.discord_user_id, v.discord_channel_id,
       (SELECT c.guild_id FROM public.viewer_discord_config c WHERE c.id = 1) AS discord_guild_id,
       EXISTS (
         SELECT 1 FROM public.viewer_login_events e1
         WHERE e1.viewer_id = v.id AND e1.event_type = 'login_succeeded'
           AND (
             SELECT count(DISTINCT e2.client_ip) FROM public.viewer_login_events e2
             WHERE e2.viewer_id = v.id AND e2.event_type = 'login_succeeded'
               AND e2.client_ip IS NOT NULL
               AND e2.created_at > e1.created_at - interval '24 hours'
               AND e2.created_at <= e1.created_at
           ) >= 3
       ) AS flag_many_ips,
       EXISTS (
         SELECT 1 FROM public.viewer_login_events e3
         JOIN public.viewer_login_events e4
           ON e4.client_ip = e3.client_ip AND e4.event_type = 'login_succeeded'
          AND e4.viewer_id <> e3.viewer_id
         WHERE e3.viewer_id = v.id AND e3.event_type = 'login_succeeded'
           AND e3.client_ip IS NOT NULL
       ) AS flag_shared_ip
FROM public.viewer_accounts v
{where}
ORDER BY v.created_at DESC, v.id DESC
"""


def _item(row) -> dict:
    d = dict(row)
    d["flag_many_ips"] = bool(d["flag_many_ips"])
    d["flag_shared_ip"] = bool(d["flag_shared_ip"])
    guild = d.pop("discord_guild_id", None)
    channel = d.get("discord_channel_id")
    d["discord_channel_url"] = (
        f"https://discord.com/channels/{guild}/{channel}" if guild and channel else None
    )
    return d


async def _get_item(db: AsyncSession, viewer_id: int) -> dict:
    res = await db.execute(text(_LIST_SQL.format(where="WHERE v.id = :id")), {"id": viewer_id})
    row = res.mappings().first()
    if row is None:
        raise ViewerAdminError("not_found")
    return _item(row)


async def list_viewers(db: AsyncSession, now: datetime | None = None) -> list[dict]:
    res = await db.execute(text(_LIST_SQL.format(where="")))
    return [_item(r) for r in res.mappings().all()]


async def list_logins(db: AsyncSession, viewer_id: int) -> list[dict]:
    exists = await db.execute(
        text("SELECT 1 FROM public.viewer_accounts WHERE id = :id"), {"id": viewer_id}
    )
    if exists.first() is None:
        raise ViewerAdminError("not_found")
    res = await db.execute(
        text(
            "SELECT created_at, event_type, client_ip, user_agent "
            "FROM public.viewer_login_events WHERE viewer_id = :id "
            "ORDER BY created_at DESC, id DESC LIMIT :lim"
        ),
        {"id": viewer_id, "lim": _LOGIN_LIST_LIMIT},
    )
    return [dict(r) for r in res.mappings().all()]


async def change_status(
    db: AsyncSession,
    viewer_id: int,
    action: str,
    *,
    actor: str,
    actor_user_id: int | None,
    days: int | None = None,
    now: datetime | None = None,
) -> dict:
    if action not in _ACTIONS:
        raise ValueError("unsupported action")
    current = _now(now)

    row = (
        await db.execute(
            text(
                "SELECT id, status, trial_expires_at FROM public.viewer_accounts "
                "WHERE id = :id FOR UPDATE"
            ),
            {"id": viewer_id},
        )
    ).mappings().first()
    if row is None:
        raise ViewerAdminError("not_found")

    if action == "extend" and (
        isinstance(days, bool) or not isinstance(days, int) or days < 1
    ):
        raise ViewerAdminError("invalid_days")

    from_status = row["status"]
    from_expires = row["trial_expires_at"]
    to_status = from_status
    to_expires = from_expires
    extend_days: int | None = None

    if action == "activate":
        if from_status != "trial":
            raise ViewerAdminError("conflict")
        to_status = "active"
    elif action == "suspend":
        if from_status == "suspended":
            raise ViewerAdminError("conflict")
        to_status = "suspended"
    elif action == "unsuspend":
        if from_status != "suspended":
            raise ViewerAdminError("conflict")
        last = (
            await db.execute(
                text(
                    "SELECT from_status FROM public.viewer_status_changes "
                    "WHERE viewer_id = :id AND action = 'suspend' "
                    "ORDER BY created_at DESC, id DESC LIMIT 1"
                ),
                {"id": viewer_id},
            )
        ).first()
        if last is None or last[0] is None:
            raise ViewerAdminError("conflict")
        to_status = last[0]
    else:  # extend
        if from_status != "trial":
            raise ViewerAdminError("conflict")
        to_expires = current + timedelta(days=days)
        extend_days = days

    await db.execute(
        text(
            "UPDATE public.viewer_accounts SET status = :status, "
            "trial_expires_at = :expires, updated_at = :now WHERE id = :id"
        ),
        {"status": to_status, "expires": to_expires, "now": current, "id": viewer_id},
    )
    await db.execute(
        text(
            "INSERT INTO public.viewer_status_changes "
            "(viewer_id, action, from_status, to_status, from_expires_at, to_expires_at, "
            "extend_days, actor, actor_user_id, created_at) "
            "VALUES (:vid, :action, :from_status, :to_status, :from_expires, :to_expires, "
            ":extend_days, :actor, :actor_user_id, :now)"
        ),
        {
            "vid": viewer_id,
            "action": action,
            "from_status": from_status,
            "to_status": to_status,
            "from_expires": from_expires,
            "to_expires": to_expires,
            "extend_days": extend_days,
            "actor": actor,
            "actor_user_id": actor_user_id,
            "now": current,
        },
    )
    return await _get_item(db, viewer_id)


async def change_status_by_email(
    db: AsyncSession,
    email: str,
    action: str,
    *,
    actor: str,
    days: int | None = None,
    now: datetime | None = None,
) -> dict:
    try:
        normalized = normalize_viewer_email(email)
    except (ValueError, AttributeError):
        raise ViewerAdminError("not_found") from None
    row = (
        await db.execute(
            text("SELECT id FROM public.viewer_accounts WHERE lower(email) = lower(:email)"),
            {"email": normalized},
        )
    ).first()
    if row is None:
        raise ViewerAdminError("not_found")
    return await change_status(
        db, row[0], action, actor=actor, actor_user_id=None, days=days, now=now
    )


def _parse_applied_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_JST)
    return parsed


async def register_initial(
    db: AsyncSession, rows: list[dict], *, now: datetime | None = None
) -> dict:
    """初期の閲覧者を登録する。メール・名前は戻り値にもログにも出さない。"""
    registered = skipped = failed = 0
    for item in rows:
        try:
            async with db.begin_nested():
                email = normalize_viewer_email(item["email"])
                line_name = item["line_name"]
                status = item["status"]
                if not isinstance(line_name, str) or not line_name.strip():
                    raise ValueError("line_name")
                if status not in ("trial", "active"):
                    raise ValueError("status")
                applied = _parse_applied_at(item["applied_at"])
                dup = await db.execute(
                    text("SELECT 1 FROM public.viewer_accounts WHERE lower(email) = lower(:email)"),
                    {"email": email},
                )
                if dup.first() is not None:
                    skipped += 1
                    continue
                expires = applied + timedelta(days=_TRIAL_DAYS) if status == "trial" else None
                await db.execute(
                    text(
                        "INSERT INTO public.viewer_accounts "
                        "(email, line_name, status, trial_expires_at) "
                        "VALUES (:email, :line_name, :status, :expires)"
                    ),
                    {"email": email, "line_name": line_name, "status": status, "expires": expires},
                )
                registered += 1
        except Exception:
            failed += 1
    return {"registered": registered, "skipped": skipped, "failed": failed}
