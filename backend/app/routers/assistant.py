"""ADR-1056 段2: チャット秘書の口 POST /api/v1/assistant/messages。

利用者の文を容器 secretary-agent（DB を持たない）に渡し、頼みの形（請求書／予定／聞き返し）に
書き換えた下書きを返す。ここでは何も作らない（請求書・予定を作るのは画面が今の口を本人のログインで呼ぶとき）。

順番（厳守）: ①守りを通す ②db.commit() ③容器を呼ぶ ④会社の文脈を張り直す ⑤名前探し ⑥返す。
DB の取引を開いたまま AI を待たない。ログは 1 回 1 行（text と答えの中身は書かない）。
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_feature,
    require_permission,
    require_super_admin,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.assistant import (
    AgentEnvelope,
    AssistantMessageIn,
    AssistantMessageOut,
    Candidates,
    DraftItem,
    EventDraft,
    InvoiceDraft,
    UnknownDraft,
    parse_iso,
)
from app.services.secretary_resolve import resolve_names

logger = logging.getLogger(__name__)

router = APIRouter()

SECRETARY_AGENT_URL = os.getenv("SECRETARY_AGENT_URL", "http://secretary-agent:8090")
AGENT_TIMEOUT_SECONDS = 85.0
_JST = ZoneInfo("Asia/Tokyo")

# 守りの Depends。テストは router 側のこの名前で上書きする（require_feature は呼ぶたびに別の関数を返すため）
_feature_secretary_chat = require_feature("secretary_chat")
_perm_customers_view = require_permission("customers.view")
_perm_invoices_create = require_permission("invoices.create")


def _fail(status_code: int, code: str, log_code: str | None = None) -> HTTPException:
    exc = HTTPException(status_code=status_code, detail={"code": code})
    exc._log_code = log_code or code  # type: ignore[attr-defined]
    return exc


def _log(user_id: int, tenant_id: int, started: float, code: str, cost: float | None = None) -> None:
    logger.info(
        "assistant_message user_id=%s tenant_id=%s seconds=%.2f code=%s total_cost_usd=%s",
        user_id,
        tenant_id,
        time.monotonic() - started,
        code,
        cost if cost is not None else "-",
    )


async def _call_agent(text: str) -> dict:
    """容器を呼ぶ。失敗は (HTTPException, ログの code) に直す。"""
    now = datetime.now(_JST).isoformat(timespec="seconds")
    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{SECRETARY_AGENT_URL}/intent",
                json={"text": text, "now": now},
            )
    except httpx.TimeoutException:
        raise _fail(504, "timeout")
    except httpx.HTTPError:
        # 届かない・接続拒否など
        raise _fail(503, "not_ready")

    if resp.status_code == 200:
        try:
            return resp.json()
        except ValueError:
            raise _fail(502, "unreadable")
    if resp.status_code == 503:
        raise _fail(503, "not_ready")
    if resp.status_code == 429:
        raise _fail(429, "busy")
    if resp.status_code == 504:
        raise _fail(504, "timeout")
    if resp.status_code == 502:
        agent_code = None
        try:
            body = resp.json()
            if isinstance(body, dict):
                agent_code = body.get("code")
        except ValueError:
            pass
        if agent_code == "auth_failed":
            raise _fail(503, "auth_failed")
        if agent_code == "cli_failed":
            raise _fail(502, "agent_failed", "cli_failed")
        raise _fail(502, "unreadable")
    raise _fail(502, "unreadable")


@router.post(
    "/assistant/messages",
    response_model=AssistantMessageOut,
    dependencies=[
        Depends(_feature_secretary_chat),
        Depends(require_super_admin),
        Depends(_perm_customers_view),
        Depends(_perm_invoices_create),
    ],
)
async def post_assistant_message(
    body: AssistantMessageIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> AssistantMessageOut:
    started = time.monotonic()
    user_id = current_user.id

    # ② 取引を閉じる（AI を待つ間 DB を開いたままにしない）
    await db.commit()

    # ③ 容器を呼ぶ
    cost: float | None = None
    try:
        raw = await _call_agent(body.text)
        try:
            envelope = AgentEnvelope.model_validate(raw)
        except ValidationError:
            raise _fail(502, "unreadable")
        cost = envelope.total_cost_usd
        intent = envelope.intent

        # 予定の日時の検査（AI が unknown で聞き返すべきところを予定で返した場合もここで止まる）
        event_start = event_end = None
        if intent.kind == "event":
            ev = intent.event
            assert ev is not None
            try:
                event_start = parse_iso(ev.start)
                event_end = parse_iso(ev.end) if ev.end is not None else event_start + timedelta(hours=1)
                if event_end < event_start:
                    raise ValueError("end before start")
            except (ValueError, TypeError):
                raise _fail(502, "unreadable")
    except HTTPException as exc:
        _log(user_id, tenant_id, started, getattr(exc, "_log_code", "unreadable"), cost)
        raise

    # ④ 会社の文脈を張り直す
    await reset_tenant_context(db, tenant_id)

    # ⑤ 名前探し ⑥ 返す
    if intent.kind == "invoice":
        inv = intent.invoice
        assert inv is not None
        candidates = await resolve_names(db, tenant_id, inv.company_name, inv.contact_name)
        draft: InvoiceDraft | EventDraft | UnknownDraft = InvoiceDraft(
            company_name=inv.company_name,
            contact_name=inv.contact_name,
            items=[
                DraftItem(product_name=i.product_name, quantity=i.quantity, unit_price=i.unit_price)
                for i in inv.items
            ],
            due_date=inv.due_date,
            notes=inv.notes,
            currency="JPY",
        )
    elif intent.kind == "event":
        ev = intent.event
        assert ev is not None and event_start is not None and event_end is not None
        candidates = {"companies": [], "contacts": []}
        draft = EventDraft(
            title=ev.title,
            start=ev.start,
            end=ev.end if ev.end is not None else event_end.isoformat(),
            is_all_day=ev.is_all_day,
            location=ev.location,
            description=ev.description,
            calendar_type="personal",
        )
    else:
        assert intent.reply is not None
        candidates = {"companies": [], "contacts": []}
        draft = UnknownDraft(reply=intent.reply)

    _log(user_id, tenant_id, started, "ok", cost)
    return AssistantMessageOut(
        kind=intent.kind,
        draft=draft,
        candidates=Candidates(**candidates),
    )
