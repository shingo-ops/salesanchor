"""
ADR-1025 便2: 自動セッション用の口 3 つ。

  GET  /api/v1/ops/error-reports/{report_code}
  POST /api/v1/ops/error-reports/{report_code}/events
  POST /api/v1/ops/error-reports/{report_code}/reanalyze

認証: 専用の鍵 ERROR_REPORT_AGENT_TOKEN だけ（super admin のログインでは通さない）。
鍵が未設定・空なら全員 401。書き込みは運用者の旗を立てた 1 トランザクション。
"""
from __future__ import annotations

import json
import os
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import reset_operator_context, set_operator_context
from app.database import get_db
from app.schemas.analysis_error_report_ops import (
    OpsEventRequest,
    OpsEventResponse,
    OpsReanalyzeResponse,
    OpsReportDetail,
    OpsReportEvent,
    OpsReportField,
    OpsReportHeader,
)
from app.services.analysis_error_report_svc import _INSERT_EVENT_SQL, _json, _read_system_values
from app.services.line_analysis_v102_svc import is_v102_prompt_version
from app.services.v102_human_decisions_svc import TCG_SCHEMA

router = APIRouter(prefix="/ops/error-reports", tags=["ops"])

_bearer = HTTPBearer(auto_error=False)

_CLOSED_STATUSES = ("resolved", "cancelled")

_REPORT_SQL = (
    "SELECT id::text AS id, report_code, extraction_item_id::text AS extraction_item_id, "
    "extraction_job_id::text AS extraction_job_id, status, reported_at "
    "FROM public.analysis_error_reports WHERE report_code = :code"
)
_FIELDS_SQL = (
    "SELECT field_name, system_value, expected_value, expected_missing_product "
    "FROM public.analysis_error_report_fields WHERE report_id = CAST(:rid AS uuid) ORDER BY id"
)
_EVENTS_SQL = (
    "SELECT at, actor, kind, payload FROM public.analysis_error_report_events "
    "WHERE report_id = CAST(:rid AS uuid) ORDER BY at, id"
)
_PROMPT_VERSION_SQL = "SELECT prompt_version FROM {schema}.extraction_jobs WHERE id = CAST(:jid AS uuid)"
_INSERT_EVENT_RETURNING_SQL = _INSERT_EVENT_SQL + " RETURNING id"
_SET_WORKING_SQL = (
    "UPDATE public.analysis_error_reports SET status = 'working' WHERE id = CAST(:rid AS uuid) AND status = 'open'"
)


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="ERROR_REPORT_UNAUTHORIZED", headers={"WWW-Authenticate": "Bearer"})


def _agent_token() -> str:
    return os.getenv("ERROR_REPORT_AGENT_TOKEN", "")


async def require_error_report_agent(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """専用の鍵だけを受ける。未設定・空・違う鍵・ログインのトークンはすべて 401。"""
    presented = cred.credentials if cred else None
    expected = _agent_token()
    if not presented or not expected:
        raise _unauthorized()
    try:
        ok = secrets.compare_digest(presented, expected)
    except (TypeError, ValueError):
        ok = False
    if not ok:
        raise _unauthorized()
    return {"actor": "error_report_agent"}


async def _load_report(db: AsyncSession, report_code: str) -> dict[str, Any]:
    row = (await db.execute(text(_REPORT_SQL), {"code": report_code})).mappings().first()
    if row is None:
        raise HTTPException(404, "Report not found")
    return dict(row)


async def _prompt_version(db: AsyncSession, job_id: str) -> str | None:
    row = (await db.execute(text(_PROMPT_VERSION_SQL.format(schema=TCG_SCHEMA)), {"jid": job_id})).first()
    return row[0] if row else None


@router.get("/{report_code}", response_model=OpsReportDetail, summary="誤り報告の取得（ADR-1025）")
async def get_error_report(
    report_code: str,
    db: AsyncSession = Depends(get_db),
    _agent: dict[str, Any] = Depends(require_error_report_agent),
) -> OpsReportDetail:
    await set_operator_context(db)
    try:
        report = await _load_report(db, report_code)
        fields = (await db.execute(text(_FIELDS_SQL), {"rid": report["id"]})).mappings().all()
        events = (await db.execute(text(_EVENTS_SQL), {"rid": report["id"]})).mappings().all()
        current = await _read_system_values(db, report["extraction_item_id"])
        prompt_version = await _prompt_version(db, report["extraction_job_id"])
    finally:
        await reset_operator_context(db)
    return OpsReportDetail(
        report=OpsReportHeader(**{k: v for k, v in report.items() if k != "id"}),
        fields=[OpsReportField(**dict(f)) for f in fields],
        current_values=json.loads(_json(current)),
        prompt_version=prompt_version,
        events=[OpsReportEvent(**dict(e)) for e in events],
    )


@router.post(
    "/{report_code}/events", response_model=OpsEventResponse, status_code=201,
    summary="誤り報告に原因・対応を記録する（ADR-1025）",
)
async def post_error_report_event(
    report_code: str,
    body: OpsEventRequest,
    db: AsyncSession = Depends(get_db),
    _agent: dict[str, Any] = Depends(require_error_report_agent),
) -> OpsEventResponse:
    await set_operator_context(db)
    try:
        report = await _load_report(db, report_code)
        if report["status"] in _CLOSED_STATUSES:
            raise HTTPException(409, "Report is closed")
        event_id = (
            await db.execute(
                text(_INSERT_EVENT_RETURNING_SQL),
                {"rid": report["id"], "actor": body.actor, "kind": body.kind, "payload": _json(body.payload)},
            )
        ).scalar_one()
        if report["status"] == "open":
            await db.execute(text(_SET_WORKING_SQL), {"rid": report["id"]})
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)
    return OpsEventResponse(id=int(event_id))


@router.post(
    "/{report_code}/reanalyze", response_model=OpsReanalyzeResponse, status_code=202,
    summary="誤り報告の行を再解析して照合する（v102 のみ・ADR-1025）",
)
async def post_error_report_reanalyze(
    report_code: str,
    db: AsyncSession = Depends(get_db),
    _agent: dict[str, Any] = Depends(require_error_report_agent),
) -> OpsReanalyzeResponse:
    from app.tasks import tcg_extraction  # noqa: PLC0415 - 重い import を口の呼び出し時まで遅らせる

    await set_operator_context(db)
    try:
        report = await _load_report(db, report_code)
        if report["status"] in _CLOSED_STATUSES:
            raise HTTPException(409, "Report is closed")
        if not is_v102_prompt_version(await _prompt_version(db, report["extraction_job_id"])):
            raise HTTPException(409, "not_v102")
        task = tcg_extraction.error_report_reanalyze_and_verify_task
        if task is None:
            raise HTTPException(503, "Task queue unavailable")
        task_id = str(uuid.uuid4())
        try:
            task.apply_async(args=[report["id"]], task_id=task_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(503, "Task enqueue failed") from exc
        await db.execute(
            text(_INSERT_EVENT_SQL),
            {"rid": report["id"], "actor": "error_report_agent", "kind": "reanalyzed",
             "payload": _json({"task_id": task_id})},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)
    return OpsReanalyzeResponse(task_id=task_id)
