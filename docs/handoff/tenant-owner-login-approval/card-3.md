# card: 便3 会社のオーナーが社員のログインを許可する口（バックエンド）

状態: カード発行（Opus、2026-11-06）。PO の実装承認は 2026-11-06「1」（このまま作り始める）。設計: docs/handoff/tenant-owner-login-approval/design.md 便3（このカードだけで作業できるように中身を下に全部書く）。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret には触らない。PR は作らない（Opus が作る）。
基準: origin/main `8ba171f49f6571cfb38e76873cf0f8539cf9d202`。下の行番号はすべてこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。消すファイルは無い。PR は Opus が作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に新しいファイルの全文と、足す行の全文を書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin3 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/tenant-owner-bin3-owner-approval-api` を origin から取り、`docs/handoff/tenant-owner-login-approval/card-3.md` が在ること。
- P2 `ls migrations/20261106_140000_add_login_request_admin_requested_at.sql` が在る（便2 の列）。
- P3 `grep -rn "tenant/login-requests\|ask-admin\|is_tenant_owner\|require_tenant_owner" backend/app frontend/src` が 0 件。
- P4 `grep -rn "admin_requested_at" backend` が 0 件。
- P5 次の文がそれぞれちょうど 1 件:
  - `grep -c "# コードが require_permission で求めたキーの集合。経路の読み込み（アプリの起動）でそろう。" backend/app/auth/dependencies.py`
  - `grep -c '"is_tenant_admin": is_tenant_admin(system_keys),' backend/app/routers/roles.py`
  - `grep -c '@router.post("/login-requests/recovery", response_model=SelfTokenResponse)' backend/app/routers/auth.py`
  - `grep -c "tenant_commission_settings,  # ADR-021 Phase 5 / Sprint 5: 報酬計算 MVP" backend/app/main.py`
  - `grep -c 'app.include_router(super_admin_login_requests.router, prefix="/api/v1", tags=\["super-admin"\])' backend/app/main.py`
  - `grep -c "failed_code_attempts INTEGER NOT NULL DEFAULT 0" backend/tests/conftest.py`
  - `grep -c '("POST", "/api/v1/auth/login-requests/recovery"),' backend/tests/test_viewer_isolation.py`

## 1. 触るファイル

新しく作る:
1. `backend/app/routers/tenant_login_requests.py`（2-7）
2. `backend/tests/test_tenant_login_requests.py`（2-13）

書き換える:
3. `backend/app/auth/system_roles.py`（2-1）
4. `backend/app/auth/dependencies.py`（2-2）
5. `backend/app/routers/roles.py`（2-3）
6. `backend/app/auth/devices.py`（2-4）
7. `backend/app/routers/super_admin_login_requests.py`（2-5）
8. `backend/app/services/auth_mail.py`（2-6）
9. `backend/app/routers/auth.py`（2-8）
10. `backend/app/main.py`（2-9）
11. `backend/app/realtime/topics.py`（2-10）
12. `backend/tests/test_viewer_isolation.py`（2-11）
13. `backend/tests/conftest.py`（2-12）
14. `backend/tests/test_new_device_approval.py`（2-14）
15. `frontend/api-contract/openapi.json`（2-15。手で書かず、コマンドで作り直す）

触らない: 上に挙げた以外のすべて。特に `migrations/`、`frontend/src/`、`frontend/api-contract/schema.d.ts`、`.github/`、`scripts/`、`docs/`（このカードを除く）。上のファイルの中でも、書いていない行は 1 文字も変えない。

## 2. 変更の中身

### 2-1. `backend/app/auth/system_roles.py`

関数 `is_tenant_admin` の終わり（`    return bool(system_keys & {ROLE_KEY_OWNER, ROLE_KEY_ADMIN})`）の後の空行 2 つの次（`def compute_permission_keys(` の前）に、次を足す（後ろに空行 2 つ）:
```
def is_tenant_owner(system_keys: set[str]) -> bool:
    """オーナー（system_key=owner）だけか。admin は入れない（ADR-1063）。"""
    return ROLE_KEY_OWNER in system_keys
```

### 2-2. `backend/app/auth/dependencies.py`

(a) 15 行目
変更前: `from app.auth.system_roles import compute_permission_keys, is_tenant_admin`
変更後: `from app.auth.system_roles import compute_permission_keys, is_tenant_admin, is_tenant_owner`

(b) 570 行目 `# コードが require_permission で求めたキーの集合。経路の読み込み（アプリの起動）でそろう。` の直前に、次を足す（足した関数の後ろに空行 2 つを置いて 570 行目に続ける）:
```
async def require_tenant_owner(
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """会社のオーナー（system_key=owner）だけ通す。admin は通さない（ADR-1063）。

    判定の正本は user_roles。users.role は見ない。
    """
    if not is_tenant_owner(await get_user_system_keys(db, user.id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner_only")
    return user
```

### 2-3. `backend/app/routers/roles.py`

(a) 29 行目
変更前: `from app.auth.system_roles import TENANT_HIDDEN_SYSTEM_KEYS, is_tenant_admin`
変更後: `from app.auth.system_roles import TENANT_HIDDEN_SYSTEM_KEYS, is_tenant_admin, is_tenant_owner`

(b) 162 行目 `        "is_tenant_admin": is_tenant_admin(system_keys),` の次に 2 行足す:
```
        # オーナー（system_key=owner）だけか。ログインの許可待ちの鈴を出すかに使う（ADR-1063）
        "is_tenant_owner": is_tenant_owner(system_keys),
```

### 2-4. `backend/app/auth/devices.py`

ファイルの最後（関数 `parse_request_id` の終わり `        return None`）の後に、空行 2 つを置いて次を足す（ファイルの最後は改行 1 つ）。`uuid`・`text`・`NamedTuple`・`_now` は既にある。
```
class AdminDecision(NamedTuple):
    """管理者の許可の結果。outcome は approved / own_request / not_found。"""

    outcome: str
    target_user_id: int | None = None
    target_tenant_id: int | None = None


async def mark_admin_requested(db: AsyncSession, request_id: str) -> bool:
    """「会社の管理者に頼む」を押した時刻を入れる。待っていて未期限で、まだ頼んでいないときだけ True（ADR-1063）。"""
    now = _now()
    row = (
        await db.execute(
            text(
                "UPDATE public.auth_login_requests SET admin_requested_at = :now "
                "WHERE id = :id AND status = 'pending' AND expires_at > :now AND admin_requested_at IS NULL "
                "RETURNING id"
            ),
            {"now": now, "id": request_id},
        )
    ).first()
    return row is not None


async def list_admin_requested(db: AsyncSession, *, tenant_id: int, exclude_user_id: int):
    """同じ会社の人が「会社の管理者に頼む」を押した、待っている依頼（自分の依頼は除く）。

    表 auth_login_requests には RLS が無いので、会社の絞り込み u.tenant_id は必ずここで付ける（ADR-1063）。
    """
    return (
        await db.execute(
            text(
                "SELECT r.id, r.user_id, u.email, u.full_name, r.status, r.label, r.location, "
                "r.created_at, r.expires_at, r.admin_requested_at "
                "FROM public.auth_login_requests r JOIN public.users u ON u.id = r.user_id "
                "WHERE u.tenant_id = :tid AND r.status = 'pending' AND r.expires_at > :now "
                "AND r.admin_requested_at IS NOT NULL AND r.user_id <> :me "
                "ORDER BY r.admin_requested_at DESC LIMIT 200"
            ),
            {"tid": tenant_id, "now": _now(), "me": exclude_user_id},
        )
    ).all()


async def approve_request_as_admin(
    db: AsyncSession,
    *,
    request_id: str,
    approver_user_id: int,
    note: str,
    tenant_id: int | None,
    require_admin_requested: bool,
) -> AdminDecision:
    """管理者が依頼を許可する（super admin と会社のオーナーで同じ部品・ADR-1063）。commit は呼び出し側。

    tenant_id を渡すと、その会社の人の依頼だけを対象にする（会社のオーナー）。None は会社を絞らない（super admin）。
    require_admin_requested が True なら「会社の管理者に頼む」を押した依頼だけを対象にする。
    """
    sql = (
        "SELECT r.user_id, u.tenant_id FROM public.auth_login_requests r "
        "JOIN public.users u ON u.id = r.user_id WHERE r.id = :id"
    )
    params: dict = {"id": request_id}
    if tenant_id is not None:
        sql += " AND u.tenant_id = :tid"
        params["tid"] = tenant_id
    if require_admin_requested:
        sql += " AND r.admin_requested_at IS NOT NULL"
    target = (await db.execute(text(sql), params)).first()
    if target is None:
        return AdminDecision("not_found")
    if target.user_id == approver_user_id:
        return AdminDecision("own_request")
    update_sql = (
        "UPDATE public.auth_login_requests SET status = 'approved', decided_at = :now, "
        "decided_via = 'admin', decided_by_user_id = :admin, decided_note = :note "
        "WHERE id = :id AND status = 'pending' AND expires_at > :now"
    )
    if require_admin_requested:
        update_sql += " AND admin_requested_at IS NOT NULL"
    update_sql += " RETURNING id"
    decided = (
        await db.execute(
            text(update_sql),
            {"now": _now(), "admin": approver_user_id, "note": note, "id": request_id},
        )
    ).first()
    if decided is None:
        return AdminDecision("not_found")
    return AdminDecision("approved", target.user_id, target.tenant_id)
```

### 2-5. `backend/app/routers/super_admin_login_requests.py`

関数 `approve_login_request` の中身のうち、`    rid = devices.parse_request_id(request_id)` から関数の最後（ファイルの最後）`    return AdminApproveResult(status="approved")` までを、次の全文に置き換える（`    require_app_origin(request)` と docstring はそのまま残す）:
```
    rid = devices.parse_request_id(request_id)
    if rid is None:
        raise HTTPException(status_code=404, detail="not_found")
    # 会社のオーナーの許可（ADR-1063）と同じ部品。super admin は会社を絞らず、頼んだかどうかも見ない
    decision = await devices.approve_request_as_admin(
        db,
        request_id=rid,
        approver_user_id=current_user.id,
        note=body.note.strip(),
        tenant_id=None,
        require_admin_requested=False,
    )
    if decision.outcome == "own_request":
        raise HTTPException(status_code=403, detail="cannot_approve_own_request")
    if decision.outcome != "approved":
        raise HTTPException(status_code=404, detail="not_found")
    # 依頼した人の会社の履歴に残す。依頼の id は UUID で整数の列に入らないので record_id は None、note の中身は書かない
    await _record_auth_audit(
        db,
        tenant_id=decision.target_tenant_id,
        user_id=current_user.id,
        action="update",
        table_name="auth_login_requests",
        record_id=None,
        new_data={
            "event": "login_request_approved_admin",
            "request_id": rid,
            "target_user_id": decision.target_user_id,
        },
    )
    await db.commit()
    await publish_user_change(decision.target_user_id, TOPIC_AUTH_LOGIN_REQUEST)
    return AdminApproveResult(status="approved")
```
import の行は変えない（一覧の口がまだ `datetime`・`text` を使う）。手順5 の ruff が「使っていない import」を出したら、その import だけを消し、報告に書く。

### 2-6. `backend/app/services/auth_mail.py`

ファイルの最後（関数 `send_new_device_mail` の終わりの `logger.error(...)` の行）の後に、空行 2 つを置いて次を足す（ファイルの最後は改行 1 つ）:
```
STAFF_LOGIN_HELP_SUBJECT = "【Sales Anchor】社員からログインの許可の依頼 / Login approval request from a staff member"

_STAFF_LOGIN_HELP_BODY = """Sales Anchor で、社員が新しい機械からのログインの許可を頼んでいます。

社員: {staff}
日時（日本時間）: {when}
機械: {device}
場所の目安: {location}

本人に電話か対面で確かめてから、アプリの「管理センター」→「ログインの許可待ち」で許可してください。
心当たりのない依頼は許可しないでください。
このメールにリンクはありません。

---------------------------------------------
A staff member is asking for approval to log in to Sales Anchor from a new device.

Staff: {staff}
Time (JST): {when}
Device: {device}
Approximate location: {location}

Confirm with the staff member by phone or in person, then approve it in the app under "Admin Center" -> "Pending login approvals".
Do not approve a request you do not recognize.
This email contains no links.
---------------------------------------------

{geo_credit}
Sales Anchor
"""


def send_staff_login_help_mail(
    to_addr: str, *, staff: str, when: str, device: str, location: str | None
) -> None:
    """社員が「会社の管理者に頼む」を押したことをオーナーに知らせる（ADR-1063）。BackgroundTasks から呼ぶ同期関数。

    リンクを入れない。パスワード・番号・Cookie の値は入れない。失敗しても外に出さずログに残す。
    """
    settings = smtp_settings()
    if settings is None:
        logger.info("[auth_mail] SMTP not configured, skipping staff login help mail")
        return
    try:
        body = _STAFF_LOGIN_HELP_BODY.format(
            staff=staff,
            when=when,
            device=device,
            location=location or "不明 / unknown",
            geo_credit=GEO_CREDIT if location else "",
        )
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.mail_from
        msg["To"] = to_addr
        msg["Subject"] = STAFF_LOGIN_HELP_SUBJECT
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(settings.host, settings.port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.user, settings.password)
            smtp.send_message(msg)
        logger.info("[auth_mail] staff login help mail sent (to=%s)", _mask_addr(to_addr))
    except Exception as e:  # noqa: BLE001
        logger.error("[auth_mail] staff login help mail failed (to=%s): %s", _mask_addr(to_addr), type(e).__name__)
```

### 2-7. 新しいファイル `backend/app/routers/tenant_login_requests.py`（全文）

```
"""会社のオーナーが、同じ会社の社員のログインの許可待ちを許可する（ADR-1063）。

社員が新しい機械で「会社の管理者に頼む」を押した依頼だけが並ぶ。オーナー（system_key=owner）だけが使える。
表 auth_login_requests には RLS が無いので、SQL には必ず会社の絞り込み（u.tenant_id）を入れる（devices の部品が入れる）。
許可の部品は super admin の許可（ADR-1055 K7）と同じ devices.approve_request_as_admin。
本人確認の方法（note）は記録に書かない。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import devices
from app.auth.dependencies import get_current_tenant, require_tenant_owner, reset_tenant_context
from app.auth.origin import require_app_origin
from app.database import get_db
from app.models import User
from app.realtime.publisher import publish_user_change
from app.realtime.topics import TOPIC_AUTH_LOGIN_REQUEST
from app.routers.auth import _record_auth_audit
from app.routers.super_admin_login_requests import (
    AdminApproveBody,
    AdminApproveResult,
    AdminLoginRequestItem,
    _iso,
)

router = APIRouter()


class TenantLoginRequestItem(AdminLoginRequestItem):
    admin_requested_at: str | None = Field(default=None, description="会社の管理者に頼んだ日時")


class TenantLoginRequestList(BaseModel):
    items: list[TenantLoginRequestItem]


@router.get("/tenant/login-requests", response_model=TenantLoginRequestList)
async def list_tenant_login_requests(
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_tenant_owner),
    db: AsyncSession = Depends(get_db),
):
    """同じ会社の人が「会社の管理者に頼む」を押した、待っている依頼。自分の依頼は出さない。"""
    rows = await devices.list_admin_requested(db, tenant_id=tenant_id, exclude_user_id=current_user.id)
    return TenantLoginRequestList(
        items=[
            TenantLoginRequestItem(
                id=str(r.id),
                user_id=r.user_id,
                email=r.email,
                full_name=r.full_name,
                status=r.status,
                label=r.label,
                location=r.location,
                created_at=_iso(r.created_at),
                expires_at=_iso(r.expires_at),
                admin_requested_at=_iso(r.admin_requested_at),
            )
            for r in rows
        ]
    )


@router.post("/tenant/login-requests/{request_id}/approve", response_model=AdminApproveResult)
async def approve_tenant_login_request(
    request_id: str,
    body: AdminApproveBody,
    request: Request,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_tenant_owner),
    db: AsyncSession = Depends(get_db),
):
    """オーナーが許可する。別の会社の依頼・頼んでいない依頼は 404、自分の依頼は 403。待つ機械は poll で入る。"""
    require_app_origin(request)
    rid = devices.parse_request_id(request_id)
    if rid is None:
        raise HTTPException(status_code=404, detail="not_found")
    decision = await devices.approve_request_as_admin(
        db,
        request_id=rid,
        approver_user_id=current_user.id,
        note=body.note.strip(),
        tenant_id=tenant_id,
        require_admin_requested=True,
    )
    if decision.outcome == "own_request":
        raise HTTPException(status_code=403, detail="cannot_approve_own_request")
    if decision.outcome != "approved":
        raise HTTPException(status_code=404, detail="not_found")
    # 依頼の id は UUID で整数の列に入らないので record_id は None、note の中身は書かない
    await _record_auth_audit(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="update",
        table_name="auth_login_requests",
        record_id=None,
        new_data={
            "event": "login_request_approved_owner",
            "request_id": rid,
            "target_user_id": decision.target_user_id,
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    await publish_user_change(decision.target_user_id, TOPIC_AUTH_LOGIN_REQUEST)
    return AdminApproveResult(status="approved")
```

### 2-8. `backend/app/routers/auth.py`

(a) 15 行目
変更前: `from sqlalchemy import func, select, text`
変更後: `from sqlalchemy import bindparam, func, select, text`

(b) 53 行目
変更前: `from app.services.auth_mail import send_invite_email, send_new_device_mail, send_password_reset_email`
変更後（4 行）:
```
from app.services.auth_mail import (
    send_invite_email,
    send_new_device_mail,
    send_password_reset_email,
    send_staff_login_help_mail,
)
```

(c) 54 行目 `from app.services.invite import create_invite_token, invite_url` の次に 1 行足す:
```
from app.services.user_notices import _owner_user_ids
```
（import の並び順を ruff の I が直したい場合は、手順5 の `ruff check --fix --select I` の結果に従う。）

(d) `@router.post("/login-requests/recovery", response_model=SelfTokenResponse)` の行の直前（関数 poll の終わり `    )` の後の空行 2 つの次）に、次を足す（後ろに空行 2 つを置いて recovery の行に続ける）:
```
class LoginRequestAskAdminResponse(BaseModel):
    status: str = Field(description="requested / already_requested / no_owner")


@router.post("/login-requests/ask-admin", response_model=LoginRequestAskAdminResponse)
async def login_request_ask_admin(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """待つ機械で「会社の管理者に頼む」を押す（Cookie sa_login_pending・ADR-1063）。

    依頼に頼んだ時刻を入れ、同じ会社のオーナー（本人を除く）に合図とメールを送る。1つの依頼で1回だけ。
    オーナーがいないときも時刻は入る（super admin の許可は今までどおり使える）。
    """
    _require_issuance_enabled()
    _require_app_origin(request)
    row = await _load_login_request(db, request)
    if row is None:
        return _pending_closed("expired")
    now = datetime.now(timezone.utc)
    if row.status != "pending" or self_tokens._as_utc(row.expires_at) <= now:
        raise HTTPException(status_code=409, detail="not_pending")
    if not await devices.mark_admin_requested(db, str(row.id)):
        await db.rollback()
        return LoginRequestAskAdminResponse(status="already_requested")
    info = (
        await db.execute(
            text(
                "SELECT r.label, r.location, u.tenant_id, u.full_name, u.email "
                "FROM public.auth_login_requests r JOIN public.users u ON u.id = r.user_id WHERE r.id = :id"
            ),
            {"id": str(row.id)},
        )
    ).first()
    await set_tenant_context(db, info.tenant_id)
    owner_ids = [uid for uid in await _owner_user_ids(db, info.tenant_id) if uid != row.user_id]
    await clear_tenant_context(db)
    owner_emails: list[str] = []
    if owner_ids:
        owner_emails = [
            r[0]
            for r in (
                await db.execute(
                    text(
                        "SELECT email FROM public.users WHERE id IN :ids AND email IS NOT NULL ORDER BY id"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": owner_ids},
                )
            ).all()
        ]
    await _record_auth_audit(
        db,
        tenant_id=info.tenant_id,
        user_id=row.user_id,
        action="update",
        table_name="auth_login_requests",
        record_id=None,
        new_data={
            "event": "login_request_admin_asked",
            "request_id": str(row.id),
            "owner_count": len(owner_ids),
        },
    )
    await db.commit()
    _audit(request, user_id=row.user_id, reason="admin_asked")
    if not owner_ids:
        return LoginRequestAskAdminResponse(status="no_owner")
    for uid in owner_ids:
        await publish_user_change(uid, TOPIC_AUTH_LOGIN_REQUEST)
    staff = f"{info.full_name} <{info.email}>" if info.full_name else (info.email or "")
    when = devices.jst_text(now)
    for addr in owner_emails:
        background_tasks.add_task(
            send_staff_login_help_mail,
            addr,
            staff=staff,
            when=when,
            device=info.label or "不明 / unknown",
            location=info.location,
        )
    return LoginRequestAskAdminResponse(status="requested")
```
注: `self_tokens._as_utc` が無ければ（`grep -n "def _as_utc" backend/app/auth/self_tokens.py` が 0 件）、poll の口が期限を比べている書き方を `grep -n "expires_at" backend/app/routers/auth.py` で探し、同じ書き方にする。見つからなければ `BLOCKED: _as_utc`。

### 2-9. `backend/app/main.py`

(a) 145 行目 `    tenant_commission_settings,  # ADR-021 Phase 5 / Sprint 5: 報酬計算 MVP` の次に 1 行足す:
```
    tenant_login_requests,  # ADR-1063: 会社のオーナーが社員のログインを許可する
```
（この import のかっこの中が名前の順に並んでいて、ruff の I が別の場所を求めたら、`ruff check --fix --select I backend/app/main.py` の結果に従う。）

(b) 254 行目 `app.include_router(super_admin_login_requests.router, prefix="/api/v1", tags=["super-admin"])` の次に 1 行足す:
```
app.include_router(tenant_login_requests.router, prefix="/api/v1", tags=["tenant"], dependencies=[Depends(get_current_tenant)])
```
（`Depends`・`get_current_tenant` は main.py の 5 行目・13 行目で import 済み。）

### 2-10. `backend/app/realtime/topics.py`

(a) 117 行目 `    ("POST", "/api/v1/auth/login-requests/recovery"): "人宛ての合図は口の中で直接送る（ADR-1055）。書き込みの口の自動合図にしない",` の次に 1 行足す:
```
    ("POST", "/api/v1/auth/login-requests/ask-admin"): "人宛ての合図は口の中で直接送る（ADR-1063）。書き込みの口の自動合図にしない",
```
(b) 124 行目 `    ("POST", "/api/v1/super-admin/login-requests/{request_id}/approve"): ...` の次に 1 行足す:
```
    ("POST", "/api/v1/tenant/login-requests/{request_id}/approve"): "人宛ての合図は口の中で直接送る（ADR-1063）。書き込みの口の自動合図にしない",
```

### 2-11. `backend/tests/test_viewer_isolation.py`

45 行目 `        ("POST", "/api/v1/auth/login-requests/recovery"),` の次に 2 行足す:
```
        # ADR-1063: 「会社の管理者に頼む」も Cookie sa_login_pending だけで動き、トークンを見ない
        ("POST", "/api/v1/auth/login-requests/ask-admin"),
```

### 2-12. `backend/tests/conftest.py`

1440 行目
変更前: `                failed_code_attempts INTEGER NOT NULL DEFAULT 0`
変更後（2 行）:
```
                failed_code_attempts INTEGER NOT NULL DEFAULT 0,
                admin_requested_at TIMESTAMP
```

### 2-13. 新しいファイル `backend/tests/test_tenant_login_requests.py`（全文。実 PostgreSQL で会社の切り分けを確かめる）

```
"""会社のオーナーの許可（ADR-1063 便3）を実 PostgreSQL で確かめる。会社番号は 970 / 971。

使い捨て DB を作り、本物の create_tenant_schema（rls_bootstrap）と migration を流し、
アプリ接続役 salesanchor_app（NOBYPASSRLS）で確かめる。
(1) オーナー探し _owner_user_ids は会社の文脈が無いと 0 人（RLS）、文脈があればその会社のオーナーだけ。
(2) devices の部品は別の会社・頼んでいない依頼・自分の依頼を許可しない。一覧は同じ会社の頼んだ依頼だけ。
(3) require_tenant_owner はオーナーだけ通す（admin・社員・別の会社のオーナーは 403）。
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import pytest
from fastapi import HTTPException

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。",
    ),
    pytest.mark.asyncio,
]

_TA = 970
_TB = 971
_OWNER_A = 9700
_STAFF_A = 9701
_ADMIN_A = 9702
_OWNER_B = 9710
_STAFF_B = 9711
# test_users_rls.py と同じ順（self_hosted → auth_events → 機械の表）
_MIGRATIONS = (
    "20261013_160000_add_self_hosted_auth_tables.sql",
    "001_create_auth_events.sql",
    "20261101_130000_add_new_device_approval.sql",
    "20261106_140000_add_login_request_admin_requested_at.sql",
)
_EXTRA_DDL = """
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ NULL;
"""
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
GRANT USAGE ON SCHEMA tenant_970 TO salesanchor_app;
GRANT USAGE ON SCHEMA tenant_971 TO salesanchor_app;
GRANT SELECT ON tenant_970.roles, tenant_970.user_roles TO salesanchor_app;
GRANT SELECT ON tenant_971.roles, tenant_971.user_roles TO salesanchor_app;
"""


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り、2 社・5 人・役割を入れて (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.rls_bootstrap import _apply_migration, bootstrap_tenant_schema

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "owner_lr_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    app_engine = create_async_engine(_with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0)
    try:
        await bootstrap_tenant_schema(admin_engine, _TA)
        await bootstrap_tenant_schema(admin_engine, _TB)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_EXTRA_DDL)
        for mig in _MIGRATIONS:
            await _apply_migration(admin_engine, mig)
        async with admin_engine.begin() as conn:
            for uid, tid in ((_OWNER_A, _TA), (_STAFF_A, _TA), (_ADMIN_A, _TA), (_OWNER_B, _TB), (_STAFF_B, _TB)):
                await conn.execute(
                    text(
                        "INSERT INTO public.users (id, tenant_id, username, email, full_name, is_active) "
                        "VALUES (:u, :t, :n, :e, :n, TRUE)"
                    ),
                    {"u": uid, "t": tid, "n": f"u{uid}", "e": f"u{uid}@example.com"},
                )
            for uid, schema, key in (
                (_OWNER_A, "tenant_970", "owner"),
                (_ADMIN_A, "tenant_970", "admin"),
                (_OWNER_B, "tenant_971", "owner"),
            ):
                await conn.execute(
                    text(
                        f"INSERT INTO {schema}.user_roles (user_id, role_id) "
                        f"SELECT :u, id FROM {schema}.roles WHERE system_key = :k"
                    ),
                    {"u": uid, "k": key},
                )
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
        yield admin_engine, app_engine
    finally:
        await app_engine.dispose()
        await admin_engine.dispose()
        async with control.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await control.dispose()


async def _add_request(admin_engine, user_id: int, *, asked: bool) -> str:
    from sqlalchemy import text

    rid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO public.auth_login_requests "
                "(id, user_id, status, match_number, candidates, pending_token_hash, expires_at, admin_requested_at) "
                "VALUES (:id, :u, 'pending', '12', '123456', :h, :exp, :asked)"
            ),
            {
                "id": rid,
                "u": user_id,
                "h": uuid.uuid4().bytes,
                "exp": now + timedelta(minutes=30),
                "asked": now if asked else None,
            },
        )
    return rid


def _session(app_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    return async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)()


async def test_owner_lookup_needs_tenant_context():
    from app.auth.dependencies import clear_tenant_context, set_tenant_context
    from app.services.user_notices import _owner_user_ids

    async with _fresh() as (_admin, app_engine):
        async with _session(app_engine) as db:
            await clear_tenant_context(db)
            assert await _owner_user_ids(db, _TA) == []
            await set_tenant_context(db, _TA)
            assert await _owner_user_ids(db, _TA) == [_OWNER_A]
            await clear_tenant_context(db)


async def test_devices_parts_keep_to_one_company():
    from sqlalchemy import text

    from app.auth import devices

    async with _fresh() as (admin_engine, app_engine):
        other = await _add_request(admin_engine, _STAFF_B, asked=True)
        unasked = await _add_request(admin_engine, _STAFF_A, asked=False)
        own = await _add_request(admin_engine, _OWNER_A, asked=True)
        good = await _add_request(admin_engine, _STAFF_A, asked=True)
        async with _session(app_engine) as db:
            kw = {"approver_user_id": _OWNER_A, "note": "電話で確認", "tenant_id": _TA, "require_admin_requested": True}
            listed = await devices.list_admin_requested(db, tenant_id=_TA, exclude_user_id=_OWNER_A)
            assert [str(r.id) for r in listed] == [good]
            assert (await devices.approve_request_as_admin(db, request_id=other, **kw)).outcome == "not_found"
            assert (await devices.approve_request_as_admin(db, request_id=unasked, **kw)).outcome == "not_found"
            assert (await devices.approve_request_as_admin(db, request_id=own, **kw)).outcome == "own_request"
            ok = await devices.approve_request_as_admin(db, request_id=good, **kw)
            assert (ok.outcome, ok.target_user_id, ok.target_tenant_id) == ("approved", _STAFF_A, _TA)
            await db.commit()
            again = await devices.approve_request_as_admin(db, request_id=good, **kw)
            assert again.outcome == "not_found"
            assert await devices.mark_admin_requested(db, unasked) is True
            assert await devices.mark_admin_requested(db, unasked) is False
            await db.commit()
        async with admin_engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT status, decided_via, decided_by_user_id, decided_note FROM public.auth_login_requests WHERE id = :id"
                    ),
                    {"id": good},
                )
            ).first()
            assert tuple(row) == ("approved", "admin", _OWNER_A, "電話で確認")
            other_row = (
                await conn.execute(text("SELECT status FROM public.auth_login_requests WHERE id = :id"), {"id": other})
            ).first()
            assert other_row.status == "pending"


async def test_require_tenant_owner_only_lets_owner_in():
    from app.auth.dependencies import clear_tenant_context, require_tenant_owner, set_tenant_context
    from app.models import User

    async with _fresh() as (_admin, app_engine):
        async with _session(app_engine) as db:
            await set_tenant_context(db, _TA)
            owner = User(id=_OWNER_A, tenant_id=_TA, email="o@example.com")
            assert await require_tenant_owner(tenant_id=_TA, user=owner, db=db) is owner
            for uid in (_ADMIN_A, _STAFF_A, _OWNER_B):
                with pytest.raises(HTTPException) as exc:
                    await require_tenant_owner(tenant_id=_TA, user=User(id=uid, tenant_id=_TA, email="x@example.com"), db=db)
                assert exc.value.status_code == 403 and exc.value.detail == "owner_only"
            await clear_tenant_context(db)
```

### 2-14. `backend/tests/test_new_device_approval.py`

(a) 31 行目 `ADMIN_ID = 2103` の次に `OWNER_ID = 2104` を足す。34 行目 `ADMIN_EMAIL = "nd-admin@example.com"` の次に `OWNER_EMAIL = "nd-owner@example.com"` を足す。

(b) fixture `no_redis_and_spies` の中:
- `    publish = AsyncMock()` の次に 2 行足す:
```
    staff_mail = MagicMock()
    owners = AsyncMock(return_value=[])
```
- `         patch("app.routers.super_admin_login_requests.publish_user_change", new=publish), \` の次に 3 行足す:
```
         patch("app.routers.tenant_login_requests.publish_user_change", new=publish), \
         patch("app.routers.auth.send_staff_login_help_mail", new=staff_mail), \
         patch("app.routers.auth._owner_user_ids", new=owners), \
```
- 変更前: `        yield SimpleNamespace(mail=mail, publish=publish)`
  変更後: `        yield SimpleNamespace(mail=mail, publish=publish, staff_mail=staff_mail, owners=owners)`

(c) ファイルの最後に、空行 2 つを置いて次を足す（ファイルの最後は改行 1 つ）:
```
# ── ADR-1063 便3: 会社の管理者に頼む・会社のオーナーが許可する ──────────

TENANT = 999


@pytest.fixture
def owner_keys():
    """会社のオーナーの判定（user_roles）と会社（get_current_tenant）を差し替える。値は試験の中で変える。"""
    from app.auth.dependencies import get_current_tenant
    from app.main import app

    state = SimpleNamespace(keys={"owner"}, tenant=TENANT)

    async def fake_tenant():
        return state.tenant

    async def fake_keys(db, user_id):
        return state.keys

    app.dependency_overrides[get_current_tenant] = fake_tenant
    with patch("app.auth.dependencies.get_user_system_keys", new=fake_keys):
        yield state
    app.dependency_overrides.pop(get_current_tenant, None)


async def _owner_setup(db, password_hash):
    await _insert_user(db, password_hash)  # 頼む社員
    await _insert_user(db, password_hash, user_id=OWNER_ID, email=OWNER_EMAIL)
    return self_tokens.create_access_token(OWNER_ID, OWNER_EMAIL, "pwd")


async def _ask(client):
    return await client.post(f"{AUTH}/login-requests/ask-admin", headers={"origin": ORIGIN})


TENANT_URL = "/api/v1/tenant/login-requests"


async def test_ask_admin_tells_each_owner_once(enforce, machine, db_session, password_hash, spies):
    await _owner_setup(db_session, password_hash)
    spies.owners.return_value = [OWNER_ID, USER_ID]  # 本人がオーナーでも本人には送らない
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    spies.publish.reset_mock()

    first = await _ask(b)
    second = await _ask(b)

    assert first.status_code == 200 and first.json()["status"] == "requested"
    assert second.status_code == 200 and second.json()["status"] == "already_requested"
    assert [c.args[0] for c in spies.publish.await_args_list] == [OWNER_ID]
    spies.staff_mail.assert_called_once()
    assert spies.staff_mail.call_args.args == (OWNER_EMAIL,)
    assert EMAIL in spies.staff_mail.call_args.kwargs["staff"]
    row = await _row(db_session, "SELECT admin_requested_at, status FROM auth_login_requests WHERE id = :id", id=rid)
    assert row.admin_requested_at is not None and row.status == "pending"


async def test_ask_admin_without_owner(enforce, machine, db_session, password_hash, spies):
    await _owner_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    spies.publish.reset_mock()

    resp = await _ask(b)

    assert resp.status_code == 200 and resp.json()["status"] == "no_owner"
    spies.publish.assert_not_awaited()
    spies.staff_mail.assert_not_called()


async def test_ask_admin_needs_waiting_request(enforce, machine, db_session, password_hash):
    await _owner_setup(db_session, password_hash)
    assert (await _ask(machine())).json()["status"] == "expired"  # Cookie が無い
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await db_session.execute(text("UPDATE auth_login_requests SET status = 'rejected' WHERE id = :id"), {"id": rid})
    await db_session.commit()

    resp = await _ask(b)

    assert resp.status_code == 409 and resp.json()["detail"] == "not_pending"


async def test_owner_lists_and_approves_and_machine_gets_in(enforce, machine, db_session, password_hash, owner_keys, spies):
    owner_token = await _owner_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    assert (await _ask(b)).json()["status"] == "no_owner"  # 試験ではオーナー探しを空に差し替えている
    owner = machine()

    listed = await owner.get(TENANT_URL, headers=_bearer(owner_token))
    assert listed.status_code == 200
    assert [i["id"] for i in listed.json()["items"]] == [rid]
    assert listed.json()["items"][0]["admin_requested_at"]

    spies.publish.reset_mock()
    with patch("app.routers.tenant_login_requests._record_auth_audit", new=AsyncMock()) as audit:
        resp = await owner.post(f"{TENANT_URL}/{rid}/approve", json={"note": "電話で確認"}, headers=_bearer(owner_token))
    assert resp.status_code == 200
    row = await _row(db_session, "SELECT status, decided_by_user_id, decided_note, decided_via FROM auth_login_requests")
    assert (row.status, row.decided_by_user_id, row.decided_note, row.decided_via) == ("approved", OWNER_ID, "電話で確認", "admin")
    kwargs = audit.await_args.kwargs
    assert kwargs["tenant_id"] == TENANT and kwargs["user_id"] == OWNER_ID and kwargs["record_id"] is None
    assert kwargs["new_data"] == {"event": "login_request_approved_owner", "request_id": rid, "target_user_id": USER_ID}
    assert [c.args[0] for c in spies.publish.await_args_list] == [USER_ID]

    done = await _poll(b)
    assert done.json()["access_token"]


async def test_owner_cannot_approve_unasked_request(enforce, machine, db_session, password_hash, owner_keys):
    owner_token = await _owner_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)  # 頼むを押していない
    owner = machine()

    assert (await owner.get(TENANT_URL, headers=_bearer(owner_token))).json()["items"] == []
    resp = await owner.post(f"{TENANT_URL}/{rid}/approve", json={"note": "x"}, headers=_bearer(owner_token))
    assert resp.status_code == 404
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"


async def test_owner_of_other_company_sees_nothing(enforce, machine, db_session, password_hash, owner_keys):
    owner_token = await _owner_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await _ask(b)
    owner_keys.tenant = 998  # 別の会社のオーナー
    owner = machine()

    assert (await owner.get(TENANT_URL, headers=_bearer(owner_token))).json()["items"] == []
    resp = await owner.post(f"{TENANT_URL}/{rid}/approve", json={"note": "x"}, headers=_bearer(owner_token))
    assert resp.status_code == 404
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"


@pytest.mark.parametrize("keys", [{"admin"}, {"sales"}, set()])
async def test_only_owner_can_use_tenant_routes(enforce, machine, db_session, password_hash, owner_keys, keys):
    owner_token = await _owner_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await _ask(b)
    owner_keys.keys = keys
    other = machine()

    listed = await other.get(TENANT_URL, headers=_bearer(owner_token))
    resp = await other.post(f"{TENANT_URL}/{rid}/approve", json={"note": "x"}, headers=_bearer(owner_token))

    assert listed.status_code == 403 and listed.json()["detail"] == "owner_only"
    assert resp.status_code == 403 and resp.json()["detail"] == "owner_only"
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"


async def test_owner_cannot_approve_own_request(enforce, machine, db_session, password_hash, owner_keys):
    await _owner_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await _ask(b)
    self_token = self_tokens.create_access_token(USER_ID, EMAIL, "pwd")  # 頼んだ本人がオーナーでも
    me = machine()

    assert (await me.get(TENANT_URL, headers=_bearer(self_token))).json()["items"] == []
    resp = await me.post(f"{TENANT_URL}/{rid}/approve", json={"note": "自分"}, headers=_bearer(self_token))
    assert resp.status_code == 403 and resp.json()["detail"] == "cannot_approve_own_request"
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"
```

### 2-15. `frontend/api-contract/openapi.json`

手で書かない。手順6 のコマンドで作り直す（`.github/workflows/api-contract-check.yml` と同じ作り方）。`frontend/api-contract/schema.d.ts` は触らない。

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/tenant-owner-bin3-owner-approval-api && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P5 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/tenant-owner-login-approval/card-3.md migrations/20261106_140000_add_login_request_admin_requested_at.sql | tail -2
    cd ~/sa && grep -rn "tenant/login-requests\|ask-admin\|is_tenant_owner\|require_tenant_owner" backend/app frontend/src | tail -5; echo "P3 end"
    cd ~/sa && grep -rn "admin_requested_at" backend | tail -5; echo "P4 end"
    cd ~/sa && grep -c "# コードが require_permission で求めたキーの集合。経路の読み込み（アプリの起動）でそろう。" backend/app/auth/dependencies.py; grep -c '"is_tenant_admin": is_tenant_admin(system_keys),' backend/app/routers/roles.py; grep -c '@router.post("/login-requests/recovery", response_model=SelfTokenResponse)' backend/app/routers/auth.py; grep -c "tenant_commission_settings,  # ADR-021 Phase 5 / Sprint 5: 報酬計算 MVP" backend/app/main.py; grep -c 'app.include_router(super_admin_login_requests.router, prefix="/api/v1", tags=\["super-admin"\])' backend/app/main.py; grep -c "failed_code_attempts INTEGER NOT NULL DEFAULT 0" backend/tests/conftest.py; grep -c '("POST", "/api/v1/auth/login-requests/recovery"),' backend/tests/test_viewer_isolation.py
    cd ~/sa && grep -n "def _as_utc" backend/app/auth/self_tokens.py | tail -2

手順3 §2 の変更をする（2-1 → 2-14 の順。2-15 は手順6）

手順4 道具を入れる
    cd ~/sa/backend && pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa && (pip install -q ruff 2>&1 | tail -1); ruff --version | tail -1

手順5 形と見張り（期待: ruff は 0 件、lint_tenant_schema は 0 で終わる）
    cd ~/sa && ruff check --fix --select I backend/app/main.py backend/app/routers/auth.py backend/app/routers/tenant_login_requests.py backend/tests/test_tenant_login_requests.py 2>&1 | tail -5
    cd ~/sa && ruff check backend/app/auth/system_roles.py backend/app/auth/dependencies.py backend/app/routers/roles.py backend/app/auth/devices.py backend/app/routers/super_admin_login_requests.py backend/app/services/auth_mail.py backend/app/routers/tenant_login_requests.py backend/app/routers/auth.py backend/app/main.py backend/app/realtime/topics.py backend/tests/test_viewer_isolation.py backend/tests/test_tenant_login_requests.py backend/tests/test_new_device_approval.py 2>&1 | tail -15
    cd ~/sa && python3 scripts/lint_tenant_schema.py --mode strict backend/app/ 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"

手順6 openapi.json を作り直す
    cd ~/sa/backend && ENVIRONMENT=test python3 -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -3
    cd ~/sa && git diff --stat frontend/api-contract/openapi.json | tail -2
    cd ~/sa && grep -c "/api/v1/tenant/login-requests\|/api/v1/auth/login-requests/ask-admin" frontend/api-contract/openapi.json | tail -1

手順7 試験（期待: すべて passed。PG の試験は手元に PostgreSQL が無ければ skipped で良い）
    cd ~/sa/backend && python3 -m pytest -q -p no:cacheprovider tests/test_new_device_approval.py 2>&1 | tail -15
    cd ~/sa/backend && python3 -m pytest -q -p no:cacheprovider tests/test_viewer_isolation.py tests/test_realtime_topics.py tests/test_origin_check_not_on_get.py tests/test_tenant_admin_ssot.py tests/test_permission_catalog.py tests/test_tenant_login_requests.py 2>&1 | tail -15

手順8 差分を確かめる
    cd ~/sa && git status --short | tail -20
    cd ~/sa && git diff --stat | tail -20

手順9 記録して送る（§1 の 15 個だけを add する）
    cd ~/sa && git add backend/app/routers/tenant_login_requests.py backend/tests/test_tenant_login_requests.py backend/app/auth/system_roles.py backend/app/auth/dependencies.py backend/app/routers/roles.py backend/app/auth/devices.py backend/app/routers/super_admin_login_requests.py backend/app/services/auth_mail.py backend/app/routers/auth.py backend/app/main.py backend/app/realtime/topics.py backend/tests/test_viewer_isolation.py backend/tests/conftest.py backend/tests/test_new_device_approval.py frontend/api-contract/openapi.json && git commit -q -m "feat(auth): tenant owner approves staff login requests (ADR-1063 bin3)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/tenant-owner-bin3-owner-approval-api 2>&1 | tail -3

## 4. 想定される分かれ道

BLOCKED: に入ったら、その場で作業を停止し、それまでの出力と §5 の形の報告を返して終わる（直さずに先へ進まない・別のやり方を試さない）。

- P1〜P5 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- `_as_utc` が無く、poll の口の書き方も見つからない → `BLOCKED: _as_utc`。
- 変更前の行が見つからない・2 か所ある → `BLOCKED: ファイル名と行 変更前の文が一致しない`。
- 手順5 の ruff が I（並び順）以外を出した → 2-5 の「使っていない import」だけは消してよい。それ以外は出力を報告して `BLOCKED: ruff`。
- 手順5 の lint_tenant_schema が 0 以外で終わる → 出力を報告して `BLOCKED: lint_tenant_schema`。
- 手順4 の requirements が入らない・手順6 の openapi が作れない → 出力を報告して `BLOCKED: openapi`（openapi.json を手で書かない）。
- 手順7 で failed / error が 1 件でも出た → 試験の側を直さず、出力の最後 15 行を報告して `BLOCKED: 試験名`。ただし、カードの書き写し間違い（字の打ち間違い・字下げ）が原因だと出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを報告に書く。
- `git status` に §1 の 15 個以外のファイルが出た → それを add せず、名前を報告に書く。
- push が拒まれた → 出力の最後の 3 行を報告して `BLOCKED: push`（force はしない）。

## 5. 報告の形

- 1 行目: 受領確認（`RECEIVED tenant-owner-bin3 HEAD=…`）。
- 手順2・4・5・6・7・8・9 の出力（tail の範囲）をそのまま貼る。
- §4 の分かれ道に入ったら、どれに入ったかと見えたもの。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
