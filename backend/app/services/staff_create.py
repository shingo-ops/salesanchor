"""スタッフ（public.users + staff + user_roles）を1人作る共用処理（ADR-1068・ADR-1008）。

POST /staff（管理者が全項目を書く今の新規作成）と、招待リンクからの自己登録（申込）の両方から呼ぶ。
この関数は commit しない。commit・reset_tenant_context・invalidate_user_permissions・
招待メールの鍵（create_invite_token）と送信・schedule_own_staff_sync は呼び出し側に残す。
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.staff import StaffCreate, StaffEmailInput, StaffUIPreferences
from app.services.audit import record_audit_log
from app.services.role_assignment import assign_single_role

# staff.staff_code は VARCHAR(20) NOT NULL（services/tenant.py の staff テーブル定義と同値）
STAFF_CODE_MAX_LENGTH = 20
_PLACEHOLDER_PREFIX = "TMP-"

# 他社か自社かを言い分けない（ADR-1063 便1・K7）。他社在籍を文言から分からないようにする
EMAIL_UNAVAILABLE_DETAIL = "このメールアドレスは登録できません。別のメールアドレスを使ってください。"


def new_placeholder_code() -> str:
    """INSERT 時の一意な仮コード（EMP-%05d へ UPDATE されるまでの値）。VARCHAR(20) に収める。"""
    return _PLACEHOLDER_PREFIX + uuid.uuid4().hex[: STAFF_CODE_MAX_LENGTH - len(_PLACEHOLDER_PREFIX)]


async def resolve_user_for_new_staff(
    db: AsyncSession,
    tenant_id: int,
    data: StaffCreate,
    *,
    allow_reuse: bool = True,
    is_active: bool = True,
) -> tuple[int, bool]:
    """名簿に紐付ける users.id を決める（既存を再利用 or 新規作成。ADR-1008 決定5）。

    allow_reuse=True（POST /staff）: 同じ email の users が、同テナントで名簿なし → それを使う /
    同テナントで名簿あり → 409 / 別テナント → 409 / 無し → 作る。
    allow_reuse=False（自己登録の申込）: 同じ email の users がどこかに1件でもあれば 409。
    新しく作る users の is_active は引数どおり。commit しない。戻り値は (users.id, 新しく作ったか)。
    """
    found = await db.execute(
        text("SELECT id, tenant_id FROM public.users WHERE lower(email) = lower(:email) LIMIT 1"),
        {"email": data.primary_email},
    )
    existing = found.mappings().first()
    if existing is not None:
        if not allow_reuse or existing["tenant_id"] != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMAIL_UNAVAILABLE_DETAIL,
            )
        linked = await db.execute(
            text("SELECT 1 FROM staff WHERE user_id = :uid LIMIT 1"),
            {"uid": existing["id"]},
        )
        if linked.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMAIL_UNAVAILABLE_DETAIL,
            )
        return int(existing["id"]), False

    display_name = f"{data.surname_jp} {data.given_name_jp}"
    created = await db.execute(
        text("""
            INSERT INTO public.users (tenant_id, username, email, full_name, is_active)
            VALUES (:tid, :name, :email, :name, :active)
            RETURNING id
        """),
        {"tid": tenant_id, "name": display_name, "email": data.primary_email, "active": is_active},
    )
    return int(created.scalar_one()), True


async def upsert_ui_prefs(db: AsyncSession, staff_id: int, prefs: StaffUIPreferences | None) -> None:
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


async def replace_additional_emails(
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


async def create_staff_record(
    db: AsyncSession,
    tenant_id: int,
    data: StaffCreate,
    *,
    granter: User,
    allow_reuse: bool,
    is_active: bool,
    audit_extra: dict[str, Any] | None = None,
) -> tuple[int, int, bool]:
    """users（既存の再利用 or 新規）・staff・user_roles・ui_prefs・副メール・監査ログを作る。

    granter は役割の付与者であり、監査ログの user_id でもある。audit_extra は監査ログの new_data に足す。
    commit しない。戻り値は (staff_id, user_id, user_created)。
    """
    staff_code = new_placeholder_code()
    user_id, user_created = await resolve_user_for_new_staff(
        db, tenant_id, data, allow_reuse=allow_reuse, is_active=is_active,
    )
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
    await assign_single_role(db, tenant_id, granter, user_id, data.role_id)
    await upsert_ui_prefs(db, new_id, data.ui_preferences)
    await replace_additional_emails(db, new_id, data.additional_emails)
    new_data = data.model_dump(exclude_none=True, mode="json")
    if audit_extra:
        new_data.update(audit_extra)
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=granter.id,
        action="create", table_name="staff", record_id=new_id,
        new_data=new_data,
    )
    return int(new_id), user_id, user_created
