"""
ADR-1052 段2: 相談係（クラウドの Claude）の「件」の口 8 つ。

  POST /api/v1/ops/case/{incident_id}/ticket                         ADMIN  件の札を作る（応答で 1 回だけ返す）
  GET  /api/v1/ops/case/pending                                      ADMIN  判断待ちの申請と、自動で断った行
  POST /api/v1/ops/case/unmask-requests/{request_id}/decision        ADMIN  申請の許可・拒否
  POST /api/v1/ops/case/audits                                       ADMIN  週次点検の結果を残す
  GET  /api/v1/ops/case/audit-inputs                                 ADMIN  点検の材料（数だけ）
  POST /api/v1/ops/case/{incident_id}/report                         AGENT＋札  報告（1 件 1 通）
  POST /api/v1/ops/case/{incident_id}/unmask-requests                AGENT＋札  値を見たい申請
  GET  /api/v1/ops/case/unmask-requests/{request_id}                 AGENT＋札  申請の状態

認証: 専用の鍵 2 つ（CASE_AGENT_TOKEN・CASE_ADMIN_TOKEN）。どちらも未設定・空なら全員 401。
どちらの口も、もう片方の鍵では 401。2 つの鍵が同じ値なら両方の口を全員 401（値は記録に出さない）。
相談係の口だけ、件の札（ヘッダ X-Case-Ticket）も要る。合わなければ 403（件が無い場合も 403＝件の有無を漏らさない）。
応答と記録に、札・鍵・申請の理由の全文を書かない。この API は値を返さない（値を返すのは ai-unmask-http だけ）。
DB の失敗は 503 と OPS_CASE_UNAVAILABLE だけを返し、記録には口の名前と SQLSTATE だけを出す。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import reset_operator_context, set_operator_context
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ops-case"])

_bearer = HTTPBearer(auto_error=False)

_REPORT_MAX_BYTES = 32 * 1024
_AUDIT_MAX_BYTES = 64 * 1024
_TICKET_TTL_HOURS = 24
_REQUEST_LIMIT_PER_CASE = 2
_UNAVAILABLE = {"detail": "OPS_CASE_UNAVAILABLE"}

_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_INT_RE = re.compile(r"-?[0-9]{1,19}")
_INT_RANGES = {
    "smallint": (-(2**15), 2**15 - 1),
    "integer": (-(2**31), 2**31 - 1),
    "bigint": (-(2**63), 2**63 - 1),
}
_PK_TYPES = frozenset({"smallint", "integer", "bigint", "uuid", "text", "character varying"})


# ---------------------------------------------------------------------------
# 認証（鍵 2 つ）
# ---------------------------------------------------------------------------


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="OPS_CASE_UNAUTHORIZED", headers={"WWW-Authenticate": "Bearer"})


def _tokens() -> tuple[str, str]:
    return os.getenv("CASE_AGENT_TOKEN", ""), os.getenv("CASE_ADMIN_TOKEN", "")


def _same(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _authorize(cred: HTTPAuthorizationCredentials | None, which: Literal["agent", "admin"]) -> None:
    agent, admin = _tokens()
    expected = agent if which == "agent" else admin
    presented = cred.credentials if cred else None
    if not presented or not expected:
        raise _unauthorized()
    if agent and admin and _same(agent, admin):
        # 同じ値の鍵では口の取り違えを防げない。両方の口を止める（値は出さない）
        logger.error("ops_case keys identical")
        raise _unauthorized()
    if not _same(presented, expected):
        raise _unauthorized()


async def require_case_agent(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    _authorize(cred, "agent")


async def require_case_admin(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    _authorize(cred, "admin")


# ---------------------------------------------------------------------------
# DB の共通部品
# ---------------------------------------------------------------------------


async def _clear_operator(db: AsyncSession) -> None:
    # SET は巻き戻しで元に戻るため、戻した値を commit で確定させる（接続に 'true' を残さない）
    await db.rollback()
    await reset_operator_context(db)
    await db.commit()


def _sqlstate(exc: BaseException) -> str:
    orig = getattr(exc, "orig", None)
    for obj in (orig, getattr(orig, "__cause__", None)):
        for attr in ("sqlstate", "pgcode"):
            code = getattr(obj, attr, None)
            if isinstance(code, str) and code:
                return code
    return "unknown"


def _unavailable(route: str, exc: BaseException) -> HTTPException:
    # 記録には口の名前と SQLSTATE だけ（エラーの文・表の名前・値は出さない）
    logger.error("ops_case %s db_error sqlstate=%s", route, _sqlstate(exc))
    return HTTPException(status_code=503, detail=_UNAVAILABLE["detail"])


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="OPS_CASE_FORBIDDEN")


async def _verify_ticket(db: AsyncSession, incident_id: str, ticket: str | None) -> None:
    """件の札を確かめる。件が無い・札が違う・期限切れはどれも同じ 403。"""
    presented = _sha256_hex(ticket) if ticket and len(ticket) <= 256 else ""
    row = (
        await db.execute(
            text(
                "SELECT ticket_hash, (ticket_expires_at IS NOT NULL AND ticket_expires_at > now()) AS fresh "
                "FROM ops_case.cases WHERE incident_id = CAST(:iid AS uuid)"
            ),
            {"iid": incident_id},
        )
    ).first()
    stored = row[0] if row and row[0] else "0" * 64
    same = _same(presented, stored)
    if not (row is not None and row[0] and row[1] and presented and same):
        raise _forbidden()


async def require_case_ticket(
    incident_id: uuid.UUID,
    x_case_ticket: str | None = Header(default=None, alias="X-Case-Ticket"),
    db: AsyncSession = Depends(get_db),
    _agent: None = Depends(require_case_agent),
) -> str:
    """相談係の口（{incident_id} つき）の札の確認。通れば運用者の旗を立てたまま返す（口の最後に外す）。"""
    iid = str(incident_id)
    try:
        await set_operator_context(db)
        try:
            await _verify_ticket(db, iid, x_case_ticket)
        except HTTPException:
            await _clear_operator(db)
            raise
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("ticket_check", exc) from None
    return iid


async def _safe_clear(db: AsyncSession) -> None:
    try:
        await _clear_operator(db)
    except Exception:  # noqa: BLE001 - 後始末の失敗で本来の応答を隠さない
        logger.error("ops_case clear_operator failed")


# ---------------------------------------------------------------------------
# 入力
# ---------------------------------------------------------------------------


class ReportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["investigating", "reported"]
    summary: str | None = Field(default=None, max_length=8000)
    cause: str | None = Field(default=None, max_length=8000)
    evidence: Any = None
    proposal: Any = None
    risk: str | None = Field(default=None, max_length=4000)
    needs_decision: str | None = Field(default=None, max_length=4000)


class UnmaskRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view_name: str = Field(min_length=1, max_length=200)
    column_names: list[str] = Field(min_length=1, max_length=100)
    row_keys: list[str] = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=20, max_length=1000)


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "denied"]
    reason: str = Field(min_length=1, max_length=1000)
    minutes: int | None = Field(default=None, ge=1, le=15)


class AuditBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[Any]


async def _read_limited(request: Request, limit: int) -> bytes:
    """本文を読み、limit を超えたら 413。"""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail="OPS_CASE_PAYLOAD_TOO_LARGE")
    body = await request.body()
    if len(body) > limit:
        raise HTTPException(status_code=413, detail="OPS_CASE_PAYLOAD_TOO_LARGE")
    return body


def _parse(model: type[BaseModel], raw: bytes) -> Any:
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        # 入力の値をそのまま返さない（場所と種類だけ）
        errors = [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors(include_input=False)]
        raise HTTPException(status_code=422, detail=errors) from None


def _dedupe(items: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def _unprocessable(code: str) -> HTTPException:
    return HTTPException(status_code=422, detail=code)


def _key_ok(pk_type: str, key: str) -> bool:
    if pk_type in _INT_RANGES:
        if not _INT_RE.fullmatch(key):
            return False
        lo, hi = _INT_RANGES[pk_type]
        return lo <= int(key) <= hi
    if pk_type == "uuid":
        return bool(_UUID_RE.fullmatch(key))
    return 1 <= len(key) <= 200  # text・character varying


# ---------------------------------------------------------------------------
# 管理の口（ADMIN）
# ---------------------------------------------------------------------------


@router.post("/ops/case/{incident_id}/ticket", dependencies=[Depends(require_case_admin)])
async def create_ticket(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """件の札を作る。あれば上書き（前の札は使えなくなる）。札は応答で 1 回だけ返す。"""
    iid = str(incident_id)
    ticket = secrets.token_urlsafe(32)
    try:
        await set_operator_context(db)
        exists = (
            await db.execute(text("SELECT 1 FROM public.ops_incidents WHERE id = CAST(:iid AS uuid)"), {"iid": iid})
        ).first()
        if exists is None:
            raise HTTPException(status_code=404, detail="OPS_CASE_INCIDENT_NOT_FOUND")
        expires_at = (
            await db.execute(
                text(
                    "INSERT INTO ops_case.cases (incident_id, ticket_hash, ticket_expires_at) "
                    "VALUES (CAST(:iid AS uuid), :h, now() + make_interval(hours => :hours)) "
                    "ON CONFLICT (incident_id) DO UPDATE "
                    "SET ticket_hash = EXCLUDED.ticket_hash, ticket_expires_at = EXCLUDED.ticket_expires_at "
                    "RETURNING ticket_expires_at"
                ),
                {"iid": iid, "h": _sha256_hex(ticket), "hours": _TICKET_TTL_HOURS},
            )
        ).scalar_one()
        await db.commit()
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("ticket", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {"incident_id": iid, "ticket": ticket, "expires_at": expires_at}


@router.get("/ops/case/pending", dependencies=[Depends(require_case_admin)])
async def list_pending(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """判断待ちの申請（理由・列・行の数・作った時刻）と、24 時間以内に自動で断った行。値は無い。"""
    try:
        await set_operator_context(db)
        pending = (
            (
                await db.execute(
                    text(
                        "SELECT id::text AS id, incident_id::text AS incident_id, view_name, column_names, "
                        "cardinality(row_keys) AS row_count, reason, created_at "
                        "FROM ops_case.unmask_requests WHERE status = 'pending' ORDER BY created_at"
                    )
                )
            )
            .mappings()
            .all()
        )
        auto_denied = (
            (
                await db.execute(
                    text(
                        "SELECT id::text AS id, incident_id::text AS incident_id, created_at "
                        "FROM ops_case.unmask_requests "
                        "WHERE decided_by = 'auto:limit' AND created_at > now() - interval '24 hours' "
                        "ORDER BY created_at"
                    )
                )
            )
            .mappings()
            .all()
        )
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("pending", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {"pending": [dict(r) for r in pending], "auto_denied": [dict(r) for r in auto_denied]}


@router.post("/ops/case/unmask-requests/{request_id}/decision", dependencies=[Depends(require_case_admin)])
async def decide_request(
    request_id: uuid.UUID, body: DecisionBody, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """申請の許可・拒否。pending 以外は 409。expires_at は backend が決める（許可のときだけ）。"""
    if body.decision == "approved" and body.minutes is None:
        raise _unprocessable("minutes_required")
    if body.decision == "denied" and body.minutes is not None:
        raise _unprocessable("minutes_only_for_approved")
    rid = str(request_id)
    try:
        await set_operator_context(db)
        row = (
            await db.execute(
                text(
                    "UPDATE ops_case.unmask_requests SET status = :status, decided_by = 'agent-console', "
                    "decision_reason = :reason, approved_minutes = :minutes, "
                    "expires_at = CASE WHEN :status = 'approved' THEN now() + make_interval(mins => :minutes) END "
                    "WHERE id = CAST(:rid AS uuid) AND status = 'pending' "
                    "RETURNING id::text AS id, status, expires_at"
                ),
                {"status": body.decision, "reason": body.reason, "minutes": body.minutes, "rid": rid},
            )
        ).first()
        if row is None:
            exists = (
                await db.execute(
                    text("SELECT 1 FROM ops_case.unmask_requests WHERE id = CAST(:rid AS uuid)"), {"rid": rid}
                )
            ).first()
            raise HTTPException(status_code=409 if exists else 404, detail="OPS_CASE_NOT_PENDING" if exists else "OPS_CASE_NOT_FOUND")
        await db.commit()
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("decision", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {"id": row[0], "status": row[1], "expires_at": row[2]}


@router.post("/ops/case/audits", dependencies=[Depends(require_case_admin)])
async def post_audit(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """週次点検の結果を 1 行残す（64KB まで）。"""
    body: AuditBody = _parse(AuditBody, await _read_limited(request, _AUDIT_MAX_BYTES))
    try:
        await set_operator_context(db)
        row = (
            await db.execute(
                text(
                    "INSERT INTO ops_case.audits (findings, finding_count) "
                    "VALUES (CAST(:findings AS jsonb), :n) RETURNING id, finding_count"
                ),
                {"findings": json.dumps(body.findings, ensure_ascii=False), "n": len(body.findings)},
            )
        ).first()
        await db.commit()
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("audits", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {"id": row[0], "finding_count": row[1]}


@router.get("/ops/case/audit-inputs", dependencies=[Depends(require_case_admin)])
async def audit_inputs(days: int = 7, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """点検の材料。申請・判断・読み出しの数と、ai_cloud の作成の結果の数だけ（値は無い）。"""
    if not 1 <= days <= 90:
        raise _unprocessable("days_out_of_range")
    try:
        await set_operator_context(db)
        requests = (
            (
                await db.execute(
                    text(
                        "SELECT status, count(*) AS n FROM ops_case.unmask_requests "
                        "WHERE created_at > now() - make_interval(days => :days) GROUP BY status"
                    ),
                    {"days": days},
                )
            )
            .mappings()
            .all()
        )
        auto_limit = (
            await db.execute(
                text(
                    "SELECT count(*) FROM ops_case.unmask_requests WHERE decided_by = 'auto:limit' "
                    "AND created_at > now() - make_interval(days => :days)"
                ),
                {"days": days},
            )
        ).scalar_one()
        reads = (
            await db.execute(
                text(
                    "SELECT count(*), coalesce(sum(row_count), 0) FROM ops_case.unmask_reads "
                    "WHERE read_at > now() - make_interval(days => :days)"
                ),
                {"days": days},
            )
        ).one()
        build = (
            await db.execute(
                text(
                    "SELECT count(*) FILTER (WHERE ok) AS ok_count, count(*) FILTER (WHERE NOT ok) AS failed_count "
                    "FROM ai_cloud_meta.build_log WHERE built_at > now() - make_interval(days => :days)"
                ),
                {"days": days},
            )
        ).one()
        latest = (
            (
                await db.execute(
                    text(
                        "SELECT built_at, ok, view_count, failed_count "
                        "FROM ai_cloud_meta.build_log ORDER BY built_at DESC LIMIT 1"
                    )
                )
            )
            .mappings()
            .first()
        )
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("audit_inputs", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {
        "days": days,
        "requests_by_status": {r["status"]: r["n"] for r in requests},
        "auto_denied": auto_limit,
        "reads": {"count": reads[0], "row_count": int(reads[1])},
        "build_log": {"ok": build[0], "failed": build[1], "latest": dict(latest) if latest else None},
    }


# ---------------------------------------------------------------------------
# 相談係の口（AGENT＋札）
# ---------------------------------------------------------------------------


@router.post("/ops/case/{incident_id}/report")
async def post_report(
    request: Request, incident_id: str = Depends(require_case_ticket), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """報告（1 件 1 通。2 回目は 409。本文は 32KB まで）。"""
    try:
        body: ReportBody = _parse(ReportBody, await _read_limited(request, _REPORT_MAX_BYTES))
    except HTTPException:
        await _safe_clear(db)
        raise
    def _j(v: Any) -> str | None:
        return None if v is None else json.dumps(v, ensure_ascii=False)

    try:
        row = (
            await db.execute(
                text(
                    "INSERT INTO ops_case.reports (incident_id, status, summary, cause, evidence, proposal, risk, "
                    "needs_decision) VALUES (CAST(:iid AS uuid), :status, :summary, :cause, CAST(:evidence AS jsonb), "
                    "CAST(:proposal AS jsonb), :risk, :needs) "
                    "ON CONFLICT (incident_id) DO NOTHING RETURNING id::text"
                ),
                {
                    "iid": incident_id,
                    "status": body.status,
                    "summary": body.summary,
                    "cause": body.cause,
                    "evidence": _j(body.evidence),
                    "proposal": _j(body.proposal),
                    "risk": body.risk,
                    "needs": body.needs_decision,
                },
            )
        ).first()
        if row is None:
            raise HTTPException(status_code=409, detail="OPS_CASE_REPORT_EXISTS")
        await db.commit()
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("report", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {"id": row[0], "incident_id": incident_id}


async def _check_request_content(db: AsyncSession, view_name: str, columns: list[str], keys: list[str]) -> None:
    """申請の中身の検査（どれも 422）。拒否表の一覧は backend に写さず、DB の関数を呼ぶ。"""
    if not 1 <= len(columns) <= 5 or not 1 <= len(keys) <= 20:
        raise _unprocessable("size")
    sources = (
        (
            await db.execute(
                text("SELECT DISTINCT source FROM ai_cloud_meta.build_columns WHERE view_name = :v"),
                {"v": view_name},
            )
        )
        .scalars()
        .all()
    )
    if len(sources) != 1:
        raise _unprocessable("view")
    source = sources[0]
    if (await db.execute(text("SELECT ops_case.is_denied_source(:s)"), {"s": source})).scalar_one():
        raise _unprocessable("source")
    modes = dict(
        (
            await db.execute(
                text("SELECT column_name, mode FROM ai_cloud_meta.build_columns WHERE view_name = :v"),
                {"v": view_name},
            )
        )
        .tuples()
        .all()
    )
    for col in columns:
        if modes.get(col) is None or modes[col] == "excluded":
            raise _unprocessable("column")
    pk = (
        await db.execute(
            text(
                "SELECT pg_catalog.format_type(a.atttypid, NULL) "
                "FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                "JOIN pg_catalog.pg_index i ON i.indrelid = c.oid AND i.indisprimary AND i.indnatts = 1 "
                "JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = i.indkey[0] "
                "WHERE n.nspname || '.' || c.relname = :s AND c.relkind IN ('r', 'p')"
            ),
            {"s": source},
        )
    ).all()
    if len(pk) != 1 or pk[0][0] not in _PK_TYPES:
        raise _unprocessable("key_type")
    for key in keys:
        if not _key_ok(pk[0][0], key):
            raise _unprocessable("key")


@router.post("/ops/case/{incident_id}/unmask-requests")
async def post_unmask_request(
    body: UnmaskRequestBody,
    incident_id: str = Depends(require_case_ticket),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """値を見たい申請。検査を通れば pending で 1 行。3 つ目は自動で断る（409）。"""
    columns = _dedupe(body.column_names)
    keys = _dedupe(body.row_keys)
    params = {"iid": incident_id, "view": body.view_name, "cols": columns, "keys": keys, "reason": body.reason}
    try:
        # 件の行をロックしてから数える（同時に送られても 3 本目が通らない）
        await db.execute(
            text("SELECT 1 FROM ops_case.cases WHERE incident_id = CAST(:iid AS uuid) FOR UPDATE"), {"iid": incident_id}
        )
        used = (
            await db.execute(
                text(
                    "SELECT count(*) FROM ops_case.unmask_requests "
                    "WHERE incident_id = CAST(:iid AS uuid) AND decided_by IS DISTINCT FROM 'auto:limit'"
                ),
                {"iid": incident_id},
            )
        ).scalar_one()
        if used >= _REQUEST_LIMIT_PER_CASE:
            already = (
                await db.execute(
                    text(
                        "SELECT 1 FROM ops_case.unmask_requests WHERE incident_id = CAST(:iid AS uuid) "
                        "AND decided_by = 'auto:limit' AND created_at > now() - interval '24 hours' LIMIT 1"
                    ),
                    {"iid": incident_id},
                )
            ).first()
            if already is None and 1 <= len(columns) <= 5 and 1 <= len(keys) <= 20:
                await db.execute(
                    text(
                        "INSERT INTO ops_case.unmask_requests (incident_id, view_name, column_names, row_keys, "
                        "reason, status, decided_by, decision_reason) VALUES (CAST(:iid AS uuid), :view, "
                        "CAST(:cols AS text[]), CAST(:keys AS text[]), :reason, 'denied', 'auto:limit', 'limit')"
                    ),
                    params,
                )
                await db.commit()
            raise HTTPException(status_code=409, detail="OPS_CASE_REQUEST_LIMIT")
        await _check_request_content(db, body.view_name, columns, keys)
        rid = (
            await db.execute(
                text(
                    "INSERT INTO ops_case.unmask_requests (incident_id, view_name, column_names, row_keys, reason) "
                    "VALUES (CAST(:iid AS uuid), :view, CAST(:cols AS text[]), CAST(:keys AS text[]), :reason) "
                    "RETURNING id::text"
                ),
                params,
            )
        ).scalar_one()
        await db.commit()
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("unmask_request", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {"id": rid, "status": "pending"}


@router.get("/ops/case/unmask-requests/{request_id}")
async def get_unmask_request(
    request_id: uuid.UUID,
    x_case_ticket: str | None = Header(default=None, alias="X-Case-Ticket"),
    db: AsyncSession = Depends(get_db),
    _agent: None = Depends(require_case_agent),
) -> dict[str, Any]:
    """その件の申請だけ（別の件の札・存在しない申請は 403）。値は無い。"""
    rid = str(request_id)
    try:
        await set_operator_context(db)
        row = (
            await db.execute(
                text(
                    "SELECT incident_id::text, status, expires_at, read_count, decision_reason "
                    "FROM ops_case.unmask_requests WHERE id = CAST(:rid AS uuid)"
                ),
                {"rid": rid},
            )
        ).first()
        if row is None:
            # 申請の有無を漏らさない（件が無いときと同じ 403）
            raise _forbidden()
        await _verify_ticket(db, row[0], x_case_ticket)
    except DBAPIError as exc:
        await _safe_clear(db)
        raise _unavailable("unmask_request_get", exc) from None
    except BaseException:
        await _safe_clear(db)
        raise
    await _clear_operator(db)
    return {"id": rid, "status": row[1], "expires_at": row[2], "read_count": row[3], "decision_reason": row[4]}
