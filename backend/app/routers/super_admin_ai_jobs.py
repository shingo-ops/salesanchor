"""ADR-1058 段2: AI の担当の画面の API（スーパー管理だけ）。design.md §6・§6-1。

担当表の読み書きは app.services.ai_assignment の1か所（design.md §4-3）。ここは使用の記録
（public.llm_usage_events）からログインの○×と回数を足して返すだけ。鍵の値・メールは返さない（K4）。
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.routers.assistant import agent_url
from app.services.ai_assignment import (
    SWITCHABLE_JOB_KEYS,
    AiChoiceMismatch,
    AiJobNotFound,
    AiJobNotWired,
    AiJobRow,
    change_ai_assignment,
    list_ai_job_history,
    list_ai_jobs,
)
from app.services.llm_budget import USAGE_SDKS_BY_PROVIDER

router = APIRouter()

# 秘書の容器の /health を待つ上限（design.md §6-1。GET 全体が容器を待って遅くならないように）
HEALTH_TIMEOUT_SECONDS = 2.0
_SECRETARY_JOB_KEY = "secretary_intent"

# 1つの仕事の使用の記録の集計（purpose＝job_key・今の provider の sdk の集合。design.md §6 の①・§6-1 の数え方）
_USAGE_STATS_SQL = """
    SELECT
        (SELECT max(e.occurred_at) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'ok') AS last_ok_at,
        (SELECT count(*) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'ok'
            AND e.occurred_at >= now() - interval '24 hours') AS count_24h,
        (SELECT count(*) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'failed'
            AND e.occurred_at >= now() - interval '24 hours') AS failed_24h,
        (SELECT e.error_code FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks)
          ORDER BY e.occurred_at DESC, e.id DESC LIMIT 1) AS newest_error_code,
        (SELECT e.error_code FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'failed'
          ORDER BY e.occurred_at DESC, e.id DESC LIMIT 1) AS last_error_code,
        (SELECT max(e.occurred_at) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'failed') AS last_error_at
"""


class AiChoiceOut(BaseModel):
    choice_id: int
    provider: str
    model: str


class AiJobOut(BaseModel):
    job_key: str
    provider: str
    model: str
    choice_id: int
    choices: list[AiChoiceOut]
    login_ok: bool
    login_reason: str | None
    last_ok_at: datetime | None
    count_24h: int
    failed_24h: int
    last_error_code: str | None
    last_error_at: datetime | None
    login_refreshed_at: datetime | None
    switchable: bool


class AiJobsOut(BaseModel):
    jobs: list[AiJobOut]


class AiJobChangeIn(BaseModel):
    choice_id: int


class AiProviderModel(BaseModel):
    provider: str
    model: str


class AiJobHistoryItem(BaseModel):
    job_key: str
    old: AiProviderModel | None
    new: AiProviderModel
    changed_by_name: str | None
    changed_by_id: int | None
    changed_at: datetime


class AiJobHistoryOut(BaseModel):
    items: list[AiJobHistoryItem]


def _login_state(
    provider: str,
    newest_error_code: str | None,
    gemini_key_present: bool,
    agent_ready: bool | None,
) -> tuple[bool, str | None]:
    """ログインの○×と理由（design.md §6 の①②③。どれかで ×。理由の優先は auth_failed > key_missing > not_ready）。

    agent_ready は秘書の行だけ真偽、ほかの行は None（容器を見ない）。
    """
    if newest_error_code == "auth_failed":
        return False, "auth_failed"
    if provider == "gemini" and not gemini_key_present:
        return False, "key_missing"
    if agent_ready is False:
        return False, "not_ready"
    return True, None


def _gemini_key_present() -> bool:
    """Gemini の鍵が環境にあるかどうかだけを見る（値は読まない・返さない。K4）。"""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


# codex の auth.json の last_refresh（例 2026-11-11T00:00:00.123456789Z）。秒の下は6桁に切ってから読む。
_REFRESHED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})$")


async def _secretary_health(url: str) -> dict | None:
    """秘書の容器の /health を 2 秒で読む。200 で JSON の dict なら返す。返らない・届かない・形が違えば None。"""
    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_SECONDS) as client:
            res = await client.get(f"{url}/health")
        body = res.json() if res.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _parse_refreshed(value: object) -> datetime | None:
    """codex のログインの更新日時を読む。読めなければ None（推測で埋めない）。"""
    if not isinstance(value, str):
        return None
    m = _REFRESHED_RE.match(value)
    if m is None:
        return None
    frac = f".{m.group(2)[:6]}" if m.group(2) else ""
    zone = "+00:00" if m.group(3) == "Z" else m.group(3)
    try:
        return datetime.fromisoformat(f"{m.group(1)}{frac}{zone}")
    except ValueError:
        return None


async def _agent_state_for(job: AiJobRow) -> tuple[bool | None, datetime | None]:
    """秘書の行だけ容器を見る（ready と、codex の時だけログインの更新日時）。ほかの行は (None, None)。

    宛先は assistant.agent_url（配線の正本）。容器の無い provider は not_ready。
    """
    if job.job_key != _SECRETARY_JOB_KEY:
        return None, None
    url = agent_url(job.provider)
    if url is None:
        return False, None
    health = await _secretary_health(url)
    if health is None or health.get("ready") is not True:
        return False, None
    refreshed = _parse_refreshed(health.get("last_refresh")) if job.provider == "codex" else None
    return True, refreshed


async def _usage_stats(db: AsyncSession, job_key: str, provider: str) -> dict:
    sdks = sorted(USAGE_SDKS_BY_PROVIDER.get(provider, frozenset()))
    row = (await db.execute(text(_USAGE_STATS_SQL), {"job_key": job_key, "sdks": sdks})).mappings().one()
    return dict(row)


async def _job_out(db: AsyncSession, job: AiJobRow, gemini_key_present: bool) -> AiJobOut:
    stats = await _usage_stats(db, job.job_key, job.provider)
    agent_ready, refreshed_at = await _agent_state_for(job)
    login_ok, login_reason = _login_state(job.provider, stats["newest_error_code"], gemini_key_present, agent_ready)
    return AiJobOut(
        job_key=job.job_key,
        provider=job.provider,
        model=job.model,
        choice_id=job.choice_id,
        choices=[AiChoiceOut(choice_id=c.choice_id, provider=c.provider, model=c.model) for c in job.choices],
        login_ok=login_ok,
        login_reason=login_reason,
        last_ok_at=stats["last_ok_at"],
        count_24h=int(stats["count_24h"] or 0),
        failed_24h=int(stats["failed_24h"] or 0),
        last_error_code=stats["last_error_code"],
        last_error_at=stats["last_error_at"],
        # secretary_intent で provider=codex の時だけ値（design.md §6-1）
        login_refreshed_at=refreshed_at,
        switchable=job.job_key in SWITCHABLE_JOB_KEYS,
    )


@router.get("/super-admin/ai-jobs", response_model=AiJobsOut)
async def get_ai_jobs(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AiJobsOut:
    gemini_key_present = _gemini_key_present()
    jobs = await list_ai_jobs(db)
    return AiJobsOut(jobs=[await _job_out(db, job, gemini_key_present) for job in jobs])


@router.get("/super-admin/ai-jobs/history", response_model=AiJobHistoryOut)
async def get_ai_job_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AiJobHistoryOut:
    rows = await list_ai_job_history(db, limit)
    return AiJobHistoryOut(
        items=[
            AiJobHistoryItem(
                job_key=r.job_key,
                old=(
                    AiProviderModel(provider=r.old_provider, model=r.old_model)
                    if r.old_provider is not None and r.old_model is not None
                    else None
                ),
                new=AiProviderModel(provider=r.new_provider, model=r.new_model),
                changed_by_name=r.changed_by_name,
                changed_by_id=r.changed_by_id,
                changed_at=r.changed_at,
            )
            for r in rows
        ]
    )


@router.put("/super-admin/ai-jobs/{job_key}", response_model=AiJobOut)
async def put_ai_job(
    job_key: str,
    body: AiJobChangeIn,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AiJobOut:
    try:
        await change_ai_assignment(db, job_key, body.choice_id, current_user.id)
    except AiJobNotFound:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from None
    except AiJobNotWired:
        raise HTTPException(status_code=409, detail={"code": "not_wired"}) from None
    except AiChoiceMismatch:
        raise HTTPException(status_code=422, detail={"code": "choice_mismatch"}) from None
    await db.commit()
    gemini_key_present = _gemini_key_present()
    for job in await list_ai_jobs(db):
        if job.job_key == job_key:
            return await _job_out(db, job, gemini_key_present)
    raise HTTPException(status_code=404, detail={"code": "not_found"})
