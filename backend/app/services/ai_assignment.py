"""ADR-1058: AI の担当表を読む所（ここ1か所だけ。design.md §4-3）。

行が無ければ AiAssignmentMissing を上げる（既定値に逃げない）。sync 版は段1b-2 で同じ SQL から足す。
app.database は読まない（読むとエンジンを作るため。セッションは呼び手から受け取る）。
段2: 画面の一覧・切り替え・変えた記録もここに置く（担当表の SQL はこのファイルだけ）。確定（commit）は呼び手がする。
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SELECT_ASSIGNMENT_SQL = """
    SELECT c.provider, c.model
    FROM public.ai_job_assignments a
    JOIN public.ai_job_choices c ON c.id = a.choice_id AND c.job_key = a.job_key
    WHERE a.job_key = :job_key
"""


class AiAssignment(NamedTuple):
    provider: str
    model: str


class AiAssignmentMissing(LookupError):
    """担当表に job_key の行が無い。"""


async def get_ai_assignment(db: AsyncSession, job_key: str) -> AiAssignment:
    """job_key の今の担当（provider・model）を返す。行が無ければ AiAssignmentMissing。"""
    row = (await db.execute(text(_SELECT_ASSIGNMENT_SQL), {"job_key": job_key})).first()
    if row is None:
        raise AiAssignmentMissing(job_key)
    return AiAssignment(provider=row[0], model=row[1])


# ---------------------------------------------------------------------------
# 段2: 画面（design.md §6・§6-1）
# ---------------------------------------------------------------------------

# 今コードが担当表を読む仕事（design.md §7 の段2）。1b-2 で5つ全部が読むようになったら、
# この定数と画面の switchable の欄と PUT の 409 not_wired を消す。
SWITCHABLE_JOB_KEYS: frozenset[str] = frozenset({"secretary_intent"})

_LIST_ASSIGNMENTS_SQL = """
    SELECT a.job_key, a.choice_id, c.provider, c.model
    FROM public.ai_job_assignments a
    JOIN public.ai_job_choices c ON c.id = a.choice_id AND c.job_key = a.job_key
    ORDER BY a.job_key
"""

_LIST_CHOICES_SQL = """
    SELECT id, job_key, provider, model
    FROM public.ai_job_choices
    ORDER BY job_key, id
"""

_LOCK_ASSIGNMENT_SQL = """
    SELECT choice_id
    FROM public.ai_job_assignments
    WHERE job_key = :job_key
    FOR UPDATE
"""

_CHOICE_OF_JOB_SQL = """
    SELECT 1
    FROM public.ai_job_choices
    WHERE id = :choice_id AND job_key = :job_key
"""

_UPDATE_ASSIGNMENT_SQL = """
    UPDATE public.ai_job_assignments
    SET choice_id = :choice_id, updated_by = :user_id, updated_at = now()
    WHERE job_key = :job_key
"""

_INSERT_HISTORY_SQL = """
    INSERT INTO public.ai_job_assignment_history (job_key, old_choice_id, new_choice_id, changed_by)
    VALUES (:job_key, :old_choice_id, :new_choice_id, :user_id)
"""

_LIST_HISTORY_SQL = """
    SELECT h.job_key,
           oc.provider AS old_provider, oc.model AS old_model,
           nc.provider AS new_provider, nc.model AS new_model,
           u.full_name AS changed_by_name, h.changed_by AS changed_by_id, h.changed_at
    FROM public.ai_job_assignment_history h
    JOIN public.ai_job_choices nc ON nc.id = h.new_choice_id
    LEFT JOIN public.ai_job_choices oc ON oc.id = h.old_choice_id
    LEFT JOIN public.users u ON u.id = h.changed_by
    ORDER BY h.changed_at DESC, h.id DESC
    LIMIT :limit
"""


class AiChoice(NamedTuple):
    choice_id: int
    provider: str
    model: str


class AiJobRow(NamedTuple):
    job_key: str
    choice_id: int
    provider: str
    model: str
    choices: tuple[AiChoice, ...]


class AiJobHistoryRow(NamedTuple):
    job_key: str
    old_provider: str | None
    old_model: str | None
    new_provider: str
    new_model: str
    changed_by_name: str | None
    changed_by_id: int | None
    changed_at: datetime


class AiJobNotFound(LookupError):
    """担当表に job_key の行が無い（5つの仕事の外）。画面の API は 404 not_found。"""


class AiJobNotWired(Exception):
    """job_key は5つの中だが、今のコードが担当表を読まない仕事。画面の API は 409 not_wired。"""


class AiChoiceMismatch(ValueError):
    """choice_id がその job_key の選択肢ではない。画面の API は 422 choice_mismatch。"""


async def list_ai_jobs(db: AsyncSession) -> list[AiJobRow]:
    """担当表の全行（今の担当と、その仕事の選択肢）を job_key の順に返す。仕事の一覧はここから作る。"""
    choices: dict[str, list[AiChoice]] = {}
    for row in (await db.execute(text(_LIST_CHOICES_SQL))).all():
        choices.setdefault(row[1], []).append(AiChoice(choice_id=row[0], provider=row[2], model=row[3]))
    return [
        AiJobRow(
            job_key=row[0],
            choice_id=row[1],
            provider=row[2],
            model=row[3],
            choices=tuple(choices.get(row[0], [])),
        )
        for row in (await db.execute(text(_LIST_ASSIGNMENTS_SQL))).all()
    ]


async def change_ai_assignment(db: AsyncSession, job_key: str, choice_id: int, user_id: int | None) -> bool:
    """担当を変え、履歴を1行書く（同じ取引。確定は呼び手）。変えた時 True、今と同じ choice_id なら何も書かず False。

    判定の順は 404 → 409 → 422 で、どれも書き込みより前（design.md §6-1）。
    今の行を FOR UPDATE で押さえてから old_choice_id を読む（2人が同時に変えても履歴の old がずれない）。
    """
    current = (await db.execute(text(_LOCK_ASSIGNMENT_SQL), {"job_key": job_key})).first()
    if current is None:
        raise AiJobNotFound(job_key)
    if job_key not in SWITCHABLE_JOB_KEYS:
        raise AiJobNotWired(job_key)
    found = (await db.execute(text(_CHOICE_OF_JOB_SQL), {"choice_id": choice_id, "job_key": job_key})).first()
    if found is None:
        raise AiChoiceMismatch(choice_id)
    old_choice_id = current[0]
    if old_choice_id == choice_id:
        return False
    params = {"job_key": job_key, "choice_id": choice_id, "user_id": user_id}
    await db.execute(text(_UPDATE_ASSIGNMENT_SQL), params)
    await db.execute(
        text(_INSERT_HISTORY_SQL),
        {"job_key": job_key, "old_choice_id": old_choice_id, "new_choice_id": choice_id, "user_id": user_id},
    )
    return True


async def list_ai_job_history(db: AsyncSession, limit: int) -> list[AiJobHistoryRow]:
    """変えた記録を新しい順に limit 件。名前は users.full_name だけ（メール・username は読まない。K4）。"""
    rows = (await db.execute(text(_LIST_HISTORY_SQL), {"limit": limit})).all()
    return [AiJobHistoryRow(*row) for row in rows]


__all__ = [
    "SWITCHABLE_JOB_KEYS",
    "AiAssignment",
    "AiAssignmentMissing",
    "AiChoice",
    "AiChoiceMismatch",
    "AiJobHistoryRow",
    "AiJobNotFound",
    "AiJobNotWired",
    "AiJobRow",
    "change_ai_assignment",
    "get_ai_assignment",
    "list_ai_job_history",
    "list_ai_jobs",
]
