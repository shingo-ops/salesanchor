"""ADR-1077 便2b: 秘書の決まり帳（public.secretary_rules）を読む・書く（design.md §4・§5）。

この表の SQL はこのファイルにだけ書く。commit は呼ぶ側（口）がする。
RLS（自社の会社文脈）に加えて、WHERE でも tenant_id を見る。
承認済みを数えて書く間は、会社ごとに pg_advisory_xact_lock(1077, tenant_id) で 1 本ずつにする（design.md §4。
会社の番号は 1 から始まるので、便3 の試しの鍵 (1077, 0) とは重ならない）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_APPROVED = 20  # 承認済みの上限（design.md §3「大きさ」・§4）
CANDIDATE_LIST_LIMIT = 100  # 候補の一覧に出す数（新しい順）
_LOCK_CLASS = 1077  # 鍵の 1 つ目の数（ADR-1077）


class RulesFull(Exception):
    """承認済みが MAX_APPROVED 件ある（口は 409 rules_full）。"""


class RuleNotFound(LookupError):
    """その番号の決まりが自社に無い（口は 404 rule_not_found）。"""


class RuleWrongStatus(Exception):
    """今の状態ではその操作ができない（口は 409 wrong_status）。"""


@dataclass(frozen=True)
class SecretaryRule:
    id: int
    status: str
    rule_text: str
    source_text: str | None
    source_kind: str | None
    source_reply: str | None
    created_at: datetime
    decided_at: datetime | None


_SELECT_APPROVED_TEXTS = text(
    "SELECT rule_text FROM public.secretary_rules "
    "WHERE tenant_id = :tenant_id AND status = 'approved' "
    "ORDER BY decided_at, id"
)
_SELECT_APPROVED = text(
    "SELECT id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at "
    "FROM public.secretary_rules "
    "WHERE tenant_id = :tenant_id AND status = 'approved' "
    "ORDER BY decided_at, id"
)
_SELECT_CANDIDATES = text(
    "SELECT id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at "
    "FROM public.secretary_rules "
    "WHERE tenant_id = :tenant_id AND status = 'candidate' "
    "ORDER BY id DESC LIMIT :limit"
)
_LOCK = text("SELECT pg_advisory_xact_lock(CAST(:lock_class AS integer), CAST(:tenant_id AS integer))")
_COUNT_APPROVED = text(
    "SELECT count(*) FROM public.secretary_rules WHERE tenant_id = :tenant_id AND status = 'approved'"
)
_INSERT_APPROVED = text(
    "INSERT INTO public.secretary_rules (tenant_id, status, rule_text, created_by, decided_by, decided_at) "
    "VALUES (:tenant_id, 'approved', :rule_text, :created_by, :decided_by, now()) "
    "RETURNING id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at"
)
_INSERT_CANDIDATE = text(
    "INSERT INTO public.secretary_rules "
    "(tenant_id, status, rule_text, source_text, source_kind, source_reply, created_by) "
    "VALUES (:tenant_id, 'candidate', :rule_text, :source_text, :source_kind, :source_reply, :created_by) "
    "RETURNING id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at"
)
_SELECT_STATUS = text("SELECT status FROM public.secretary_rules WHERE id = :rule_id AND tenant_id = :tenant_id")
_DECIDE = text(
    "UPDATE public.secretary_rules "
    "SET status = :to_status, rule_text = COALESCE(CAST(:rule_text AS text), rule_text), "
    "decided_by = :user_id, decided_at = now() "
    "WHERE id = :rule_id AND tenant_id = :tenant_id AND status = :from_status "
    "RETURNING id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at"
)


def _to_rule(row) -> SecretaryRule:
    return SecretaryRule(**dict(row))


async def list_approved_rule_texts(db: AsyncSession, tenant_id: int) -> list[str]:
    """秘書の容器へ送る承認済みの決まりの文（決めた時刻の古い順）。件数で切らない（上限は書く側で守る）。"""
    result = await db.execute(_SELECT_APPROVED_TEXTS, {"tenant_id": tenant_id})
    return [row[0] for row in result.all()]


async def list_rules(db: AsyncSession, tenant_id: int, status: str) -> list[SecretaryRule]:
    """一覧（approved は全部・決めた時刻の古い順。candidate は新しい順に CANDIDATE_LIST_LIMIT 件まで）。"""
    if status == "approved":
        result = await db.execute(_SELECT_APPROVED, {"tenant_id": tenant_id})
    elif status == "candidate":
        result = await db.execute(_SELECT_CANDIDATES, {"tenant_id": tenant_id, "limit": CANDIDATE_LIST_LIMIT})
    else:
        raise ValueError(f"unknown status: {status}")
    return [_to_rule(row) for row in result.mappings().all()]


async def _lock_and_count(db: AsyncSession, tenant_id: int) -> int:
    """会社ごとの鍵を取り（取引の終わりまで持つ）、承認済みの数を返す。"""
    await db.execute(_LOCK, {"lock_class": _LOCK_CLASS, "tenant_id": tenant_id})
    return (await db.execute(_COUNT_APPROVED, {"tenant_id": tenant_id})).scalar_one()


async def _status_of(db: AsyncSession, tenant_id: int, rule_id: int) -> str | None:
    result = await db.execute(_SELECT_STATUS, {"rule_id": rule_id, "tenant_id": tenant_id})
    return result.scalar_one_or_none()


async def add_approved_rule(db: AsyncSession, tenant_id: int, user_id: int, rule_text: str) -> SecretaryRule:
    """案の「承認」: いきなり approved で入れる（design.md §5（３））。20 件あれば RulesFull。"""
    if await _lock_and_count(db, tenant_id) >= MAX_APPROVED:
        raise RulesFull()
    params = {"tenant_id": tenant_id, "rule_text": rule_text, "created_by": user_id, "decided_by": user_id}
    row = (await db.execute(_INSERT_APPROVED, params)).mappings().one()
    return _to_rule(row)


async def add_candidate(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    rule_text: str,
    source_text: str,
    source_kind: str,
    source_reply: str | None,
) -> SecretaryRule:
    """答えの「違う」: その 1 往復を candidate で入れる（design.md §5（４））。"""
    params = {
        "tenant_id": tenant_id,
        "rule_text": rule_text,
        "source_text": source_text,
        "source_kind": source_kind,
        "source_reply": source_reply,
        "created_by": user_id,
    }
    row = (await db.execute(_INSERT_CANDIDATE, params)).mappings().one()
    return _to_rule(row)


async def _decide(
    db: AsyncSession,
    tenant_id: int,
    rule_id: int,
    user_id: int,
    from_status: str,
    to_status: str,
    rule_text: str | None = None,
) -> SecretaryRule:
    params = {
        "to_status": to_status,
        "rule_text": rule_text,
        "user_id": user_id,
        "rule_id": rule_id,
        "tenant_id": tenant_id,
        "from_status": from_status,
    }
    row = (await db.execute(_DECIDE, params)).mappings().first()
    if row is None:
        current = await _status_of(db, tenant_id, rule_id)
        if current is None:
            raise RuleNotFound(rule_id)
        raise RuleWrongStatus(current)
    return _to_rule(row)


async def approve_candidate(
    db: AsyncSession, tenant_id: int, rule_id: int, user_id: int, rule_text: str
) -> SecretaryRule:
    """候補を文を付けて approved にする（design.md §5（５））。番号が無い・候補でないを先に見てから 20 件を見る。"""
    if await _lock_and_count(db, tenant_id) >= MAX_APPROVED:
        current = await _status_of(db, tenant_id, rule_id)
        if current is None:
            raise RuleNotFound(rule_id)
        if current != "candidate":
            raise RuleWrongStatus(current)
        raise RulesFull()
    return await _decide(db, tenant_id, rule_id, user_id, "candidate", "approved", rule_text)


async def reject_candidate(db: AsyncSession, tenant_id: int, rule_id: int, user_id: int) -> SecretaryRule:
    """候補を捨てる（candidate → rejected）。"""
    return await _decide(db, tenant_id, rule_id, user_id, "candidate", "rejected")


async def remove_rule(db: AsyncSession, tenant_id: int, rule_id: int, user_id: int) -> SecretaryRule:
    """決まりを外す（approved → removed）。次の頼みから容器へ送らない（R4）。"""
    return await _decide(db, tenant_id, rule_id, user_id, "approved", "removed")
