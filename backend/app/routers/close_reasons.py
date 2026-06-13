from __future__ import annotations

"""
成約・失注理由マスタ API（close_reasons）。

ADR-138 §D1-2 / PR3（入力動線）
テナントスキーマの close_reasons テーブルに対するマスタ CRUD を提供する。

変更履歴:
  2026-06-13: 初版作成
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
from app.database import get_db
from app.schemas.close_reason import CloseReasonCreate, CloseReasonResponse, CloseReasonUpdate

router = APIRouter()


@router.get(
    "/close-reasons",
    response_model=list[CloseReasonResponse],
    dependencies=[Depends(require_permission("deals.view"))],
)
async def list_close_reasons(
    type: str | None = Query(default=None, description="'won' または 'lost' でフィルタ"),
    include_inactive: bool = Query(default=False, description="非アクティブも含む"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """成約・失注理由マスタ一覧を返す（sort_order 昇順）"""
    close_reasons_t = tenant_table_ref(db, tenant_id, "close_reasons")

    conditions = []
    params: dict = {}

    if type is not None:
        if type not in ("won", "lost"):
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="type は 'won' または 'lost' のみ有効です",
            )
        conditions.append("type = :type")
        params["type"] = type

    if not include_inactive:
        conditions.append("is_active = true")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    result = await db.execute(
        text(f"SELECT id, type, label, sort_order, is_active, created_at FROM {close_reasons_t} {where_clause} ORDER BY sort_order ASC, id ASC"),
        params,
    )
    rows = result.mappings().all()
    return [CloseReasonResponse(**r) for r in rows]


@router.post(
    "/close-reasons",
    response_model=CloseReasonResponse,
    status_code=201,
    dependencies=[Depends(require_permission("deals.update"))],
)
async def create_close_reason(
    data: CloseReasonCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """成約・失注理由マスタに新規理由を追加する"""
    close_reasons_t = tenant_table_ref(db, tenant_id, "close_reasons")

    result = await db.execute(
        text(f"""
            INSERT INTO {close_reasons_t} (type, label, sort_order)
            VALUES (:type, :label, :sort_order)
            RETURNING id, type, label, sort_order, is_active, created_at
        """),
        {"type": data.type, "label": data.label, "sort_order": data.sort_order},
    )
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return CloseReasonResponse(**row)


@router.patch(
    "/close-reasons/{reason_id}",
    response_model=CloseReasonResponse,
    dependencies=[Depends(require_permission("deals.update"))],
)
async def update_close_reason(
    reason_id: int,
    data: CloseReasonUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """成約・失注理由マスタを更新する（ラベル・表示順・アクティブ状態）"""
    close_reasons_t = tenant_table_ref(db, tenant_id, "close_reasons")

    existing = await db.execute(
        text(f"SELECT id FROM {close_reasons_t} WHERE id = :id"),
        {"id": reason_id},
    )
    if not existing.first():
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="指定された理由が見つかりません",
        )

    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="更新するフィールドを指定してください",
        )

    set_clause = ", ".join(f"{k} = :{k}" for k in update_fields)
    update_fields["id"] = reason_id

    result = await db.execute(
        text(f"""
            UPDATE {close_reasons_t}
            SET {set_clause}
            WHERE id = :id
            RETURNING id, type, label, sort_order, is_active, created_at
        """),
        update_fields,
    )
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return CloseReasonResponse(**row)
