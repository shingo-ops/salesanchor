from __future__ import annotations

"""
スタッフ自己登録の招待 API（ADR-1068・設計 docs/handoff/staff-self-registration/design.md §3-3）。

管理の4本（router・認証必須）:
  POST /staff/join-invites・GET /staff/join-invites・POST /staff/join-invites/{id}/reissue・
  POST /staff/join-invites/{id}/revoke
ログイン不要の2本（public_router）:
  GET /public/staff-join/{鍵}・POST /public/staff-join/{鍵}

メールは送らない（URL を管理者が手で送る）。鍵・登録番号は sha256 だけを保存する。
無効な鍵（形違い・会社なし・期限切れ・使用済み・取消・存在しない）は理由を分けず 404 を1種類で返す。
ログに鍵・登録番号・メール・招待の文字列を出さない。
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import dependencies as auth_deps
from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    set_tenant_context,
)
from app.auth.viewer_signup_code import format_signup_code, generate_signup_code, signup_code_sha256
from app.cache import check_auth_rate_limit, invalidate_user_permissions, record_auth_failure
from app.client_ip import get_client_ip
from app.database import get_db
from app.models import User
from app.schemas.staff import StaffCreate, StaffStatus
from app.schemas.staff_join import (
    StaffJoinInfo,
    StaffJoinInviteCreate,
    StaffJoinInviteCreated,
    StaffJoinInviteItem,
    StaffJoinSubmit,
    StaffJoinSubmitted,
)
from app.services.role_assignment import check_assignable_role
from app.services.staff_create import EMAIL_UNAVAILABLE_DETAIL, create_staff_record
from app.services.staff_join import (
    JOIN_LINK_TTL,
    REG_CODE_TTL,
    as_utc,
    create_reception_invite,
    hash_join_key,
    join_url,
    new_join_key,
    parse_join_key,
)

logger = logging.getLogger(__name__)

router = APIRouter()  # 認証必須（main.py で get_current_tenant を付けて登録）
public_router = APIRouter()  # ログイン不要

INVITE_INVALID = "staff_join_invalid"  # 無効の理由は区別しない（推測防止）
TOO_MANY = "staff_join_too_many_attempts"
CREATOR_GONE_DETAIL = "招待を作った管理者が今は招待できません。管理者に連絡してください。"

_require_staff_create = require_permission("staff.create")
_require_staff_view = require_permission("staff.view")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _invalid() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=INVITE_INVALID)


# ─────────────────────────── 管理（認証必須） ───────────────────────────

@router.post("/staff/join-invites", response_model=StaffJoinInviteCreated, status_code=201,
             dependencies=[Depends(_require_staff_create)])
async def create_join_invite(
    data: StaffJoinInviteCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """招待を1本作り、URL を1回だけ返す。メールは送らない。"""
    await check_assignable_role(db, tenant_id, current_user, data.role_id)  # 400 / 403
    key = new_join_key(tenant_id)
    expires_at = _now() + JOIN_LINK_TTL
    invite_id = int((await db.execute(
        text(
            "INSERT INTO staff_join_invites (tenant_id, role_id, created_by, token_hash, expires_at, status) "
            "VALUES (:tid, :rid, :uid, :th, :exp, 'open') RETURNING id"
        ),
        {
            "tid": tenant_id,
            "rid": data.role_id,
            "uid": current_user.id,
            "th": hash_join_key(key),
            "exp": expires_at,
        },
    )).scalar_one())
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return StaffJoinInviteCreated(id=invite_id, url=join_url(key), expires_at=expires_at)


@router.get("/staff/join-invites", response_model=list[StaffJoinInviteItem],
            dependencies=[Depends(_require_staff_view)])
async def list_join_invites(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """open・submitted を新しい順に返す（状態・役割名・期限・作った人）。鍵は返さない。"""
    rows = (await db.execute(
        text(
            "SELECT id, status, role_id, expires_at, created_at, created_by FROM staff_join_invites "
            "WHERE tenant_id = :tid AND status IN ('open', 'submitted') "
            "ORDER BY created_at DESC, id DESC"
        ),
        {"tid": tenant_id},
    )).all()
    role_names = {
        int(r[0]): r[1]
        for r in (await db.execute(
            text("SELECT id, name FROM roles WHERE tenant_id = :tid"), {"tid": tenant_id},
        )).all()
    }
    creator_ids = sorted({int(i.created_by) for i in rows})
    creator_names: dict[int, str | None] = {}
    for uid in creator_ids:
        found = (await db.execute(
            text("SELECT full_name FROM public.users WHERE id = :id"), {"id": uid},
        )).first()
        creator_names[uid] = found[0] if found else None
    return [
        StaffJoinInviteItem(
            id=int(i.id),
            status=i.status,
            role_id=int(i.role_id),
            role_name=role_names.get(int(i.role_id)),
            expires_at=as_utc(i.expires_at),
            created_at=as_utc(i.created_at),
            created_by=int(i.created_by),
            created_by_name=creator_names.get(int(i.created_by)),
        )
        for i in rows
    ]


async def _load_open_invite(db: AsyncSession, tenant_id: int, invite_id: int):
    invite = (await db.execute(
        text(
            "SELECT id, status, role_id FROM staff_join_invites "
            "WHERE id = :id AND tenant_id = :tid FOR UPDATE"
        ),
        {"id": invite_id, "tid": tenant_id},
    )).first()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:staff_join_invite")
    if invite.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="受付中の招待だけ操作できます")
    return invite


@router.post("/staff/join-invites/{invite_id}/reissue", response_model=StaffJoinInviteCreated,
             dependencies=[Depends(_require_staff_create)])
async def reissue_join_invite(
    invite_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """open の招待だけ。新しい鍵を作り、期限を 72 時間に戻す。古い鍵は開けなくなる。"""
    invite = await _load_open_invite(db, tenant_id, invite_id)
    await check_assignable_role(db, tenant_id, current_user, int(invite.role_id))
    key = new_join_key(tenant_id)
    expires_at = _now() + JOIN_LINK_TTL
    await db.execute(
        text(
            "UPDATE staff_join_invites SET token_hash = :th, expires_at = :exp "
            "WHERE id = :id AND tenant_id = :tid"
        ),
        {"th": hash_join_key(key), "exp": expires_at, "id": invite_id, "tid": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return StaffJoinInviteCreated(id=invite_id, url=join_url(key), expires_at=expires_at)


@router.post("/staff/join-invites/{invite_id}/revoke", status_code=200,
             dependencies=[Depends(_require_staff_create)])
async def revoke_join_invite(
    invite_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """open の招待だけ。revoked にする。"""
    await _load_open_invite(db, tenant_id, invite_id)
    await db.execute(
        text(
            "UPDATE staff_join_invites SET status = 'revoked', revoked_at = :now "
            "WHERE id = :id AND tenant_id = :tid"
        ),
        {"now": _now(), "id": invite_id, "tid": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return {"id": invite_id, "status": "revoked"}


# ─────────────────────── ログイン不要（鍵で引く） ───────────────────────

async def _open_invite_by_key(db: AsyncSession, key: str, ip: str, *, for_update: bool):
    """鍵から有効な招待を引く。無効はすべて同じ 404。鍵の先頭の会社番号で set_tenant_context してから RLS のもとで引く。"""
    parsed = parse_join_key(key)
    if parsed is None:
        await record_auth_failure(ip)
        raise _invalid()  # 形が合わなければ DB を引かない
    tenant_id, raw = parsed
    tenant = (await db.execute(
        text("SELECT is_active FROM public.tenants WHERE id = :tid"), {"tid": tenant_id},
    )).first()
    if tenant is None or not tenant[0]:
        await record_auth_failure(ip)
        raise _invalid()
    await set_tenant_context(db, tenant_id)
    sql = (
        "SELECT id, tenant_id, role_id, created_by, status, expires_at FROM staff_join_invites "
        "WHERE token_hash = :th"
    )
    if for_update:
        sql += " FOR UPDATE"
    invite = (await db.execute(text(sql), {"th": hash_join_key(raw)})).first()
    expires = as_utc(invite.expires_at) if invite is not None else None
    if (
        invite is None
        or int(invite.tenant_id) != tenant_id
        or invite.status != "open"
        or expires is None
        or expires <= _now()
    ):
        await db.rollback()
        await record_auth_failure(ip)
        raise _invalid()
    return invite


async def _role_name(db: AsyncSession, tenant_id: int, role_id: int) -> str | None:
    found = (await db.execute(
        text("SELECT name FROM roles WHERE id = :rid AND tenant_id = :tid"), {"rid": role_id, "tid": tenant_id},
    )).first()
    return found[0] if found else None


@public_router.get("/public/staff-join/{key}", response_model=StaffJoinInfo)
async def get_join_info(key: str, request: Request, db: AsyncSession = Depends(get_db)):
    """会社名・役割名・期限を返す。無効なら 404 を1種類で返す。"""
    ip = get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail=TOO_MANY)
    invite = await _open_invite_by_key(db, key, ip, for_update=False)
    tenant_id = int(invite.tenant_id)
    tenant_name = (await db.execute(
        text("SELECT tenant_name FROM public.tenants WHERE id = :tid"), {"tid": tenant_id},
    )).scalar_one()
    return StaffJoinInfo(
        tenant_name=tenant_name,
        role_name=await _role_name(db, tenant_id, int(invite.role_id)),
        expires_at=as_utc(invite.expires_at),
    )


@public_router.post("/public/staff-join/{key}", response_model=StaffJoinSubmitted)
async def submit_join(key: str, data: StaffJoinSubmit, request: Request, db: AsyncSession = Depends(get_db)):
    """申込。users（無効）・staff（登録待ち）・役割を作り、登録番号を1回だけ返す。メールは送らない。"""
    ip = get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail=TOO_MANY)

    # (1) 招待の行を FOR UPDATE で取る（open で期限内）
    invite = await _open_invite_by_key(db, key, ip, for_update=True)
    tenant_id = int(invite.tenant_id)
    try:
        # (2) 招待を作った人を検査し直す（停止・staff.create なし・役割の検査）。どれか1つでも通らなければ 403
        granter = (await db.execute(
            select(User).where(User.id == invite.created_by, User.tenant_id == tenant_id)
        )).scalars().first()
        if granter is None or not granter.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CREATOR_GONE_DETAIL)
        # 実行時に auth_deps から引く（require_permission と同じ関数。権限の判定を1か所に保つ）
        if "staff.create" not in await auth_deps.load_user_permissions(db, tenant_id, int(granter.id)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CREATOR_GONE_DETAIL)
        try:
            await check_assignable_role(db, tenant_id, granter, int(invite.role_id))
        except HTTPException:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CREATOR_GONE_DETAIL) from None

        # (3) 人と staff を作る。users は is_active=false・staff は pending。既存のメールは会社を問わず 409
        staff_data = StaffCreate(
            **data.model_dump(),
            role_id=int(invite.role_id),
            status=StaffStatus.pending,
        )
        staff_id, user_id, _created = await create_staff_record(
            db, tenant_id, staff_data,
            granter=granter, allow_reuse=False, is_active=False,
            audit_extra={"via": "self_registration"},
        )

        # (4) 登録番号 (5) 行を submitted に
        code = generate_signup_code()
        now = _now()
        await db.execute(
            text(
                "UPDATE staff_join_invites SET status = 'submitted', user_id = :uid, staff_id = :sid, "
                "reg_code_hash = :rh, reg_code_expires_at = :rexp, submitted_at = :now "
                "WHERE id = :id AND tenant_id = :tid"
            ),
            {
                "uid": user_id,
                "sid": staff_id,
                "rh": signup_code_sha256(code),
                "rexp": now + REG_CODE_TTL,
                "now": now,
                "id": int(invite.id),
                "tid": tenant_id,
            },
        )
        # (6) commit → reset_tenant_context → invalidate_user_permissions
        await db.commit()
        await reset_tenant_context(db, tenant_id)
        await invalidate_user_permissions(tenant_id, user_id)
    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("staff join: IntegrityError tenant=%d kind=%s", tenant_id, type(exc.orig).__name__)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_UNAVAILABLE_DETAIL) from None

    # commit の後に Discord の招待を作る（Discord を待つ間 DB を開けない）。作れなければ null
    invite_url = await create_reception_invite(db, tenant_id)
    return StaffJoinSubmitted(registration_code=format_signup_code(code), discord_invite_url=invite_url)
