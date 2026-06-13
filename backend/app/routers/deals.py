from __future__ import annotations

"""
案件管理API（CRUD）。

テナントスキーマの deals テーブルに対する操作を提供する。

変更履歴:
  2026-04-16: Phase 1拡張（deal_code, lead_id, stage, probability,
    currency, assigned_to, lost_reason 追加、require_permission統合）
  2026-04-27: Phase 1-B-2 Step 5d — 旧 customer_id 系統撤去
    （resolver / customer 経路廃止、company_id + contact_id を唯一の正に）
  2026-06-04: C-1 — lost_reason_code（選択式失注理由）追加
"""

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
from app.schemas.deal import DealCreate, DealResponse, DealUpdate
from app.services.audit import record_audit_log

router = APIRouter()

# ADR-072 Phase 1: ローカル helper を削除し、`tenant_table_ref` を import 使用。


_DEAL_COLUMNS = """
    id, deal_code, company_id, contact_id, lead_id,
    title, amount, currency,
    status, stage, probability, assigned_to,
    expected_close_date, notes, lead_source,
    closed_at, close_reason_memo, created_at, updated_at
"""

_UPDATABLE_COLUMNS = {
    "company_id", "contact_id", "lead_id",
    "title", "amount", "currency",
    "status", "stage", "probability",
    "assigned_to", "expected_close_date", "notes", "lead_source",
    "close_reason_memo",
}

_WON_LOST_STATUSES = {"won", "lost"}


@router.get(
    "/deals",
    response_model=list[DealResponse],
    dependencies=[Depends(require_permission("deals.view"))],
)
async def list_deals(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    stage: str | None = Query(default=None),
    company_id: int | None = Query(default=None),
    contact_id: int | None = Query(default=None),
    assigned_to: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """商談一覧を取得する"""
    offset = (page - 1) * per_page
    conditions = []
    params: dict = {"limit": per_page, "offset": offset}

    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter
    if stage:
        conditions.append("stage = :stage")
        params["stage"] = stage
    if company_id:
        conditions.append("company_id = :company_id")
        params["company_id"] = company_id
    if contact_id:
        conditions.append("contact_id = :contact_id")
        params["contact_id"] = contact_id
    if assigned_to:
        conditions.append("assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    deals_t = tenant_table_ref(db, tenant_id, "deals")
    result = await db.execute(
        text(f"""
            SELECT {_DEAL_COLUMNS}
            FROM {deals_t}
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.mappings().all()
    return [DealResponse(**row) for row in rows]


@router.get(
    "/deals/{deal_id}",
    response_model=DealResponse,
    dependencies=[Depends(require_permission("deals.view"))],
)
async def get_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """商談詳細を取得する"""
    deals_t = tenant_table_ref(db, tenant_id, "deals")
    result = await db.execute(
        text(f"SELECT {_DEAL_COLUMNS} FROM {deals_t} WHERE id = :id"),
        {"id": deal_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商談が見つかりません")
    return DealResponse(**row)


@router.post(
    "/deals",
    response_model=DealResponse,
    status_code=201,
    dependencies=[Depends(require_permission("deals.create"))],
)
async def create_deal(
    data: DealCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """商談を登録する（deal_codeは自動採番）"""
    deals_t = tenant_table_ref(db, tenant_id, "deals")
    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
    leads_t = tenant_table_ref(db, tenant_id, "leads")
    # Step 5d: contact / company の存在 + 所属一致確認のみ
    contact_check = await db.execute(
        text(f"SELECT company_id FROM {contacts_t} WHERE id = :id"),
        {"id": data.contact_id},
    )
    contact_row = contact_check.first()
    if not contact_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された担当者が見つかりません")
    if contact_row[0] != data.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定された担当者は指定会社に所属していません",
        )

    # リード存在確認（指定時のみ）
    if data.lead_id is not None:
        lead_check = await db.execute(text(f"SELECT id FROM {leads_t} WHERE id = :id"), {"id": data.lead_id})
        if not lead_check.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定されたリードが見つかりません")

    result = await db.execute(
        text(f"""
            INSERT INTO {deals_t} (
                tenant_id, company_id, contact_id, lead_id,
                title, amount, currency,
                status, stage, probability,
                assigned_to, expected_close_date, notes, lead_source
            )
            VALUES (
                :tenant_id, :company_id, :contact_id, :lead_id,
                :title, :amount, :currency,
                :status, :stage, :probability,
                :assigned_to, :expected_close_date, :notes, :lead_source
            )
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "company_id": data.company_id,
            "contact_id": data.contact_id,
            "lead_id": data.lead_id,
            "title": data.title,
            "amount": data.amount,
            "currency": data.currency.value,
            "status": data.status.value,
            "stage": data.stage.value,
            "probability": data.probability,
            "assigned_to": data.assigned_to,
            "expected_close_date": data.expected_close_date,
            "notes": data.notes,
            "lead_source": data.lead_source,
        },
    )
    new_id = result.scalar_one()

    # deal_code = DL-00001 形式で自動採番（Python側で生成してDB非依存）
    await db.execute(
        text(f"UPDATE {deals_t} SET deal_code = :code WHERE id = :id"),
        {"code": f"DL-{new_id:05d}", "id": new_id},
    )

    fetched = await db.execute(
        text(f"SELECT {_DEAL_COLUMNS} FROM {deals_t} WHERE id = :id"),
        {"id": new_id},
    )
    row = fetched.mappings().first()

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create", table_name="deals", record_id=new_id,
        new_data=data.model_dump(exclude_none=True, mode="json"),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    await invalidate_dashboard_cache(tenant_id)

    return DealResponse(**row)


@router.patch(
    "/deals/{deal_id}",
    response_model=DealResponse,
    dependencies=[Depends(require_permission("deals.update"))],
)
async def update_deal(
    deal_id: int,
    data: DealUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """商談情報を更新する（部分更新）"""
    deals_t = tenant_table_ref(db, tenant_id, "deals")
    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
    companies_t = tenant_table_ref(db, tenant_id, "companies")
    leads_t = tenant_table_ref(db, tenant_id, "leads")
    old_result = await db.execute(
        text(f"SELECT {_DEAL_COLUMNS} FROM {deals_t} WHERE id = :id"),
        {"id": deal_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商談が見つかりません")

    raw_update = data.model_dump(exclude_unset=True)
    close_reasons_input = raw_update.pop("close_reasons", None)
    update_data = {k: v for k, v in raw_update.items() if k in _UPDATABLE_COLUMNS}
    if not update_data and close_reasons_input is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")

    # won/lost 遷移の検出と closed_at 自動セット
    new_status_raw = update_data.get("status")
    new_status = new_status_raw.value if new_status_raw is not None else None
    old_status = old_row["status"]
    is_closing = new_status in _WON_LOST_STATUSES and old_status not in _WON_LOST_STATUSES

    if is_closing:
        # closed_at を自動セット
        update_data["closed_at_now"] = True  # UPDATE 句で NOW() を埋め込む（後で処理）
        # close_reasons 必須チェック
        if not close_reasons_input:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="成約/失注遷移時は close_reasons（主因1件必須）が必要です",
            )
        primary_count = sum(1 for r in close_reasons_input if r.get("is_primary"))
        if primary_count != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"主因（is_primary: true）はちょうど1件必要です（{primary_count}件指定）",
            )
        # close_reason_memo 必須チェック
        if not update_data.get("close_reason_memo"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="成約/失注遷移時は close_reason_memo が必要です",
            )

    # company_id / contact_id の整合性検証（Step 5d 以降）
    has_company_update = "company_id" in raw_update
    has_contact_update = "contact_id" in raw_update

    if has_company_update or has_contact_update:
        target_company_id = raw_update["company_id"] if has_company_update else old_row["company_id"]
        target_contact_id = raw_update["contact_id"] if has_contact_update else old_row["contact_id"]

        if target_contact_id is not None:
            contact_check = await db.execute(
                text(f"SELECT company_id FROM {contacts_t} WHERE id = :id"),
                {"id": target_contact_id},
            )
            contact_row = contact_check.first()
            if not contact_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定された担当者が見つかりません",
                )
            if target_company_id is not None and contact_row[0] != target_company_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定された担当者は指定会社に所属していません",
                )
            # company_id を明示更新せず contact のみ更新 → contact 側の company_id を採用
            if target_company_id is None and contact_row[0] is not None:
                update_data["company_id"] = contact_row[0]

        elif target_company_id is not None and has_company_update:
            company_check = await db.execute(
                text(f"SELECT id FROM {companies_t} WHERE id = :id"),
                {"id": target_company_id},
            )
            if not company_check.first():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定された会社が見つかりません",
                )

    # lead_id を更新する場合は存在確認（指定された場合のみ、NULL クリアは許容）
    if "lead_id" in raw_update and raw_update["lead_id"] is not None:
        lead_check = await db.execute(
            text(f"SELECT id FROM {leads_t} WHERE id = :id"),
            {"id": raw_update["lead_id"]},
        )
        if not lead_check.first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたリードが見つかりません",
            )

    # Enum型の値を文字列に変換
    for key in ("status", "stage", "currency"):
        if key in update_data and update_data[key] is not None:
            update_data[key] = update_data[key].value

    # closed_at_now フラグを SET 句に変換
    use_closed_at_now = update_data.pop("closed_at_now", False)
    set_clauses_parts = [f"{k} = :{k}" for k in update_data]
    if use_closed_at_now:
        set_clauses_parts.append("closed_at = NOW()")
    set_clauses_parts.append("updated_at = NOW()")
    set_clauses = ", ".join(set_clauses_parts)
    update_data["id"] = deal_id

    result = await db.execute(
        text(f"""
            UPDATE {deals_t} SET {set_clauses}
            WHERE id = :id
            RETURNING {_DEAL_COLUMNS}
        """),
        update_data,
    )
    row = result.mappings().first()

    # close_reasons 登録（won/lost 遷移時）
    if close_reasons_input and is_closing:
        close_reasons_t = tenant_table_ref(db, tenant_id, "close_reasons")
        deal_close_reasons_t = tenant_table_ref(db, tenant_id, "deal_close_reasons")
        # 既存の理由をクリア（再遷移の場合でも冪等に）
        await db.execute(
            text(f"DELETE FROM {deal_close_reasons_t} WHERE deal_id = :did"),
            {"did": deal_id},
        )
        for reason in close_reasons_input:
            # reason_id の存在確認
            reason_check = await db.execute(
                text(f"SELECT id FROM {close_reasons_t} WHERE id = :rid AND is_active = true"),
                {"rid": reason["reason_id"]},
            )
            if not reason_check.first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"close_reason id={reason['reason_id']} が見つかりません",
                )
            await db.execute(
                text(f"""
                    INSERT INTO {deal_close_reasons_t} (deal_id, reason_id, is_primary)
                    VALUES (:did, :rid, :is_primary)
                    ON CONFLICT (deal_id, reason_id) DO UPDATE SET is_primary = EXCLUDED.is_primary
                """),
                {"did": deal_id, "rid": reason["reason_id"], "is_primary": reason["is_primary"]},
            )

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="deals", record_id=deal_id,
        old_data=dict(old_row), new_data=update_data,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    await invalidate_dashboard_cache(tenant_id)

    return DealResponse(**row)


@router.delete(
    "/deals/{deal_id}",
    status_code=204,
    dependencies=[Depends(require_permission("deals.delete"))],
)
async def delete_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """商談を削除する"""
    deals_t = tenant_table_ref(db, tenant_id, "deals")
    old_result = await db.execute(
        text(f"SELECT {_DEAL_COLUMNS} FROM {deals_t} WHERE id = :id"),
        {"id": deal_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商談が見つかりません")

    try:
        await db.execute(text(f"DELETE FROM {deals_t} WHERE id = :id"), {"id": deal_id})
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="delete", table_name="deals", record_id=deal_id,
            old_data=dict(old_row),
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この商談には関連する注文があるため削除できません。先に注文を削除してください。",
        )
    await invalidate_dashboard_cache(tenant_id)
