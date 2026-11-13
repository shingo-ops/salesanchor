"""ADR-1056 段2: チャット秘書の口 POST /api/v1/assistant/messages。

利用者の文を担当表の provider の容器（claude は secretary-agent・codex は secretary-codex。どちらも DB を持たない）に渡し、頼みの形（請求書／予定／聞き返し）に
書き換えた下書きを返す。ここでは何も作らない（請求書・予定を作るのは画面が今の口を本人のログインで呼ぶとき）。

順番（厳守）: ①守りを通す・担当表と承認済みの決まりを読む・頼みの大きさを測る ②db.commit() ③容器を呼ぶ・使用の記録に1行 ④会社の文脈を張り直す ⑤名前探し ⑥返す。
DB の取引を開いたまま AI を待たない。ログは 1 回 1 行（text と答えの中身は書かない）。
ADR-1077 便2b: 決まり帳の口（/assistant/rules・design.md §5）もここに置き、秘書の口と同じ守り _SECRETARY_DEPENDENCIES を使う。
"""

from __future__ import annotations

import json
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
    AgentUsage,
    AssistantMessageIn,
    AssistantMessageOut,
    Candidates,
    DraftItem,
    EventDraft,
    InvoiceDraft,
    UnknownDraft,
    parse_iso,
)
from app.schemas.secretary_rules import RuleFeedbackIn, RuleListOut, RuleOut, RuleStatus, RuleTextIn
from app.services.ai_assignment import get_ai_assignment
from app.services.llm_budget import USAGE_SDKS_BY_PROVIDER, UsageCounts, record_usage_isolated
from app.services.secretary_resolve import resolve_names
from app.services.secretary_rules import (
    RuleNotFound,
    RulesFull,
    RuleWrongStatus,
    SecretaryRule,
    add_approved_rule,
    add_candidate,
    approve_candidate,
    list_approved_rule_texts,
    list_rules,
    reject_candidate,
    remove_rule,
)

logger = logging.getLogger(__name__)

router = APIRouter()

SECRETARY_AGENT_URL = os.getenv("SECRETARY_AGENT_URL", "http://secretary-agent:8090")
SECRETARY_CODEX_URL = os.getenv("SECRETARY_CODEX_URL", "http://secretary-codex:8090")
AGENT_TIMEOUT_SECONDS = 85.0
# 容器へ送る頼みの大きさの上限（バイト）。容器の上限 MAX_BODY 16,384（secretary-agent/server.mjs）より小さくする（design.md §3「大きさ」）
AGENT_BODY_MAX_BYTES = 15_000
_JST = ZoneInfo("Asia/Tokyo")

# 守りの Depends。テストは router 側のこの名前で上書きする（require_feature は呼ぶたびに別の関数を返すため）
_feature_secretary_chat = require_feature("secretary_chat")
_perm_customers_view = require_permission("customers.view")
_perm_invoices_create = require_permission("invoices.create")

# 秘書の口と決まり帳の口が同じ 4 つの守りを使う（ADR-1077 便2b・design.md §5。承認できる人の判定は require_super_admin だけ）
_SECRETARY_DEPENDENCIES = [
    Depends(_feature_secretary_chat),
    Depends(require_super_admin),
    Depends(_perm_customers_view),
    Depends(_perm_invoices_create),
]


def agent_url(provider: str) -> str | None:
    """ADR-1058 段3: 担当表の provider → 秘書の容器の宛先（配線の正本はここ1か所。design.md §5-3）。

    ここに無い provider は容器が無いので None（呼び手は not_ready にする）。
    呼ぶたびにこのモジュールの値を読む（試験で宛先を差し替えられるように）。
    """
    return {"claude": SECRETARY_AGENT_URL, "codex": SECRETARY_CODEX_URL}.get(provider)


def _sdk_for(provider: str) -> str | None:
    """使用の記録の sdk（正本は llm_budget.USAGE_SDKS_BY_PROVIDER）。1つに決まらなければ None。"""
    sdks = USAGE_SDKS_BY_PROVIDER.get(provider, frozenset())
    return next(iter(sdks)) if len(sdks) == 1 else None


# 使用の記録の error_code にそのまま使うログの code（design.md §4-2-1 の秘書の読み替え）。ほかは "other"。
_LEDGER_ERROR_CODES = frozenset({"auth_failed", "timeout", "unreadable", "tool_used", "not_ready", "busy"})


def _fail(status_code: int, code: str, log_code: str | None = None) -> HTTPException:
    exc = HTTPException(status_code=status_code, detail={"code": code})
    exc._log_code = log_code or code  # type: ignore[attr-defined]
    return exc


def _log(
    user_id: int,
    tenant_id: int,
    started: float,
    code: str,
    cost: float | None = None,
    error_events: int | None = None,
) -> None:
    # error_events は secretary-codex の error の合図の数（1回あたり1を超えた件数を段3で数える。design.md §5-1）
    logger.info(
        "assistant_message user_id=%s tenant_id=%s seconds=%.2f code=%s total_cost_usd=%s error_events=%s",
        user_id,
        tenant_id,
        time.monotonic() - started,
        code,
        cost if cost is not None else "-",
        error_events if error_events is not None else "-",
    )


def _ledger_error_code(log_code: str) -> str:
    return log_code if log_code in _LEDGER_ERROR_CODES else "other"


def _counts_from(usage: AgentUsage | None) -> UsageCounts:
    """容器の使用量を台帳の列へ（design.md §5-1。tool_use_prompt_tokens・total_tokens は足し算で埋めず None）。"""
    if usage is None:
        return UsageCounts()
    return UsageCounts(
        prompt_tokens=usage.input_tokens,
        cached_content_tokens=usage.cached_input_tokens,
        candidates_tokens=usage.output_tokens,
        thoughts_tokens=usage.reasoning_output_tokens,
    )


async def _record_ledger(
    tenant_id: int,
    model: str,
    sdk: str,
    outcome: str,
    error_code: str | None,
    counts: UsageCounts | None = None,
) -> None:
    """秘書の1回の頼みを使用の記録に1行（別の取引ですぐ commit。失敗は record_usage_isolated がログに出して飲み込む）。"""
    await record_usage_isolated(
        purpose="secretary_intent",
        model=model,
        sdk=sdk,
        counts=counts if counts is not None else UsageCounts(),
        outcome=outcome,
        error_code=error_code,
        tenant_id=tenant_id,
    )


def _agent_payload(text: str, model: str, rules: list[str]) -> bytes:
    """容器への頼みの本文（ADR-1077 便2b）。測ったバイト数と送るバイト数を同じにするため、ここで JSON にする。"""
    now = datetime.now(_JST).isoformat(timespec="seconds")
    body = {"text": text, "now": now, "model": model, "rules": rules}
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


async def _call_agent(payload: bytes, url: str) -> dict:
    """容器を呼ぶ（payload は _agent_payload の値・url は agent_url の値）。失敗は (HTTPException, ログの code) に直す。"""
    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{url}/intent",
                content=payload,
                headers={"Content-Type": "application/json"},
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
        if agent_code == "tool_used":
            # ADR-1058 段3: 道具を使った合図で答えを捨てた（K2②。台帳の error_code も tool_used）
            raise _fail(502, "agent_failed", "tool_used")
        raise _fail(502, "unreadable")
    raise _fail(502, "unreadable")


@router.post(
    "/assistant/messages",
    response_model=AssistantMessageOut,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def post_assistant_message(
    body: AssistantMessageIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> AssistantMessageOut:
    started = time.monotonic()
    user_id = current_user.id

    # ① 担当を読む（commit の前。後に読むと AI を待つ間 DB の取引が開いたままになる。design.md §5-3）
    # 読めない時は容器を呼ばず、台帳にも書かない（sdk と model が分からないため）。
    try:
        assignment = await get_ai_assignment(db, "secretary_intent")
    except Exception:  # noqa: BLE001
        _log(user_id, tenant_id, started, "not_ready", None)
        raise _fail(503, "not_ready") from None
    url = agent_url(assignment.provider)
    sdk = _sdk_for(assignment.provider)
    if url is None or sdk is None:
        _log(user_id, tenant_id, started, "not_ready", None)
        raise _fail(503, "not_ready")

    # ①' 承認済みの決まりを読み、頼みの大きさを測る（commit の前。ADR-1077 便2b・design.md §3「大きさ」）
    # 読めない・大きすぎる時は容器を呼ばず、台帳にも書かない（AI を呼んでいないため）。
    try:
        rules = await list_approved_rule_texts(db, tenant_id)
    except Exception:  # noqa: BLE001
        _log(user_id, tenant_id, started, "rules_unreadable", None)
        raise _fail(503, "not_ready", "rules_unreadable") from None
    payload = _agent_payload(body.text, assignment.model, rules)
    if len(payload) > AGENT_BODY_MAX_BYTES:
        _log(user_id, tenant_id, started, "rules_too_long", None)
        raise _fail(413, "rules_too_long")

    # ② 取引を閉じる（AI を待つ間 DB を開いたままにしない）
    await db.commit()

    # ③ 容器を呼ぶ
    cost: float | None = None
    error_events: int | None = None
    try:
        raw = await _call_agent(payload, url)
        try:
            envelope = AgentEnvelope.model_validate(raw)
        except ValidationError:
            raise _fail(502, "unreadable")
        cost = envelope.total_cost_usd
        error_events = envelope.error_events
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
        log_code = getattr(exc, "_log_code", "unreadable")
        _log(user_id, tenant_id, started, log_code, cost, error_events)
        await _record_ledger(tenant_id, assignment.model, sdk, "failed", _ledger_error_code(log_code))
        raise

    # AI の呼び出しが成功した（容器が 200・形と日時の検査を通った）。この後の失敗でも ok のまま（design.md §4-2-3）
    await _record_ledger(tenant_id, assignment.model, sdk, "ok", None, _counts_from(envelope.usage))

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

    _log(user_id, tenant_id, started, "ok", cost, error_events)
    return AssistantMessageOut(
        kind=intent.kind,
        draft=draft,
        candidates=Candidates(**candidates),
    )


# ---- ADR-1077 便2b: 決まり帳の口（design.md §5）----------------------------------------
# 守りは秘書の口と同じ _SECRETARY_DEPENDENCIES。承認できる人の判定は require_super_admin だけ（R6）。
# 書く口は commit の後に会社の文脈を張り直す（ADR-072）。


def _rule_out(rule: SecretaryRule) -> RuleOut:
    return RuleOut.model_validate(rule, from_attributes=True)


@router.get("/assistant/rules", response_model=RuleListOut, dependencies=_SECRETARY_DEPENDENCIES)
async def get_assistant_rules(
    status: RuleStatus,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> RuleListOut:
    rules = await list_rules(db, tenant_id, status)
    return RuleListOut(rules=[_rule_out(r) for r in rules])


@router.post(
    "/assistant/rules",
    response_model=RuleOut,
    status_code=201,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def post_assistant_rule(
    body: RuleTextIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await add_approved_rule(db, tenant_id, user_id, body.rule_text)
    except RulesFull:
        raise _fail(409, "rules_full") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/feedback",
    response_model=RuleOut,
    status_code=201,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def post_assistant_rule_feedback(
    body: RuleFeedbackIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    rule = await add_candidate(
        db, tenant_id, user_id, body.rule_text, body.source_text, body.source_kind, body.source_reply
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/{rule_id}/approve",
    response_model=RuleOut,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def approve_assistant_rule(
    rule_id: int,
    body: RuleTextIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await approve_candidate(db, tenant_id, rule_id, user_id, body.rule_text)
    except RuleNotFound:
        raise _fail(404, "rule_not_found") from None
    except RuleWrongStatus:
        raise _fail(409, "wrong_status") from None
    except RulesFull:
        raise _fail(409, "rules_full") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/{rule_id}/reject",
    response_model=RuleOut,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def reject_assistant_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await reject_candidate(db, tenant_id, rule_id, user_id)
    except RuleNotFound:
        raise _fail(404, "rule_not_found") from None
    except RuleWrongStatus:
        raise _fail(409, "wrong_status") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/{rule_id}/remove",
    response_model=RuleOut,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def remove_assistant_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await remove_rule(db, tenant_id, rule_id, user_id)
    except RuleNotFound:
        raise _fail(404, "rule_not_found") from None
    except RuleWrongStatus:
        raise _fail(409, "wrong_status") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)
