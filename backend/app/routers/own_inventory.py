from __future__ import annotations

"""
自社在庫（own_inventory）CRUD + 2段階引当 API。

ADR SA-04/05: A在庫（テナント専用スキーマ）の管理エンドポイント。
  - GET  /own-inventory          — 一覧（ページング）
  - POST /own-inventory          — 作成
  - GET  /own-inventory/{id}     — 単件取得
  - PATCH /own-inventory/{id}    — 更新（unit_price / condition / status / notes）
  - POST /own-inventory/{id}/reserve — 引当
  - POST /own-inventory/{id}/release — 引当解除
  - POST /own-inventory/{id}/ship    — 発送確定

ADR-072: db.commit() 直後に reset_tenant_context() 必須。

変更履歴:
  2026-06-04: 初版作成（SA-Foundation PR#6）
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.own_inventory import (
    OwnInventoryCreate,
    OwnInventoryResponse,
    OwnInventoryUpdate,
    QtyRequest,
)
from app.services.audit import record_audit_log
from app.services.inventory_reservation import (
    release_reservation,
    reserve_qty,
    ship_qty,
)

router = APIRouter()

_COLS = """
    id, tenant_id, product_id,
    physical_qty, reserved_qty, available_qty,
    unit_price, condition, status,
    note_ja, note_en, antique_ledger_id,
    created_at, updated_at
"""

_UPDATABLE = {"unit_price", "condition", "status", "note_ja", "note_en", "antique_ledger_id"}


@router.get(
    "/own-inventory",
    response_model=list[OwnInventoryResponse],
    dependencies=[Depends(require_permission("products.view"))],
)
async def list_own_inventory(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status", max_length=20),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> list[OwnInventoryResponse]:
    offset = (page - 1) * per_page
    params: dict = {"limit": per_page, "offset": offset, "tenant_id": tenant_id}
    conditions = ["tenant_id = :tenant_id"]
    if status_filter:
        conditions.append("status = :status_filter")
        params["status_filter"] = status_filter
    where = " AND ".join(conditions)
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM own_inventory"
            f" WHERE {where}"
            f" ORDER BY id DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [OwnInventoryResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/own-inventory",
    response_model=OwnInventoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("products.create"))],
)
async def create_own_inventory(
    data: OwnInventoryCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OwnInventoryResponse:
    if data.reserved_qty > data.physical_qty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="reserved_qty は physical_qty 以下にしてください",
        )
    result = await db.execute(
        text(
            "INSERT INTO own_inventory"
            " (tenant_id, product_id, physical_qty, reserved_qty,"
            "  unit_price, condition, status, note_ja, note_en, antique_ledger_id)"
            " VALUES (:tenant_id, :product_id, :physical_qty, :reserved_qty,"
            "         :unit_price, :condition, :status, :note_ja, :note_en, :antique_ledger_id)"
            " RETURNING id"
        ),
        {
            "tenant_id": tenant_id,
            "product_id": data.product_id,
            "physical_qty": data.physical_qty,
            "reserved_qty": data.reserved_qty,
            "unit_price": data.unit_price,
            "condition": data.condition,
            "status": data.status,
            "note_ja": data.note_ja,
            "note_en": data.note_en,
            "antique_ledger_id": data.antique_ledger_id,
        },
    )
    new_id = result.scalar_one()
    fetched = await db.execute(
        text(f"SELECT {_COLS} FROM own_inventory WHERE id = :id"),
        {"id": new_id},
    )
    row = fetched.mappings().first()
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create", table_name="own_inventory", record_id=new_id,
        new_data=data.model_dump(exclude_none=True),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return OwnInventoryResponse(**dict(row))


@router.get(
    "/own-inventory/{own_inventory_id}",
    response_model=OwnInventoryResponse,
    dependencies=[Depends(require_permission("products.view"))],
)
async def get_own_inventory(
    own_inventory_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OwnInventoryResponse:
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM own_inventory"
            " WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": own_inventory_id, "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="自社在庫が見つかりません",
        )
    return OwnInventoryResponse(**dict(row))


@router.patch(
    "/own-inventory/{own_inventory_id}",
    response_model=OwnInventoryResponse,
    dependencies=[Depends(require_permission("products.update"))],
)
async def update_own_inventory(
    own_inventory_id: int,
    data: OwnInventoryUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OwnInventoryResponse:
    old = await db.execute(
        text(
            f"SELECT {_COLS} FROM own_inventory"
            " WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": own_inventory_id, "tenant_id": tenant_id},
    )
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="自社在庫が見つかりません",
        )
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新するフィールドを指定してください",
        )
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = own_inventory_id
    update_data["tenant_id"] = tenant_id
    result = await db.execute(
        text(
            f"UPDATE own_inventory SET {set_clauses}, updated_at = NOW()"
            f" WHERE id = :id AND tenant_id = :tenant_id RETURNING {_COLS}"
        ),
        update_data,
    )
    row = result.mappings().first()
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="own_inventory", record_id=own_inventory_id,
        old_data=dict(old_row), new_data=update_data,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return OwnInventoryResponse(**dict(row))


@router.post(
    "/own-inventory/{own_inventory_id}/reserve",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("products.update"))],
)
async def reserve_own_inventory(
    own_inventory_id: int,
    body: QtyRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await reserve_qty(db, own_inventory_id, body.qty, tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="reserve", table_name="own_inventory", record_id=own_inventory_id,
        new_data={"qty": body.qty},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072


@router.post(
    "/own-inventory/{own_inventory_id}/release",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("products.update"))],
)
async def release_own_inventory(
    own_inventory_id: int,
    body: QtyRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await release_reservation(db, own_inventory_id, body.qty, tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="release_reservation", table_name="own_inventory", record_id=own_inventory_id,
        new_data={"qty": body.qty},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072


@router.post(
    "/own-inventory/{own_inventory_id}/ship",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("products.update"))],
)
async def ship_own_inventory(
    own_inventory_id: int,
    body: QtyRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await ship_qty(db, own_inventory_id, body.qty, tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="ship", table_name="own_inventory", record_id=own_inventory_id,
        new_data={"qty": body.qty},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
