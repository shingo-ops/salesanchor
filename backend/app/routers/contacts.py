from __future__ import annotations

"""
担当者管理API（CRUD）。Phase 1-B-2 Step 5b-1 で新設。

テナントスキーマの contacts 本体 + 副テーブル（contact_emails /
contact_discord / contact_contact_channels）を一括で扱う。

エンドポイント:
  GET    /api/v1/contacts                      - 全担当者一覧（検索可）
  GET    /api/v1/contacts/{contact_id}         - 単一担当者
  POST   /api/v1/contacts                      - 新規担当者（company_id 必須）
  PATCH  /api/v1/contacts/{contact_id}         - 部分更新
  DELETE /api/v1/contacts/{contact_id}         - 削除
  GET    /api/v1/companies/{company_id}/contacts - 会社配下の担当者一覧
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
from app.cache import invalidate_dashboard_cache
from app.database import get_db
from app.models import User
from app.schemas.contact import (
    ContactChannelInput,
    ContactChannelResponse,
    ContactCreate,
    ContactDiscordInput,
    ContactDiscordResponse,
    ContactEmailInput,
    ContactEmailResponse,
    ContactMergeRequest,
    ContactResponse,
    ContactUpdate,
)
from app.services.audit import (
    build_subtable_diff,
    record_audit_log,
    snapshot_subtable_rows,
)

# 副テーブル diff のスナップショット対象列（id / *_at は audit.diff_rows 内で除外）。
# 明示列指定にして、新カラム追加時の意図しない diff ノイズを防ぐ。
_AUDIT_EMAIL_COLUMNS = ["email", "purpose"]
_AUDIT_DISCORD_COLUMNS = [
    "is_joined", "channel_id", "user_id", "invoice_webhook", "shipment_webhook",
]
_AUDIT_CHANNEL_COLUMNS = ["channel", "purpose", "is_primary"]


async def _snapshot_contact_subtables(db: AsyncSession, contact_id: int) -> dict[str, object]:
    """audit_log 用に contact の副テーブルをスナップショットする。

    PR #145 F9: companies/contacts の副テーブル変更が audit_logs に記録されない問題の対応。

    contact_discord は 1:1 のため list ではなく単一 dict（または None）として扱う。
    """
    discord_rows = await snapshot_subtable_rows(
        db, "contact_discord", "contact_id", contact_id, _AUDIT_DISCORD_COLUMNS,
    )
    return {
        "contact_emails": await snapshot_subtable_rows(
            db, "contact_emails", "contact_id", contact_id, _AUDIT_EMAIL_COLUMNS,
        ),
        "contact_discord": discord_rows[0] if discord_rows else None,
        "contact_contact_channels": await snapshot_subtable_rows(
            db, "contact_contact_channels", "contact_id", contact_id, _AUDIT_CHANNEL_COLUMNS,
        ),
    }

logger = logging.getLogger(__name__)
router = APIRouter()

_CONTACT_COLUMNS = """
    id, tenant_id, company_id, contact_code, lead_id,
    surname, given_name, display_name, job_title, department,
    is_primary_contact, primary_email, primary_phone,
    status, notes, created_at, updated_at
"""

_UPDATABLE_COLUMNS = {
    "company_id", "lead_id",
    "surname", "given_name", "display_name", "job_title", "department",
    "is_primary_contact", "primary_email", "primary_phone",
    "status", "notes",
}


async def _fetch_emails(db: AsyncSession, contact_id: int) -> list[ContactEmailResponse]:
    res = await db.execute(
        text("SELECT id, email, purpose FROM contact_emails WHERE contact_id = :cid ORDER BY id"),
        {"cid": contact_id},
    )
    return [ContactEmailResponse(**row) for row in res.mappings().all()]


async def _fetch_discord(db: AsyncSession, contact_id: int) -> ContactDiscordResponse | None:
    res = await db.execute(
        text("""
            SELECT is_joined, channel_id, user_id, invoice_webhook, shipment_webhook
            FROM contact_discord WHERE contact_id = :cid
        """),
        {"cid": contact_id},
    )
    row = res.mappings().first()
    return ContactDiscordResponse(**row) if row else None


async def _fetch_contact_channels(db: AsyncSession, contact_id: int) -> list[ContactChannelResponse]:
    res = await db.execute(
        text("""
            SELECT id, channel, purpose, is_primary
            FROM contact_contact_channels
            WHERE contact_id = :cid
            ORDER BY is_primary DESC, id
        """),
        {"cid": contact_id},
    )
    return [ContactChannelResponse(**row) for row in res.mappings().all()]


async def _compose_response(db: AsyncSession, main_row: dict) -> ContactResponse:
    cid = main_row["id"]
    return ContactResponse(
        **main_row,
        emails=await _fetch_emails(db, cid),
        discord=await _fetch_discord(db, cid),
        contact_channels=await _fetch_contact_channels(db, cid),
    )


async def _replace_emails(db: AsyncSession, contact_id: int, emails: list[ContactEmailInput]) -> None:
    await db.execute(
        text("DELETE FROM contact_emails WHERE contact_id = :cid"),
        {"cid": contact_id},
    )
    for em in emails:
        await db.execute(
            text("""
                INSERT INTO contact_emails (contact_id, email, purpose)
                VALUES (:cid, :email, :purpose)
                ON CONFLICT (contact_id, email) DO NOTHING
            """),
            {"cid": contact_id, "email": em.email, "purpose": em.purpose},
        )


async def _upsert_discord(db: AsyncSession, contact_id: int, data: ContactDiscordInput | None) -> None:
    if data is None:
        await db.execute(
            text("DELETE FROM contact_discord WHERE contact_id = :cid"),
            {"cid": contact_id},
        )
        return
    await db.execute(
        text("""
            INSERT INTO contact_discord (
                contact_id, is_joined, channel_id, user_id,
                invoice_webhook, shipment_webhook
            ) VALUES (
                :cid, :is_joined, :channel_id, :user_id, :invoice_webhook, :shipment_webhook
            )
            ON CONFLICT (contact_id) DO UPDATE SET
                is_joined = EXCLUDED.is_joined,
                channel_id = EXCLUDED.channel_id,
                user_id = EXCLUDED.user_id,
                invoice_webhook = EXCLUDED.invoice_webhook,
                shipment_webhook = EXCLUDED.shipment_webhook,
                updated_at = NOW()
        """),
        {
            "cid": contact_id,
            "is_joined": data.is_joined,
            "channel_id": data.channel_id,
            "user_id": data.user_id,
            "invoice_webhook": data.invoice_webhook,
            "shipment_webhook": data.shipment_webhook,
        },
    )
    # is_joined=TRUE の場合、contact_contact_channels に 'discord' 行を自動追加（Phase 1-B-1 と同じ挙動）
    if data.is_joined:
        await db.execute(
            text("""
                INSERT INTO contact_contact_channels (contact_id, channel, purpose, is_primary)
                SELECT :cid, 'discord', 'Discord連携', FALSE
                WHERE NOT EXISTS (
                    SELECT 1 FROM contact_contact_channels
                    WHERE contact_id = :cid AND channel = 'discord'
                )
            """),
            {"cid": contact_id},
        )


async def _replace_contact_channels(
    db: AsyncSession, contact_id: int, channels: list[ContactChannelInput]
) -> None:
    await db.execute(
        text("DELETE FROM contact_contact_channels WHERE contact_id = :cid"),
        {"cid": contact_id},
    )
    primary_seen = False
    for ch in channels:
        is_primary = ch.is_primary and not primary_seen
        if is_primary:
            primary_seen = True
        await db.execute(
            text("""
                INSERT INTO contact_contact_channels (contact_id, channel, purpose, is_primary)
                VALUES (:cid, :channel, :purpose, :is_primary)
            """),
            {
                "cid": contact_id,
                "channel": ch.channel,
                "purpose": ch.purpose,
                "is_primary": is_primary,
            },
        )


async def _clear_primary_contact_flag(db: AsyncSession, company_id: int, keep_contact_id: int | None = None) -> None:
    """指定 company の is_primary_contact=TRUE を全て FALSE にクリア（keep_contact_id 以外）。
    1社1 primary の部分UNIQUE INDEX と整合させるため、新 primary 指定前にクリアする。
    """
    if keep_contact_id is not None:
        await db.execute(
            text("""
                UPDATE contacts SET is_primary_contact = FALSE
                WHERE company_id = :cid AND id != :keep AND is_primary_contact = TRUE
            """),
            {"cid": company_id, "keep": keep_contact_id},
        )
    else:
        await db.execute(
            text("""
                UPDATE contacts SET is_primary_contact = FALSE
                WHERE company_id = :cid AND is_primary_contact = TRUE
            """),
            {"cid": company_id},
        )


# ========== Endpoints ==========


@router.get(
    "/contacts",
    response_model=list[ContactResponse],
    dependencies=[Depends(require_permission("customers.view"))],
)
async def list_contacts(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    company_id: int | None = Query(default=None, description="特定会社の担当者のみ"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """担当者一覧。検索対象は contact_code / display_name / primary_email / primary_phone。"""
    offset = (page - 1) * per_page
    where_clauses = []
    params: dict = {"limit": per_page, "offset": offset}

    if search:
        where_clauses.append(
            "(contact_code ILIKE :search OR display_name ILIKE :search "
            "OR primary_email ILIKE :search OR primary_phone ILIKE :search "
            "OR surname ILIKE :search OR given_name ILIKE :search)"
        )
        params["search"] = f"%{search}%"
    if company_id is not None:
        where_clauses.append("company_id = :company_id")
        params["company_id"] = company_id

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    # PR #147 review F5: company_id 絞り込み時は CompanyContactSelector のドロップダウンで
    # 主担当を先頭に表示する UX 期待があるため、is_primary_contact DESC を最優先にしつつ、
    # 同じ primary フラグ内では最新更新順を維持する。company_id 絞り込みなしの一覧は従来どおり
    # 更新順（ORDER BY updated_at DESC）。
    order_sql = (
        "ORDER BY is_primary_contact DESC, updated_at DESC"
        if company_id is not None
        else "ORDER BY updated_at DESC"
    )
    result = await db.execute(
        text(f"""
            SELECT {_CONTACT_COLUMNS}
            FROM contacts
            {where_sql}
            {order_sql}
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.mappings().all()
    return [await _compose_response(db, dict(row)) for row in rows]


@router.get(
    "/companies/{company_id}/contacts",
    response_model=list[ContactResponse],
    dependencies=[Depends(require_permission("customers.view"))],
)
async def list_company_contacts(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """指定会社の全担当者を取得（is_primary_contact=TRUE が先頭）。"""
    # 会社存在チェック
    exists = await db.execute(
        text("SELECT 1 FROM companies WHERE id = :id"),
        {"id": company_id},
    )
    if exists.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会社が見つかりません")

    result = await db.execute(
        text(f"""
            SELECT {_CONTACT_COLUMNS}
            FROM contacts
            WHERE company_id = :cid
            ORDER BY is_primary_contact DESC, contact_code
        """),
        {"cid": company_id},
    )
    rows = result.mappings().all()
    return [await _compose_response(db, dict(row)) for row in rows]


@router.get(
    "/contacts/channel-duplicate",
    dependencies=[Depends(require_permission("customers.view"))],
    summary="テナント内の同一チャンネルID重複チェック（保存前 best-effort 警告用）",
    tags=["contacts"],
)
async def check_channel_duplicate(
    channel: str = Query(..., max_length=30),
    purpose: str = Query(..., max_length=50),
    exclude_contact_id: int = Query(..., description="チェック対象外にする自分自身の contact_id"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """同一テナント内で channel + purpose が一致する別担当者を返す。

    戻り値: { contact_id, contact_code, display_name } または null（重複なし）。
    保存前の警告用途のため、結果は best-effort（ロックなし）。
    パスパラメータ競合を避けるため GET /contacts/{contact_id} より先に定義すること。
    """
    ccc_t = tenant_table_ref(db, tenant_id, "contact_contact_channels")
    ct_t = tenant_table_ref(db, tenant_id, "contacts")

    res = await db.execute(
        text(f"""
            SELECT c.id AS contact_id, c.contact_code, c.display_name
            FROM {ccc_t} ccc
            JOIN {ct_t} c ON c.id = ccc.contact_id
            WHERE ccc.channel = :channel
              AND COALESCE(ccc.purpose, '') = COALESCE(:purpose, '')
              AND ccc.contact_id != :exclude_id
            LIMIT 1
        """),
        {"channel": channel, "purpose": purpose, "exclude_id": exclude_contact_id},
    )
    row = res.mappings().first()
    if row is None:
        return None
    return dict(row)


@router.get(
    "/contacts/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("customers.view"))],
)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(f"SELECT {_CONTACT_COLUMNS} FROM contacts WHERE id = :id"),
        {"id": contact_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="担当者が見つかりません")
    return await _compose_response(db, dict(row))


@router.post(
    "/contacts",
    response_model=ContactResponse,
    status_code=201,
    dependencies=[Depends(require_permission("customers.create"))],
)
async def create_contact(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """担当者を登録。company_id の会社は同テナントである必要がある（RLS で自動保証）。"""
    # 会社存在確認
    company_exists = await db.execute(
        text("SELECT 1 FROM companies WHERE id = :id"),
        {"id": data.company_id},
    )
    if company_exists.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定の会社が見つかりません")

    try:
        explicit_code = data.contact_code and data.contact_code.strip()
        # CT-PEND-<8hex> = 最大 16 文字 (VARCHAR(20) に収まる)。
        # companies.py と同じパターンで、StringDataRightTruncationError 500 を回避。
        contact_code = explicit_code if explicit_code else f"CT-PEND-{uuid.uuid4().hex[:8]}"

        # is_primary_contact=TRUE 指定なら既存の primary をクリア
        if data.is_primary_contact:
            await _clear_primary_contact_flag(db, data.company_id)

        result = await db.execute(
            text("""
                INSERT INTO contacts (
                    tenant_id, company_id, contact_code, lead_id,
                    surname, given_name, display_name, job_title, department,
                    is_primary_contact, primary_email, primary_phone,
                    status, notes
                ) VALUES (
                    :tenant_id, :company_id, :contact_code, :lead_id,
                    :surname, :given_name, :display_name, :job_title, :department,
                    :is_primary_contact, :primary_email, :primary_phone,
                    :status, :notes
                )
                RETURNING id
            """),
            {
                "tenant_id": tenant_id,
                "company_id": data.company_id,
                "contact_code": contact_code,
                "lead_id": data.lead_id,
                "surname": data.surname,
                "given_name": data.given_name,
                "display_name": data.display_name,
                "job_title": data.job_title,
                "department": data.department,
                "is_primary_contact": data.is_primary_contact,
                "primary_email": data.primary_email,
                "primary_phone": data.primary_phone,
                "status": data.status.value,
                "notes": data.notes,
            },
        )
        new_id = result.scalar_one()

        if not explicit_code:
            await db.execute(
                text("UPDATE contacts SET contact_code = :code WHERE id = :id"),
                {"code": f"CT-{new_id:05d}", "id": new_id},
            )

        # 順序重要: _replace_contact_channels は冒頭で DELETE するため、
        # _upsert_discord の 'discord' 自動追加より前に呼ぶ必要がある。
        # さもないと Discord 自動追加が即座に消える（PR #121 Critical 1）。
        await _replace_emails(db, new_id, data.emails)
        await _replace_contact_channels(db, new_id, data.contact_channels)
        await _upsert_discord(db, new_id, data.discord)

        fetched = await db.execute(
            text(f"SELECT {_CONTACT_COLUMNS} FROM contacts WHERE id = :id"),
            {"id": new_id},
        )
        row = fetched.mappings().first()

        # PR #145 F9: 副テーブルの初期状態を _subtables.* にスナップショット
        new_subs_snapshot = await _snapshot_contact_subtables(db, new_id)
        new_data_payload: dict = data.model_dump(exclude_none=True, mode="json")
        sub_diff = build_subtable_diff(
            {"contact_emails": [], "contact_discord": None, "contact_contact_channels": []},
            new_subs_snapshot,
        )
        if sub_diff:
            new_data_payload["_subtables"] = sub_diff

        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="create", table_name="contacts", record_id=new_id,
            new_data=new_data_payload,
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    except IntegrityError as e:
        await db.rollback()
        logger.warning("create_contact IntegrityError: tenant=%d, err=%s", tenant_id, e.orig)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="担当者の登録に失敗しました（contact_code 重複または制約違反の可能性）",
        )
    await invalidate_dashboard_cache(tenant_id)
    return await _compose_response(db, dict(row))


@router.patch(
    "/contacts/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("customers.update"))],
)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    old_result = await db.execute(
        text(f"SELECT {_CONTACT_COLUMNS} FROM contacts WHERE id = :id"),
        {"id": contact_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="担当者が見つかりません")

    # PR #145 F9: 副テーブルの old スナップショットを _replace_* 前に取得
    old_subs_snapshot = await _snapshot_contact_subtables(db, contact_id)

    update_data = data.model_dump(exclude_unset=True, mode="python")
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新するフィールドを少なくとも1つ指定してください",
        )
    emails = update_data.pop("emails", None)
    discord = update_data.pop("discord", None)
    contact_channels = update_data.pop("contact_channels", None)

    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
    for k, v in list(update_data.items()):
        if hasattr(v, "value"):
            update_data[k] = v.value

    # is_primary_contact=TRUE に切替時は既存 primary をクリア（部分UNIQUE INDEX 対応）
    if update_data.get("is_primary_contact") is True:
        company_id_for_primary = update_data.get("company_id")
        if company_id_for_primary is None:
            company_id_for_primary = old_row["company_id"]
        await _clear_primary_contact_flag(db, company_id_for_primary, keep_contact_id=contact_id)

    if update_data:
        set_sql = ", ".join(f"{k} = :{k}" for k in update_data)
        params = {**update_data, "id": contact_id}
        await db.execute(
            text(f"UPDATE contacts SET {set_sql}, updated_at = NOW() WHERE id = :id"),
            params,
        )

    # 順序重要: contact_channels 置換 → discord upsert（Discord 自動追加が消えないように）
    if emails is not None:
        em_models = [ContactEmailInput(**e) for e in emails]
        await _replace_emails(db, contact_id, em_models)
    if contact_channels is not None:
        ch_models = [ContactChannelInput(**c) for c in contact_channels]
        await _replace_contact_channels(db, contact_id, ch_models)
    if "discord" in data.model_fields_set:
        discord_model = ContactDiscordInput(**discord) if discord else None
        await _upsert_discord(db, contact_id, discord_model)

    # PR #145 F9: 副テーブル変更後の new スナップショットと old から diff を組み立てる。
    # 変更されていない副テーブルは old/new 同一で diff_* が None を返すため _subtables から省かれる。
    new_subs_snapshot = await _snapshot_contact_subtables(db, contact_id)
    sub_diff = build_subtable_diff(old_subs_snapshot, new_subs_snapshot)

    new_data_payload: dict = data.model_dump(exclude_unset=True, mode="json")
    if sub_diff:
        new_data_payload["_subtables"] = sub_diff

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="contacts", record_id=contact_id,
        old_data=dict(old_row), new_data=new_data_payload,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)

    fetched = await db.execute(
        text(f"SELECT {_CONTACT_COLUMNS} FROM contacts WHERE id = :id"),
        {"id": contact_id},
    )
    row = fetched.mappings().first()
    return await _compose_response(db, dict(row))


@router.delete(
    "/contacts/{contact_id}",
    status_code=204,
    dependencies=[Depends(require_permission("customers.delete"))],
)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """担当者を削除する（副テーブルは ON DELETE CASCADE で自動削除）"""
    old_result = await db.execute(
        text(f"SELECT {_CONTACT_COLUMNS} FROM contacts WHERE id = :id"),
        {"id": contact_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="担当者が見つかりません")

    # PR #145 F9: 副テーブルも CASCADE で消える前にスナップショットを取って old_data に含める
    old_subs_snapshot = await _snapshot_contact_subtables(db, contact_id)
    sub_diff = build_subtable_diff(
        old_subs_snapshot,
        {"contact_emails": [], "contact_discord": None, "contact_contact_channels": []},
    )
    old_data_payload: dict = dict(old_row)
    if sub_diff:
        old_data_payload["_subtables"] = sub_diff

    try:
        await db.execute(text("DELETE FROM contacts WHERE id = :id"), {"id": contact_id})
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="delete", table_name="contacts", record_id=contact_id,
            old_data=old_data_payload,
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この担当者には関連する商談・注文・見積・請求書があるため削除できません。先に関連データを削除してください。",
        )
    await invalidate_dashboard_cache(tenant_id)


@router.post(
    "/contacts/{contact_id}/channel-acknowledge-duplicate",
    status_code=204,
    dependencies=[Depends(require_permission("customers.edit"))],
    summary="重複IDを認識した上で別人として保存した旨を監査ログに記録",
    tags=["contacts"],
)
async def acknowledge_channel_duplicate(
    contact_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """保存前の重複チェックで他担当者とIDが一致したが、別人として保存することを
    操作者が明示的に選択したときの監査ログエントリを記録する。

    Body: { channel, purpose, duplicate_contact_id }
    """
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="channel_duplicate_acknowledged",
        table_name="contacts",
        record_id=contact_id,
        old_data=None,
        new_data={
            "channel": body.get("channel"),
            "purpose": body.get("purpose"),
            "duplicate_contact_id": body.get("duplicate_contact_id"),
            "decision": "save_as_distinct",
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)


@router.post(
    "/contacts/{master_id}/merge",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("customers.delete"))],
    summary="担当者を統合（loser → master）",
    tags=["contacts"],
)
async def merge_contacts(
    master_id: int,
    body: ContactMergeRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """担当者の重複統合（ADR-098 SA-04 J3）。

    loser の deals / orders / quotes / invoices の contact_id を master へ付け替え、
    contact_contact_channels も master へ再ポイントし、loser を削除する。

    guard（v1）:
        loser に deals / orders / quotes / invoices が紐づいている場合は 400 ブロック。

    処理順序（同一トランザクション・FOR UPDATE ロック）:
      1. master / loser を FOR UPDATE ロック（昇順 ID・デッドロック防止）
      2. guard: loser が deals / orders / quotes / invoices を持つ → 400
      3. FK 付け替え: deals / orders / quotes / invoices の contact_id → master
      4. contact_contact_channels を master へ再ポイント（重複行は先削除して吸収）
      5. loser 削除
      6. 監査ログ 2 件
    """
    loser_id = body.loser_id

    if master_id == loser_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="master_id と loser_id が同じです。自己マージはできません。",
        )

    ct_t = tenant_table_ref(db, tenant_id, "contacts")
    ccc_t = tenant_table_ref(db, tenant_id, "contact_contact_channels")
    dl_t = tenant_table_ref(db, tenant_id, "deals")
    ord_t = tenant_table_ref(db, tenant_id, "orders")
    qt_t = tenant_table_ref(db, tenant_id, "quotes")
    inv_t = tenant_table_ref(db, tenant_id, "invoices")

    # 1) master / loser を昇順 FOR UPDATE ロック（デッドロック防止）
    low_id, high_id = min(master_id, loser_id), max(master_id, loser_id)
    locked_res = await db.execute(
        text(f"""
            SELECT {_CONTACT_COLUMNS}
            FROM {ct_t}
            WHERE id IN (:id1, :id2)
            ORDER BY id
            FOR UPDATE
        """),
        {"id1": low_id, "id2": high_id},
    )
    locked_rows = locked_res.mappings().all()
    rows_by_id = {r["id"]: r for r in locked_rows}
    master_row = rows_by_id.get(master_id)
    loser_row = rows_by_id.get(loser_id)

    if not master_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"master 担当者 (id={master_id}) が見つかりません",
        )
    if not loser_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"loser 担当者 (id={loser_id}) が見つかりません",
        )

    # 2) guard: loser が関連レコードを持つ場合は 400
    related_counts: dict[str, int] = {}
    for tbl, label in (
        (dl_t, "deals"),
        (ord_t, "orders"),
        (qt_t, "quotes"),
        (inv_t, "invoices"),
    ):
        cnt_res = await db.execute(
            text(f"SELECT COUNT(*) FROM {tbl} WHERE contact_id = :loser"),
            {"loser": loser_id},
        )
        cnt = cnt_res.scalar() or 0
        if cnt:
            related_counts[label] = cnt

    if related_counts:
        detail_parts = ", ".join(f"{label}: {cnt}件" for label, cnt in related_counts.items())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"loser 担当者 (id={loser_id}) には関連レコードがあるため loser にできません。"
                f"（{detail_parts}）先に担当者を変更してください。"
            ),
        )

    # 3) FK 付け替え: deals / orders / quotes / invoices
    reassigned_deals = (await db.execute(
        text(f"UPDATE {dl_t} SET contact_id = :master WHERE contact_id = :loser"),
        {"master": master_id, "loser": loser_id},
    )).rowcount or 0

    reassigned_orders = (await db.execute(
        text(f"UPDATE {ord_t} SET contact_id = :master WHERE contact_id = :loser"),
        {"master": master_id, "loser": loser_id},
    )).rowcount or 0

    reassigned_quotes = (await db.execute(
        text(f"UPDATE {qt_t} SET contact_id = :master WHERE contact_id = :loser"),
        {"master": master_id, "loser": loser_id},
    )).rowcount or 0

    reassigned_invoices = (await db.execute(
        text(f"UPDATE {inv_t} SET contact_id = :master WHERE contact_id = :loser"),
        {"master": master_id, "loser": loser_id},
    )).rowcount or 0

    # 4) contact_contact_channels を master へ再ポイント
    #    UNIQUE(contact_id, channel, COALESCE(purpose,'')) 制約があるため、
    #    master 側に同一チャンネルが既にあれば先に loser 側を削除する。
    dup_ccc_res = await db.execute(
        text(f"""
            SELECT ccc_loser.id
            FROM {ccc_t} ccc_loser
            WHERE ccc_loser.contact_id = :loser
              AND EXISTS (
                  SELECT 1 FROM {ccc_t} ccc_master
                  WHERE ccc_master.contact_id = :master
                    AND ccc_master.channel = ccc_loser.channel
                    AND COALESCE(ccc_master.purpose, '') = COALESCE(ccc_loser.purpose, '')
              )
        """),
        {"loser": loser_id, "master": master_id},
    )
    dup_ccc_ids = [r[0] for r in dup_ccc_res.fetchall()]
    if dup_ccc_ids:
        await db.execute(
            text(f"DELETE FROM {ccc_t} WHERE id = ANY(:ids)"),
            {"ids": dup_ccc_ids},
        )

    reassigned_channels = (await db.execute(
        text(f"UPDATE {ccc_t} SET contact_id = :master WHERE contact_id = :loser"),
        {"master": master_id, "loser": loser_id},
    )).rowcount or 0

    # 5) loser 削除（副テーブルは ON DELETE CASCADE で自動削除）
    await db.execute(
        text(f"DELETE FROM {ct_t} WHERE id = :loser"),
        {"loser": loser_id},
    )

    # master の最新状態を取得
    updated_res = await db.execute(
        text(f"SELECT {_CONTACT_COLUMNS} FROM {ct_t} WHERE id = :id"),
        {"id": master_id},
    )
    master_updated = updated_res.mappings().first()

    # 6) 監査ログ 2 件
    loser_name = (
        loser_row.get("display_name")
        or f"{loser_row.get('surname', '')} {loser_row.get('given_name', '')}".strip()
    )
    merge_summary = {
        "loser_id": loser_id,
        "loser_display_name": loser_name,
        "reassigned_deals": reassigned_deals,
        "reassigned_orders": reassigned_orders,
        "reassigned_quotes": reassigned_quotes,
        "reassigned_invoices": reassigned_invoices,
        "reassigned_channels": reassigned_channels,
        "reason": body.reason,
    }
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="merge_absorb", table_name="contacts", record_id=master_id,
        old_data=dict(master_row),
        new_data=merge_summary,
    )
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="merge_delete", table_name="contacts", record_id=loser_id,
        old_data=dict(loser_row),
        new_data={"merged_into": master_id, "reason": body.reason},
    )

    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    await invalidate_dashboard_cache(tenant_id)

    logger.info(
        "[merge_contacts] tenant=%d master=%d ← loser=%d "
        "(deals=%d orders=%d quotes=%d invoices=%d channels=%d)",
        tenant_id, master_id, loser_id,
        reassigned_deals, reassigned_orders, reassigned_quotes,
        reassigned_invoices, reassigned_channels,
    )

    return await _compose_response(db, dict(master_updated))
