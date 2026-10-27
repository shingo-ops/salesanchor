"""保守 API（ADR-1012 段階2 便B）。

障害記録の表 3 つ（ops_incidents / ops_incident_events / ops_control）を読み書きする口。
鍵（OPS_INGEST_TOKEN / OPS_API_TOKEN）か super admin のログインで開く。
鍵が未設定（空）の間、鍵で通る口は全部 401 で閉じたまま。テナント文脈は使わない。
DB の読み書きはすべて「運用者の旗を立てる → 処理 → 旗を戻す」の形で行う（ADR-1018・ADR-131）。
"""
from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_user,
    reset_operator_context,
    set_operator_context,
)
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ops"])

# ヘッダが無いときに 403 ではなく自分で 401 を返すため auto_error=False
_bearer = HTTPBearer(auto_error=False)

_MAX_BODY_BYTES = 262144
_MAX_ALERTS = 100
_JSON_LIMIT_BYTES = 4000
_DETAIL_LIMIT_BYTES = 8000  # 表の制約は 8192（octet_length(detail::text)）。余白を残して入口で止める
_ROUND_NOTE_MAX = 500

# 注記で更新してよい列（SQL の列名に利用者の文字列を入れないための固定の一覧）
_ANNOTATABLE_COLUMNS = (
    "human_noticed_at",
    "needs_action",
    "first_aid_started_at",
    "first_aid_done_at",
    "first_aid_result",
    "ai_started_at",
    "root_cause",
    "fix_pr",
    "review_note",
    "detection_path",
)

# Discord 発の行（labels.source='discord'）に注記で書かせない列（ADR-1039・設計 §4-9 K15）
_DISCORD_LOCKED_COLUMNS = frozenset(
    {
        "ai_started_at",
        "detection_path",
        "first_aid_started_at",
        "first_aid_done_at",
        "first_aid_result",
    }
)


async def _clear_operator(db: AsyncSession) -> None:
    # SET は巻き戻しで元に戻るため、戻した値を commit で確定させる（接続に 'true' を残さない）
    await db.rollback()
    await reset_operator_context(db)
    await db.commit()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="OPS_UNAUTHORIZED",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="OPS_FORBIDDEN")


def _token_matches(presented: str | None, expected: str) -> bool:
    if not presented or not expected:
        return False
    try:
        return secrets.compare_digest(presented, expected)
    except (TypeError, ValueError):
        return False


def _ingest_token() -> str:
    return os.getenv("OPS_INGEST_TOKEN", "")


def _api_token() -> str:
    return os.getenv("OPS_API_TOKEN", "")


async def require_ops_ingest(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    presented = cred.credentials if cred else None
    if not _token_matches(presented, _ingest_token()):
        raise _unauthorized()
    return {"actor": "alertmanager", "user_id": None}


async def require_ops_reader(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if cred is None or not cred.credentials:
        raise _unauthorized()
    presented = cred.credentials
    if _token_matches(presented, _api_token()):
        return {"actor": "ops_token", "user_id": None}
    if _token_matches(presented, _ingest_token()):
        raise _unauthorized()
    user = await get_current_user(request, cred, db)
    if not getattr(user, "is_super_admin", False):
        raise _forbidden()
    return {"actor": "super_admin", "user_id": user.id}


async def require_ops_super_admin(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if cred is None or not cred.credentials:
        raise _unauthorized()
    presented = cred.credentials
    if _token_matches(presented, _api_token()) or _token_matches(presented, _ingest_token()):
        raise _forbidden()
    user = await get_current_user(request, cred, db)
    if not getattr(user, "is_super_admin", False):
        raise _forbidden()
    return {"actor": "super_admin", "user_id": user.id}


# ---------------------------------------------------------------------------
# B1 受け口
# ---------------------------------------------------------------------------


class AlertmanagerAlert(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["firing", "resolved"]
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    startsAt: datetime
    endsAt: datetime | None = None
    fingerprint: str = Field(min_length=1, max_length=200)


class AlertmanagerPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str | None = None
    receiver: str | None = None
    groupKey: str | None = None
    alerts: list[AlertmanagerAlert]


_UPSERT_INCIDENT_SQL = text(
    """
    INSERT INTO public.ops_incidents
        (fingerprint, starts_at, alertname, severity, labels, annotations, status,
         first_notified_at, last_notified_at, resolved_at, recurrence_of)
    VALUES
        (:fingerprint, :starts_at, :alertname, :severity, CAST(:labels AS jsonb), CAST(:annotations AS jsonb), :status,
         now(), now(), :resolved_at,
         (SELECT p.id FROM public.ops_incidents p
           WHERE p.fingerprint = :fingerprint AND p.starts_at < :starts_at
           ORDER BY p.starts_at DESC LIMIT 1))
    ON CONFLICT (fingerprint, starts_at) DO UPDATE SET
        last_notified_at = now(),
        notify_count = public.ops_incidents.notify_count + 1,
        status = EXCLUDED.status,
        resolved_at = COALESCE(EXCLUDED.resolved_at, public.ops_incidents.resolved_at),
        updated_at = now()
    RETURNING id, (xmax = 0) AS inserted
    """
)

_INSERT_EVENT_SQL = text(
    "INSERT INTO public.ops_incident_events (incident_id, kind, actor, detail) "
    "VALUES (:incident_id, :kind, :actor, CAST(:detail AS jsonb))"
)


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _shrink_labels(labels: dict[str, str]) -> dict[str, Any]:
    if len(_dumps(labels).encode("utf-8")) <= _JSON_LIMIT_BYTES:
        return labels
    small: dict[str, Any] = {}
    for key in ("alertname", "severity"):
        if key in labels:
            small[key] = labels[key][:200]
    small["_truncated"] = True
    return small


def _shrink_annotations(annotations: dict[str, str]) -> dict[str, Any]:
    if len(_dumps(annotations).encode("utf-8")) <= _JSON_LIMIT_BYTES:
        return annotations
    small: dict[str, Any] = {}
    if "summary" in annotations:
        small["summary"] = annotations["summary"][:1000]
    small["_truncated"] = True
    return small


@router.post("/ops/alertmanager", dependencies=[Depends(require_ops_ingest)])
async def ingest_alertmanager(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    if len(body) > _MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="OPS_PAYLOAD_TOO_LARGE")
    try:
        payload = AlertmanagerPayload.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json(include_url=False, include_context=False, include_input=False)))
    if len(payload.alerts) > _MAX_ALERTS:
        raise HTTPException(status_code=413, detail="OPS_PAYLOAD_TOO_LARGE")

    created = 0
    updated = 0
    await set_operator_context(db)
    try:
        for alert in payload.alerts:
            row = (
                await db.execute(
                    _UPSERT_INCIDENT_SQL,
                    {
                        "fingerprint": alert.fingerprint,
                        "starts_at": alert.startsAt,
                        "alertname": alert.labels.get("alertname") or "unknown",
                        "severity": alert.labels.get("severity"),
                        "labels": _dumps(_shrink_labels(alert.labels)),
                        "annotations": _dumps(_shrink_annotations(alert.annotations)),
                        "status": alert.status,
                        "resolved_at": alert.endsAt if alert.status == "resolved" else None,
                    },
                )
            ).mappings().one()
            if row["inserted"]:
                created += 1
            else:
                updated += 1
            await db.execute(
                _INSERT_EVENT_SQL,
                {
                    "incident_id": row["id"],
                    "kind": "notified" if alert.status == "firing" else "resolved",
                    "actor": "alertmanager",
                    "detail": _dumps(
                        {
                            "status": alert.status,
                            "receiver": payload.receiver,
                            "groupKey": (payload.groupKey or "")[:500],
                        }
                    ),
                },
            )
        await db.commit()
    finally:
        await _clear_operator(db)
    return {"received": len(payload.alerts), "created": created, "updated": updated}


# ---------------------------------------------------------------------------
# B2・B3 読む
# ---------------------------------------------------------------------------


@router.get("/ops/incidents", dependencies=[Depends(require_ops_reader)])
async def list_incidents(
    status: Literal["firing", "resolved"] | None = None,
    since: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    await set_operator_context(db)
    try:
        result = await db.execute(
            text(
                "SELECT * FROM public.ops_incidents "
                "WHERE (CAST(:status AS text) IS NULL OR status = CAST(:status AS text)) "
                "AND (CAST(:since AS timestamptz) IS NULL OR first_notified_at >= CAST(:since AS timestamptz)) "
                "ORDER BY first_notified_at DESC LIMIT :limit"
            ),
            {"status": status, "since": since, "limit": limit},
        )
        items = [dict(r) for r in result.mappings().all()]
    finally:
        await _clear_operator(db)
    return {"items": items}


@router.get("/ops/incidents/{incident_id}", dependencies=[Depends(require_ops_reader)])
async def get_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    await set_operator_context(db)
    try:
        inc = (
            await db.execute(
                text("SELECT * FROM public.ops_incidents WHERE id = :id"),
                {"id": incident_id},
            )
        ).mappings().first()
        if inc is None:
            raise HTTPException(status_code=404, detail="OPS_INCIDENT_NOT_FOUND")
        events = (
            await db.execute(
                text(
                    "SELECT * FROM public.ops_incident_events "
                    "WHERE incident_id = :id ORDER BY occurred_at"
                ),
                {"id": incident_id},
            )
        ).mappings().all()
        incident = dict(inc)
        event_list = [dict(e) for e in events]
    finally:
        await _clear_operator(db)
    return {"incident": incident, "events": event_list}


# ---------------------------------------------------------------------------
# B4 注記
# ---------------------------------------------------------------------------


class OpsIncidentFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    human_noticed_at: datetime | None = None
    needs_action: bool | None = None
    first_aid_started_at: datetime | None = None
    first_aid_done_at: datetime | None = None
    first_aid_result: Literal["recovered", "not_recovered", "escalated"] | None = None
    ai_started_at: datetime | None = None
    root_cause: str | None = Field(None, max_length=4000)
    fix_pr: int | None = Field(None, ge=1)
    review_note: str | None = Field(None, max_length=4000)
    detection_path: Literal["alert", "human", "ai"] | None = None


class OpsRound(BaseModel):
    """Discord 発の件の回の記録（設計 §4-9）。accept と result の pass は別の口が書く。"""

    model_config = ConfigDict(extra="forbid")

    step: Literal[
        "start",
        "launch_failed",
        "kept",
        "closed",
        "measure",
        "result",
        "stop",
        "notify_failed",
        "suspicious",
    ]
    n: int = Field(ge=1, le=99)
    at: AwareDatetime
    session_id: str | None = Field(None, min_length=1, max_length=64)
    reservation_id: str | None = Field(None, min_length=1, max_length=64)
    result: Literal["fail"] | None = None
    reason: Literal[
        "failed-3",
        "unknown",
        "halt",
        "interrupted",
        "lost",
        "full",
        "not_ready",
        "failed",
        "cwd_invalid",
        "needs_decision",
        "blocked",
        "waiting_60m",
        "no-reply",
        "leftover",
    ] | None = None

    @model_validator(mode="after")
    def _result_only_on_result_step(self) -> "OpsRound":
        if (self.step == "result") != (self.result is not None):
            raise ValueError("result is required when step is result, and not allowed otherwise")
        return self


class OpsIncidentAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["annotated", "first_aid", "ai"]
    note: str | None = Field(None, max_length=2000)
    fields: OpsIncidentFields = OpsIncidentFields()
    round: OpsRound | None = None

    @model_validator(mode="after")
    def _round_rules(self) -> "OpsIncidentAnnotation":
        if self.round is not None:
            if self.kind != "ai":
                raise ValueError("round requires kind ai")
            if self.note is not None and len(self.note) > _ROUND_NOTE_MAX:
                raise ValueError(f"note must be at most {_ROUND_NOTE_MAX} characters when round is set")
        return self


@router.post("/ops/incidents/{incident_id}/events")
async def annotate_incident(
    incident_id: UUID,
    body: OpsIncidentAnnotation,
    who: dict[str, Any] = Depends(require_ops_reader),
    db: AsyncSession = Depends(get_db),
):
    values = body.fields.model_dump(exclude_unset=True)
    columns = [c for c in _ANNOTATABLE_COLUMNS if c in values]
    detail: dict[str, Any] = {"fields": sorted(columns), "note": body.note, "user_id": who["user_id"]}
    if body.round is not None:
        round_detail = body.round.model_dump(mode="json", exclude_none=True)
        round_detail["at"] = body.round.at.astimezone(timezone.utc).isoformat()  # 送られた時差によらず UTC の "+00:00" の形にする（model_dump は "Z"、ほかの口の _now_iso は "+00:00"）
        detail["round"] = round_detail
    detail_json = _dumps(detail)
    if len(detail_json.encode("utf-8")) > _DETAIL_LIMIT_BYTES:
        raise HTTPException(status_code=422, detail="OPS_DETAIL_TOO_LARGE")
    await set_operator_context(db)
    try:
        inc = (
            await db.execute(
                text(
                    "SELECT id, labels->>'source' AS source "
                    "FROM public.ops_incidents WHERE id = :id"
                ),
                {"id": incident_id},
            )
        ).mappings().first()
        if inc is None:
            await db.rollback()
            raise HTTPException(status_code=404, detail="OPS_INCIDENT_NOT_FOUND")
        if inc["source"] == "discord" and _DISCORD_LOCKED_COLUMNS.intersection(columns):
            await db.rollback()
            raise HTTPException(status_code=422, detail="OPS_FIELD_LOCKED_FOR_DISCORD")
        if columns:
            assignments = ", ".join(f"{c} = :{c}" for c in columns)
            await db.execute(
                text(
                    f"UPDATE public.ops_incidents SET {assignments}, updated_at = now() "
                    "WHERE id = :id"
                ),
                {**{c: values[c] for c in columns}, "id": incident_id},
            )
        await db.execute(
            _INSERT_EVENT_SQL,
            {
                "incident_id": incident_id,
                "kind": body.kind,
                "actor": who["actor"],
                "detail": detail_json,
            },
        )
        await db.commit()
    finally:
        await _clear_operator(db)
    return {"incident_id": str(incident_id), "updated_fields": sorted(columns)}


# ---------------------------------------------------------------------------
# Discord 発の件（ADR-1039 Decision 10・設計 §4-9）
# ---------------------------------------------------------------------------


class OpsHumanReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(pattern=r"^[0-9]{1,20}$")
    posted_at: AwareDatetime
    message_url: str = Field(
        max_length=200,
        pattern=r"^https://discord\.com/channels/[0-9]{1,20}/[0-9]{1,20}/[0-9]{1,20}$",
    )
    test: bool = False

    @model_validator(mode="after")
    def _url_ends_with_message_id(self) -> "OpsHumanReport":
        if self.message_url.rsplit("/", 1)[-1] != self.message_id:
            raise ValueError("message_url must end with message_id")
        return self


_INSERT_HUMAN_INCIDENT_SQL = text(
    """
    INSERT INTO public.ops_incidents
        (fingerprint, starts_at, alertname, labels, status, detection_path,
         first_notified_at, last_notified_at, human_noticed_at)
    VALUES
        (:fingerprint, :posted_at, 'discord-bug-report', CAST(:labels AS jsonb), 'firing', 'human',
         :posted_at, :posted_at, :posted_at)
    ON CONFLICT (fingerprint, starts_at) DO NOTHING
    RETURNING id
    """
)


@router.post("/ops/incidents/human")
async def report_human_incident(
    body: OpsHumanReport,
    who: dict[str, Any] = Depends(require_ops_reader),
    db: AsyncSession = Depends(get_db),
):
    fingerprint = f"discord:{body.message_id}"
    labels: dict[str, str] = {"source": "discord", "message_url": body.message_url}
    if body.test:
        labels["test"] = "true"
    await set_operator_context(db)
    try:
        row = (
            await db.execute(
                _INSERT_HUMAN_INCIDENT_SQL,
                {"fingerprint": fingerprint, "posted_at": body.posted_at, "labels": _dumps(labels)},
            )
        ).first()
        inserted = row is not None
        if inserted:
            incident_id = row[0]
            await db.execute(
                _INSERT_EVENT_SQL,
                {
                    "incident_id": incident_id,
                    "kind": "notified",
                    "actor": who["actor"],
                    "detail": _dumps(
                        {"round": {"step": "accept", "n": 1, "at": _now_iso()}, "user_id": who["user_id"]}
                    ),
                },
            )
        else:
            incident_id = (
                await db.execute(
                    text(
                        "SELECT id FROM public.ops_incidents "
                        "WHERE fingerprint = :fingerprint AND starts_at = :posted_at"
                    ),
                    {"fingerprint": fingerprint, "posted_at": body.posted_at},
                )
            ).scalar_one()
        await db.commit()
    finally:
        await _clear_operator(db)
    return {"incident_id": str(incident_id), "inserted": inserted}


class OpsIncidentClose(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int = Field(ge=1, le=99)
    session_id: str = Field(min_length=1, max_length=64)


@router.post("/ops/incidents/{incident_id}/close")
async def close_incident(
    incident_id: UUID,
    body: OpsIncidentClose,
    who: dict[str, Any] = Depends(require_ops_reader),
    db: AsyncSession = Depends(get_db),
):
    await set_operator_context(db)
    try:
        inc = (
            await db.execute(
                text(
                    "SELECT status, labels->>'source' AS source "
                    "FROM public.ops_incidents WHERE id = :id FOR UPDATE"
                ),
                {"id": incident_id},
            )
        ).mappings().first()
        if inc is None:
            await db.rollback()
            raise HTTPException(status_code=404, detail="OPS_INCIDENT_NOT_FOUND")
        if inc["source"] != "discord":
            await db.rollback()
            raise HTTPException(status_code=409, detail="OPS_INCIDENT_NOT_DISCORD")
        closed = inc["status"] != "resolved"
        if closed:
            await db.execute(
                text(
                    "UPDATE public.ops_incidents "
                    "SET status = 'resolved', resolved_at = now(), updated_at = now() "
                    "WHERE id = :id"
                ),
                {"id": incident_id},
            )
            await db.execute(
                _INSERT_EVENT_SQL,
                {
                    "incident_id": incident_id,
                    "kind": "resolved",
                    "actor": who["actor"],
                    "detail": _dumps(
                        {
                            "round": {
                                "step": "result",
                                "result": "pass",
                                "n": body.n,
                                "session_id": body.session_id,
                                "at": _now_iso(),
                            },
                            "user_id": who["user_id"],
                        }
                    ),
                },
            )
            await db.commit()
        else:
            await db.rollback()
    finally:
        await _clear_operator(db)
    return {"incident_id": str(incident_id), "closed": closed}


# ---------------------------------------------------------------------------
# B5 全停止スイッチ
# ---------------------------------------------------------------------------


class OpsControlChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


_SET_CONTROL_SQL = text(
    """
    INSERT INTO public.ops_control (id, halt_all, changed_at, changed_by, reason)
    VALUES (1, :halt_all, now(), :changed_by, :reason)
    ON CONFLICT (id) DO UPDATE SET
        halt_all = :halt_all, changed_at = now(), changed_by = EXCLUDED.changed_by, reason = EXCLUDED.reason
    RETURNING halt_all, changed_at, changed_by, reason
    """
)


def _changed_by(who: dict[str, Any]) -> str:
    if who["actor"] == "ops_token":
        return "ops_token"
    return f"super_admin:{who['user_id']}"


async def _set_control(
    db: AsyncSession, halt_all: bool, who: dict[str, Any], reason: str
) -> dict[str, Any]:
    changed_by = _changed_by(who)
    await set_operator_context(db)
    try:
        row = (
            await db.execute(
                _SET_CONTROL_SQL,
                {"halt_all": halt_all, "changed_by": changed_by, "reason": reason},
            )
        ).mappings().one()
        await db.commit()
        result = dict(row)
    finally:
        await _clear_operator(db)
    logger.warning("[ops] halt_all=%s by=%s reason=%s", halt_all, changed_by, reason)
    return result


@router.get("/ops/control", dependencies=[Depends(require_ops_reader)])
async def get_control(db: AsyncSession = Depends(get_db)):
    await set_operator_context(db)
    try:
        row = (
            await db.execute(
                text(
                    "SELECT halt_all, changed_at, changed_by, reason "
                    "FROM public.ops_control WHERE id = 1"
                )
            )
        ).mappings().first()
        result = dict(row) if row is not None else None
    finally:
        await _clear_operator(db)
    if result is None:
        return {"halt_all": False, "changed_at": None, "changed_by": None, "reason": None}
    return result


@router.post("/ops/control/halt")
async def halt_all(
    body: OpsControlChange,
    who: dict[str, Any] = Depends(require_ops_reader),
    db: AsyncSession = Depends(get_db),
):
    return await _set_control(db, True, who, body.reason)


@router.post("/ops/control/resume")
async def resume_all(
    body: OpsControlChange,
    who: dict[str, Any] = Depends(require_ops_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _set_control(db, False, who, body.reason)
