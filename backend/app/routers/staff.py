from __future__ import annotations

"""
スタッフ管理 API。Phase 1 再設計版。

テナントスキーマの staff / staff_emails / staff_ui_preferences に対する
CRUD を提供する。UI設定は ネストで含めて返す/更新する。

変更履歴:
  2026-04-23: 初版作成（Phase 1 再設計 スプリント C）
"""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import (
    clear_tenant_context,
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    set_tenant_context,
)
from app.cache import invalidate_user_permissions
from app.database import get_db
from app.models import User
from app.routers.roles import _hidden_role_params, _visible_role_sql, _visible_text
from app.schemas.staff import (
    StaffCreate,
    StaffEmailInput,
    StaffProfileUpdate,
    StaffResponse,
    StaffUIPreferences,
    StaffUpdate,
)
from app.services.audit import record_audit_log
from app.services.auth_mail import send_invite_email
from app.services.invite import create_invite_token, invite_enabled, invite_url
from app.services.role_assignment import assign_single_role
from app.services.staff_avatar import (
    AVATAR_MAX_BYTES,
    ERR_SAVE_FAILED,
    ERR_TOO_LARGE,
    AvatarError,
    build_avatar_url,
    delete_avatar_file,
    new_token,
    process_avatar,
    save_avatar,
)

logger = logging.getLogger(__name__)
# staff.staff_code は VARCHAR(20) NOT NULL（services/tenant.py の staff テーブル定義と同値）
STAFF_CODE_MAX_LENGTH = 20
_PLACEHOLDER_PREFIX = "TMP-"


def _new_placeholder_code() -> str:
    """INSERT 時の一意な仮コード（EMP-%05d へ UPDATE されるまでの値）。VARCHAR(20) に収める。"""
    return _PLACEHOLDER_PREFIX + uuid.uuid4().hex[: STAFF_CODE_MAX_LENGTH - len(_PLACEHOLDER_PREFIX)]


async def _resolve_user_for_new_staff(
    db: AsyncSession, tenant_id: int, data: StaffCreate,
) -> tuple[int, bool]:
    """POST /staff 用: 名簿に紐付ける users.id を決める（既存を再利用 or 新規作成。ADR-1008 決定5）。

    同じ email の users が、同テナントで名簿なし → それを使う / 同テナントで名簿あり → 409 /
    別テナント → 409 / 無し → 作る。呼び出し側のトランザクション内で実行する（commit しない）。
    戻り値は (users.id, 新しく作ったか)。
    """
    found = await db.execute(
        text("SELECT id, tenant_id FROM public.users WHERE lower(email) = lower(:email) LIMIT 1"),
        {"email": data.primary_email},
    )
    existing = found.mappings().first()
    if existing is not None:
        if existing["tenant_id"] != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="このメールアドレスは他の会社で使われています",
            )
        linked = await db.execute(
            text("SELECT 1 FROM staff WHERE user_id = :uid LIMIT 1"),
            {"uid": existing["id"]},
        )
        if linked.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="このメールアドレスのスタッフはすでに登録されています",
            )
        return int(existing["id"]), False

    display_name = f"{data.surname_jp} {data.given_name_jp}"
    created = await db.execute(
        text("""
            INSERT INTO public.users (tenant_id, username, email, full_name, is_active)
            VALUES (:tid, :name, :email, :name, true)
            RETURNING id
        """),
        {"tid": tenant_id, "name": display_name, "email": data.primary_email},
    )
    return int(created.scalar_one()), True


router = APIRouter()

# PATCH /staff で role_id が変わるときだけ要る権限（roles.assign）。Depends の外から呼ぶ。
_require_roles_assign = require_permission("roles.assign")

_STAFF_COLS = """
    s.id, s.tenant_id, s.user_id, s.staff_code, s.surname_jp, s.given_name_jp,
    s.surname_kana, s.given_name_kana, s.surname_en, s.given_name_en,
    u.email AS primary_email, s.discord_user_id, rr.id AS role_id, s.status,
    s.is_employee, s.phone, s.avatar_token,
    s.created_at, s.updated_at,
    rr.name AS role_name
"""

# 名簿のロールの正本は user_roles（ADR-1008 P4a）。見えるロールのうち priority 最大の1つを出す。
# 使う側は _visible_text() で text を作り、_hidden_role_params(current_user) を渡す。
# メールの正本は users.email（ADR-1008 P4b）。staff.user_id は NOT NULL なので内部結合で足りる。
_ROLE_JOIN = f"""
    JOIN public.users u ON u.id = s.user_id
    LEFT JOIN roles rr ON rr.id = (
        SELECT r.id FROM user_roles ur JOIN roles r ON r.id = ur.role_id
        WHERE ur.user_id = s.user_id AND {_visible_role_sql("r.system_key")}
        ORDER BY r.priority DESC, r.id LIMIT 1
    )
"""

_UPDATABLE = {
    "surname_jp", "given_name_jp", "surname_kana", "given_name_kana",
    "surname_en", "given_name_en", "discord_user_id",
    "status", "is_employee",
}


async def _fetch_emails(db: AsyncSession, staff_id: int) -> list[str]:
    res = await db.execute(
        text("SELECT email FROM staff_emails WHERE staff_id = :sid ORDER BY id"),
        {"sid": staff_id},
    )
    return [row.email for row in res.fetchall()]


async def _fetch_ui_prefs(db: AsyncSession, staff_id: int) -> StaffUIPreferences | None:
    res = await db.execute(
        text("""
            SELECT dark_mode, show_chat_menu, show_sales_menu, show_settings_menu,
                   show_admin_menu, show_sidebar
            FROM staff_ui_preferences WHERE staff_id = :sid
        """),
        {"sid": staff_id},
    )
    row = res.mappings().first()
    return StaffUIPreferences(**row) if row else None


async def _fetch_locale(db: AsyncSession, user_id: int | None) -> str:
    """public.users の locale カラムを取得（ADR-027）。users.id で引く（ADR-1008）。"""
    result = await db.execute(
        text("SELECT locale FROM public.users WHERE id = :uid LIMIT 1"),
        {"uid": user_id},
    )
    row = result.mappings().first()
    return row["locale"] if row and row["locale"] else "ja"


async def _fetch_theme(db: AsyncSession, user_id: int | None) -> str:
    """public.users の theme カラムを取得（ADR-033）。users.id で引く（ADR-1008）。"""
    result = await db.execute(
        text("SELECT theme FROM public.users WHERE id = :uid LIMIT 1"),
        {"uid": user_id},
    )
    row = result.mappings().first()
    return row["theme"] if row and row["theme"] else "light"


async def _compose(db: AsyncSession, main_row: dict) -> StaffResponse:
    sid = main_row["id"]
    row = {k: v for k, v in main_row.items() if k != "avatar_token"}
    return StaffResponse(
        **row,
        avatar_url=build_avatar_url(main_row.get("avatar_token")),
        emails=await _fetch_emails(db, sid),
        ui_preferences=await _fetch_ui_prefs(db, sid),
        locale=await _fetch_locale(db, main_row["user_id"]),
        theme=await _fetch_theme(db, main_row["user_id"]),
    )


async def _upsert_ui_prefs(db: AsyncSession, staff_id: int, prefs: StaffUIPreferences | None) -> None:
    """UI設定を upsert。prefs=None なら StaffUIPreferences のデフォルト値で行を作る。

    migration 019 の design は「役割権限 AND 本人のUI設定」で最終表示を決めるため、
    staff_ui_preferences 行は全スタッフに存在すべき。POST /staff で ui_preferences
    省略時もデフォルト値で行を作成する。
    """
    if prefs is None:
        prefs = StaffUIPreferences()  # pydantic デフォルト値
    await db.execute(
        text("""
            INSERT INTO staff_ui_preferences (
                staff_id, dark_mode, show_chat_menu, show_sales_menu,
                show_settings_menu, show_admin_menu, show_sidebar
            ) VALUES (:sid, :dm, :chat, :sales, :settings, :admin, :sidebar)
            ON CONFLICT (staff_id) DO UPDATE SET
                dark_mode = EXCLUDED.dark_mode,
                show_chat_menu = EXCLUDED.show_chat_menu,
                show_sales_menu = EXCLUDED.show_sales_menu,
                show_settings_menu = EXCLUDED.show_settings_menu,
                show_admin_menu = EXCLUDED.show_admin_menu,
                show_sidebar = EXCLUDED.show_sidebar,
                updated_at = NOW()
        """),
        {
            "sid": staff_id, "dm": prefs.dark_mode,
            "chat": prefs.show_chat_menu, "sales": prefs.show_sales_menu,
            "settings": prefs.show_settings_menu, "admin": prefs.show_admin_menu,
            "sidebar": prefs.show_sidebar,
        },
    )


async def _replace_additional_emails(
    db: AsyncSession, staff_id: int, emails: list[StaffEmailInput]
) -> None:
    """副メール群を全削除 → 全 INSERT で置換（冪等）"""
    await db.execute(
        text("DELETE FROM staff_emails WHERE staff_id = :sid"),
        {"sid": staff_id},
    )
    for e in emails:
        await db.execute(
            text("""
                INSERT INTO staff_emails (staff_id, email, purpose)
                VALUES (:sid, :email, :purpose)
                ON CONFLICT (staff_id, email) DO NOTHING
            """),
            {"sid": staff_id, "email": e.email, "purpose": e.purpose},
        )


@router.get("/staff/me", response_model=StaffResponse)
async def get_my_staff(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    現在ログイン中ユーザの staff レコードを返す。

    ロジック:
      current_user.id（users.id）と staff.user_id の一致で staff を引く（ADR-1008）。
      見つからなければ 404 を返す。

    実装メモ:
      当初は firebase_uid 経路を主、email を fallback として設計したが、
      `User` モデル（app/models.py）に `firebase_uid` カラムが無いため
      `getattr(current_user, "firebase_uid", None)` は常に None を返し、
      firebase_uid 経路は dead code になっていた（PR #166 review F1）。
      `User` モデル側に firebase_uid を追加する改修は本 PR スコープ外のため、
      経路を削除して email 一意路線に揃え、決定性は `ORDER BY` で確保する。
      将来 `users.firebase_uid` を実装する場合は別 PR でこのエンドポイントに
      経路を再導入する（その際は `ORDER BY` も維持）。

    アクセス制御:
      自分の情報を取得する API なので staff.view 権限は不要。
      get_current_user / get_current_tenant のみで十分。
      （B-1 軽量スコープ: ui_preferences 反映のため全ユーザがアクセスできる必要がある）
    """
    result = await db.execute(
        _visible_text(f"""
            SELECT {_STAFF_COLS}
            FROM staff s
            {_ROLE_JOIN}
            WHERE s.user_id = :uid
            LIMIT 1
        """),
        {"uid": current_user.id, **_hidden_role_params(current_user)},
    )
    row = result.mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="現在のユーザに紐づく staff レコードが見つかりません",
        )
    return await _compose(db, dict(row))


@router.patch("/staff/me/locale", status_code=200)
async def update_my_locale(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    現在ログイン中ユーザの locale を更新する（ADR-027）。
    payload: { "locale": "ja" | "en" }
    """
    locale = payload.get("locale", "ja")
    if locale not in ("ja", "en"):
        raise HTTPException(status_code=400, detail="locale は 'ja' または 'en' のみ有効です")
    await set_tenant_context(db, current_user.tenant_id)
    await db.execute(
        text("UPDATE public.users SET locale = :locale WHERE id = :uid"),
        {"locale": locale, "uid": current_user.id},
    )
    await clear_tenant_context(db)
    await db.commit()
    return {"locale": locale}


@router.patch("/staff/me/theme", status_code=200)
async def update_my_theme(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    現在ログイン中ユーザの theme を更新する（ADR-033）。
    payload: { "theme": "light" | "dark" }
    """
    theme = payload.get("theme", "light")
    if theme not in ("light", "dark"):
        raise HTTPException(status_code=400, detail="theme は 'light' または 'dark' のみ有効です")
    await set_tenant_context(db, current_user.tenant_id)
    await db.execute(
        text("UPDATE public.users SET theme = :theme WHERE id = :uid"),
        {"theme": theme, "uid": current_user.id},
    )
    await clear_tenant_context(db)
    await db.commit()
    return {"theme": theme}


_PROFILE_UPDATABLE = {
    "surname_jp", "given_name_jp", "surname_kana", "given_name_kana",
    "surname_en", "given_name_en",
    "phone",
}


@router.patch("/staff/me/profile", response_model=StaffResponse, status_code=200)
async def update_my_profile(
    data: StaffProfileUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    現在ログイン中ユーザ自身の氏名を更新する。

    管理者権限不要。メールアドレス・ロール・ステータス等は変更不可。
    本人確認: get_current_user が返す current_user.id（staff.user_id）で staff を特定。
    """
    result = await db.execute(
        _visible_text(f"""
            SELECT {_STAFF_COLS}
            FROM staff s
            {_ROLE_JOIN}
            WHERE s.user_id = :uid
            LIMIT 1
        """),
        {"uid": current_user.id, **_hidden_role_params(current_user)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="現在のユーザに紐づく staff レコードが見つかりません",
        )

    staff_id = row["id"]
    update_data = {
        k: v for k, v in data.model_dump(exclude_unset=True, mode="python").items()
        if k in _PROFILE_UPDATABLE
    }
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを少なくとも1つ指定してください")

    set_sql = ", ".join(f"{k} = :{k}" for k in update_data)
    await db.execute(
        text(f"UPDATE staff SET {set_sql}, updated_at = NOW() WHERE id = :id"),
        {**update_data, "id": staff_id},
    )
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="staff", record_id=staff_id,
        new_data=data.model_dump(exclude_unset=True, mode="json"),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    fetched = await db.execute(
        _visible_text(f"""
            SELECT {_STAFF_COLS}
            FROM staff s
            {_ROLE_JOIN}
            WHERE s.id = :id
        """),
        {"id": staff_id, **_hidden_role_params(current_user)},
    )
    return await _compose(db, dict(fetched.mappings().first()))


_AVATAR_MESSAGES = {
    "AVATAR_INVALID_TYPE": "2MB以下のJPG・PNG・WebP画像を選んでください",
    "AVATAR_TOO_LARGE": "画像のサイズが2MBを超えています",
    "AVATAR_SAVE_FAILED": "画像を保存できませんでした",
}


def _avatar_http_error(code: str, http_status: int) -> HTTPException:
    """フロントが code を文言に変換する。detail は dict（{code, detail}）で返す。"""
    return HTTPException(
        status_code=http_status,
        detail={"code": code, "detail": _AVATAR_MESSAGES.get(code, code)},
    )


async def _my_staff_id_and_token(db: AsyncSession, user_id: int) -> tuple[int, str | None]:
    """ログイン中ユーザ本人の staff.id と現在の avatar_token を返す（/staff/me と同じ特定方法）。"""
    result = await db.execute(
        text("SELECT id, avatar_token FROM staff WHERE user_id = :uid LIMIT 1"),
        {"uid": user_id},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="現在のユーザに紐づく staff レコードが見つかりません",
        )
    return row["id"], row["avatar_token"]


async def _fetch_staff_response(
    db: AsyncSession, staff_id: int, current_user: User,
) -> StaffResponse:
    fetched = await db.execute(
        _visible_text(f"SELECT {_STAFF_COLS} FROM staff s {_ROLE_JOIN} WHERE s.id = :id"),
        {"id": staff_id, **_hidden_role_params(current_user)},
    )
    return await _compose(db, dict(fetched.mappings().first()))


@router.post("/staff/me/avatar", response_model=StaffResponse, status_code=200)
async def upload_my_avatar(
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    本人の担当者アイコンを登録・変更する（ADR-159）。

    jpg/png/webp・2MB 以下。Pillow で EXIF 除去・中央正方形切り抜き・256px WebP 化し、
    新 token で保存して旧ファイルを削除する。本人以外は操作できない（権限は本人限定）。
    """
    staff_id, old_token = await _my_staff_id_and_token(db, current_user.id)

    # 上限+1 バイトだけ読む（巨大ファイルをメモリに載せない）
    data = await image.read(AVATAR_MAX_BYTES + 1)
    try:
        # Pillow の処理は CPU を使うため event loop を塞がないようスレッドで実行する
        webp = await run_in_threadpool(process_avatar, data)
        token = new_token()
        save_avatar(token, webp)
    except AvatarError as e:
        code = e.code
        http_status = (
            413 if code == ERR_TOO_LARGE
            else status.HTTP_500_INTERNAL_SERVER_ERROR if code == ERR_SAVE_FAILED
            else status.HTTP_400_BAD_REQUEST
        )
        raise _avatar_http_error(code, http_status) from None

    try:
        await db.execute(
            text("UPDATE staff SET avatar_token = :token, updated_at = NOW() WHERE id = :id"),
            {"token": token, "id": staff_id},
        )
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="update", table_name="staff", record_id=staff_id,
            new_data={"avatar": "set"},
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072
    except Exception:
        await db.rollback()
        delete_avatar_file(token)  # DB に載らなかった新ファイルは残さない
        logger.exception("upload_my_avatar: DB 更新に失敗 tenant=%d staff=%d", tenant_id, staff_id)
        raise _avatar_http_error(ERR_SAVE_FAILED, status.HTTP_500_INTERNAL_SERVER_ERROR) from None

    delete_avatar_file(old_token)
    return await _fetch_staff_response(db, staff_id, current_user)


@router.delete("/staff/me/avatar", response_model=StaffResponse, status_code=200)
async def delete_my_avatar(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """本人の担当者アイコンを削除する（未登録なら何もしない＝冪等）。"""
    staff_id, old_token = await _my_staff_id_and_token(db, current_user.id)
    if old_token:
        await db.execute(
            text("UPDATE staff SET avatar_token = NULL, updated_at = NOW() WHERE id = :id"),
            {"id": staff_id},
        )
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="update", table_name="staff", record_id=staff_id,
            new_data={"avatar": "removed"},
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072
        delete_avatar_file(old_token)
    return await _fetch_staff_response(db, staff_id, current_user)


@router.get("/staff", response_model=list[StaffResponse],
            dependencies=[Depends(require_permission("staff.view"))])
async def list_staff(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conds: list[str] = []
    params: dict = {"limit": per_page, "offset": offset}
    if search:
        conds.append("(s.staff_code ILIKE :search OR s.surname_jp ILIKE :search OR s.given_name_jp ILIKE :search OR u.email ILIKE :search)")
        params["search"] = f"%{search}%"
    if status_filter:
        conds.append("s.status = :st")
        params["st"] = status_filter
    where = f"WHERE {' AND '.join(conds)}" if conds else ""
    result = await db.execute(
        _visible_text(f"""
            SELECT {_STAFF_COLS}
            FROM staff s
            {_ROLE_JOIN}
            {where}
            ORDER BY s.staff_code
            LIMIT :limit OFFSET :offset
        """),
        {**params, **_hidden_role_params(current_user)},
    )
    rows = result.mappings().all()
    return [await _compose(db, dict(row)) for row in rows]


@router.get("/staff/{staff_id}", response_model=StaffResponse,
            dependencies=[Depends(require_permission("staff.view"))])
async def get_staff(staff_id: int, db: AsyncSession = Depends(get_db),
                    tenant_id: int = Depends(get_current_tenant),
                    current_user: User = Depends(get_current_user)):
    result = await db.execute(
        _visible_text(f"""
            SELECT {_STAFF_COLS}
            FROM staff s
            {_ROLE_JOIN}
            WHERE s.id = :id
        """),
        {"id": staff_id, **_hidden_role_params(current_user)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="スタッフが見つかりません")
    return await _compose(db, dict(row))


@router.post("/staff", response_model=StaffResponse, status_code=201,
             dependencies=[Depends(require_permission("staff.create"))])
async def create_staff(data: StaffCreate, background_tasks: BackgroundTasks,
                       db: AsyncSession = Depends(get_db),
                       tenant_id: int = Depends(get_current_tenant),
                       current_user: User = Depends(get_current_user)):
    if data.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id は指定できません",
        )
    # staff_code は常にサーバー側で自動採番する（クライアント指定は受け付けない）
    staff_code = _new_placeholder_code()
    try:
        user_id, user_created = await _resolve_user_for_new_staff(db, tenant_id, data)
        result = await db.execute(
            text("""
                INSERT INTO staff (
                    tenant_id, user_id, staff_code,
                    surname_jp, given_name_jp, surname_kana, given_name_kana,
                    surname_en, given_name_en, discord_user_id,
                    status, is_employee
                ) VALUES (
                    :tid, :uid, :code,
                    :sjp, :gjp, :sk, :gk,
                    :sen, :gen, :did,
                    :st, :is_emp
                )
                RETURNING id
            """),
            {
                "tid": tenant_id, "uid": user_id, "code": staff_code,
                "sjp": data.surname_jp, "gjp": data.given_name_jp,
                "sk": data.surname_kana, "gk": data.given_name_kana,
                "sen": data.surname_en, "gen": data.given_name_en,
                "did": data.discord_user_id,
                "st": data.status.value,
                "is_emp": bool(data.is_employee),
            },
        )
        new_id = result.scalar_one()
        await db.execute(
            text("UPDATE staff SET staff_code = :code WHERE id = :id"),
            {"code": f"EMP-{new_id:05d}", "id": new_id},
        )
        # ロールの正本は user_roles。staff.role_id には書かない（ADR-1008 P4a）
        await assign_single_role(db, tenant_id, current_user, user_id, data.role_id)
        await _upsert_ui_prefs(db, new_id, data.ui_preferences)
        await _replace_additional_emails(db, new_id, data.additional_emails)
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="create", table_name="staff", record_id=new_id,
            new_data=data.model_dump(exclude_none=True, mode="json"),
        )
        # 新しく利用者ができたときだけ、AUTH_PROVIDER=self なら初回設定の鍵を同じトランザクションで作る
        invite_raw = await create_invite_token(db, user_id) if user_created and invite_enabled() else None
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2
        await invalidate_user_permissions(tenant_id, user_id)
        if invite_raw is not None:
            background_tasks.add_task(send_invite_email, data.primary_email, invite_url(invite_raw))
    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning("create_staff IntegrityError: tenant=%d err=%s", tenant_id, e.orig)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="スタッフの登録に失敗しました（同じ値がすでに登録されています: スタッフコード・Discord ID・メールアドレスのいずれか）",
        )
    fetched = await db.execute(
        _visible_text(f"""
            SELECT {_STAFF_COLS}
            FROM staff s
            {_ROLE_JOIN}
            WHERE s.id = :id
        """),
        {"id": new_id, **_hidden_role_params(current_user)},
    )
    return await _compose(db, dict(fetched.mappings().first()))


@router.patch("/staff/{staff_id}", response_model=StaffResponse,
              dependencies=[Depends(require_permission("staff.update"))])
async def update_staff(staff_id: int, data: StaffUpdate,
                       db: AsyncSession = Depends(get_db),
                       tenant_id: int = Depends(get_current_tenant),
                       current_user: User = Depends(get_current_user)):
    old = await db.execute(
        _visible_text(f"SELECT {_STAFF_COLS} FROM staff s {_ROLE_JOIN} WHERE s.id = :id"),
        {"id": staff_id, **_hidden_role_params(current_user)},
    )
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="スタッフが見つかりません")

    update_data = data.model_dump(exclude_unset=True, mode="python")
    if "user_id" in update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="user_id は変更できません")
    if "primary_email" in update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="メールアドレスはここでは変更できません")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="更新するフィールドを少なくとも1つ指定してください")

    ui_prefs = update_data.pop("ui_preferences", None)
    additional_emails = update_data.pop("additional_emails", None)
    new_role_id = update_data.pop("role_id", None)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    for k, v in list(update_data.items()):
        if hasattr(v, "value"):
            update_data[k] = v.value

    # ロールの正本は user_roles（ADR-1008 P4a）。staff.role_id は更新しない。
    # 編集フォームは role_id を毎回送るため、今の表示と同じ値なら何もしない。
    if new_role_id is not None and new_role_id != old_row["role_id"]:
        await _require_roles_assign(current_user=current_user, tenant_id=tenant_id, db=db)
        await assign_single_role(db, tenant_id, current_user, old_row["user_id"], new_role_id)
        role_changed = True
    else:
        role_changed = False

    if update_data:
        set_sql = ", ".join(f"{k} = :{k}" for k in update_data)
        params = {**update_data, "id": staff_id}
        await db.execute(
            text(f"UPDATE staff SET {set_sql}, updated_at = NOW() WHERE id = :id"),
            params,
        )

    if ui_prefs is not None:
        prefs = StaffUIPreferences(**ui_prefs) if isinstance(ui_prefs, dict) else ui_prefs
        await _upsert_ui_prefs(db, staff_id, prefs)

    # additional_emails: None=触らない、[]=全削除、[...]=置換
    if additional_emails is not None:
        email_models = [StaffEmailInput(**e) if isinstance(e, dict) else e for e in additional_emails]
        await _replace_additional_emails(db, staff_id, email_models)

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="staff", record_id=staff_id,
        old_data=dict(old_row), new_data=data.model_dump(exclude_unset=True, mode="json"),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2: commit 後の SELECT で search_path 喪失を防ぐ
    if role_changed:
        await invalidate_user_permissions(tenant_id, old_row["user_id"])

    fetched = await db.execute(
        _visible_text(f"SELECT {_STAFF_COLS} FROM staff s {_ROLE_JOIN} WHERE s.id = :id"),
        {"id": staff_id, **_hidden_role_params(current_user)},
    )
    return await _compose(db, dict(fetched.mappings().first()))


@router.delete("/staff/{staff_id}", status_code=204,
               dependencies=[Depends(require_permission("staff.delete"))])
async def delete_staff(staff_id: int, db: AsyncSession = Depends(get_db),
                       tenant_id: int = Depends(get_current_tenant),
                       current_user: User = Depends(get_current_user)):
    old = await db.execute(
        _visible_text(f"SELECT {_STAFF_COLS} FROM staff s {_ROLE_JOIN} WHERE s.id = :id"),
        {"id": staff_id, **_hidden_role_params(current_user)},
    )
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="スタッフが見つかりません")
    try:
        # 副テーブルは ON DELETE CASCADE で消える
        await db.execute(text("DELETE FROM staff WHERE id = :id"), {"id": staff_id})
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="delete", table_name="staff", record_id=staff_id,
            old_data=dict(old_row),
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この担当者は他のデータから参照されているため削除できません",
        )
