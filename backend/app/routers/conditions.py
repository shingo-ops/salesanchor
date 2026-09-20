"""
テナント用状態マスタAPI（CRUD）。

テーブル: public.conditions
  id, code, canonical, app_kubun, is_active, priority,
  search_kw, exclude_kw, tenant_id, created_at, updated_at

変更履歴:
  2026-09-20: 初版作成（conditions_master tenant_id Phase 1）
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
)
from app.database import get_db
from app.models import User
from app.schemas.condition import (
    ConditionAliasCreate,
    ConditionAliasResponse,
    ConditionCreate,
    ConditionResponse,
    ConditionUpdate,
)
from app.services.audit import record_audit_log

router = APIRouter()

_ALIAS_COLS = "id, condition_id, alias_text, lang, updated_at"

_COLS = (
    "id, code, canonical, app_kubun, is_active, priority, "
    "search_kw, exclude_kw, tenant_id, created_at, updated_at"
)
_UPDATABLE = {"code", "canonical", "app_kubun", "is_active", "priority", "search_kw", "exclude_kw"}


@router.get(
    "/conditions",
    response_model=list[ConditionResponse],
    dependencies=[Depends(require_permission("conditions.view"))],
)
async def list_conditions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    active_only: bool = Query(default=True),
    q: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": per_page, "offset": offset}
    if active_only:
        conditions.append("is_active = TRUE")
    if q:
        conditions.append("(code ILIKE :q OR canonical ILIKE :q)")
        params["q"] = f"%{q}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM public.conditions {where} "
            "ORDER BY priority NULLS LAST, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [ConditionResponse(**dict(row)) for row in result.mappings().all()]


@router.get(
    "/conditions/catalog",
    response_model=list[ConditionResponse],
    dependencies=[Depends(require_permission("work_items.view"))],
)
async def list_condition_catalog(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """全テナント共有の中央カタログ（tenant_id IS NULL）を返す。
    作業アイテム用状態プルダウン等で使用する。
    """
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM public.conditions "
            "WHERE tenant_id IS NULL AND is_active = TRUE "
            "ORDER BY priority NULLS LAST, id"
        )
    )
    return [ConditionResponse(**dict(row)) for row in result.mappings().all()]


@router.get(
    "/conditions/{condition_id}",
    response_model=ConditionResponse,
    dependencies=[Depends(require_permission("conditions.view"))],
)
async def get_condition(
    condition_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(f"SELECT {_COLS} FROM public.conditions WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": condition_id, "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="状態が見つかりません"
        )
    return ConditionResponse(**dict(row))


@router.post(
    "/conditions",
    response_model=ConditionResponse,
    status_code=201,
    dependencies=[Depends(require_permission("conditions.create"))],
)
async def create_condition(
    data: ConditionCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    # code 重複チェック（テナント内）
    exists = await db.execute(
        text(
            "SELECT 1 FROM public.conditions WHERE code = :code AND tenant_id = :tenant_id"
        ),
        {"code": data.code, "tenant_id": tenant_id},
    )
    if exists.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この状態コードは既に存在します",
        )
    result = await db.execute(
        text(
            f"INSERT INTO public.conditions "
            f"(tenant_id, code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, updated_at) "
            f"VALUES (:tenant_id, :code, :canonical, :app_kubun, :is_active, :priority, :search_kw, :exclude_kw, now()) "
            f"RETURNING {_COLS}"
        ),
        {
            "tenant_id": tenant_id,
            "code": data.code,
            "canonical": data.canonical,
            "app_kubun": data.app_kubun,
            "is_active": data.is_active,
            "priority": data.priority,
            "search_kw": data.search_kw,
            "exclude_kw": data.exclude_kw,
        },
    )
    row = result.mappings().first()
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="create",
        table_name="conditions",
        record_id=row["id"],
        new_data=data.model_dump(exclude_none=True),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return ConditionResponse(**dict(row))


@router.patch(
    "/conditions/{condition_id}",
    response_model=ConditionResponse,
    dependencies=[Depends(require_permission("conditions.update"))],
)
async def update_condition(
    condition_id: int,
    data: ConditionUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    old = await db.execute(
        text(f"SELECT {_COLS} FROM public.conditions WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": condition_id, "tenant_id": tenant_id},
    )
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="状態が見つかりません"
        )
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください"
        )
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = condition_id
    update_data["tenant_id"] = tenant_id
    result = await db.execute(
        text(
            f"UPDATE public.conditions SET {set_clauses}, updated_at = now() "
            f"WHERE id = :id AND tenant_id = :tenant_id "
            f"RETURNING {_COLS}"
        ),
        update_data,
    )
    row = result.mappings().first()
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="update",
        table_name="conditions",
        record_id=condition_id,
        old_data=dict(old_row),
        new_data=update_data,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return ConditionResponse(**dict(row))


@router.delete(
    "/conditions/{condition_id}",
    status_code=204,
    dependencies=[Depends(require_permission("conditions.delete"))],
)
async def delete_condition(
    condition_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    old = await db.execute(
        text(f"SELECT {_COLS} FROM public.conditions WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": condition_id, "tenant_id": tenant_id},
    )
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="状態が見つかりません"
        )
    await db.execute(
        text(
            "UPDATE public.conditions SET is_active = FALSE, updated_at = now() "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": condition_id, "tenant_id": tenant_id},
    )
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="soft_delete",
        table_name="conditions",
        record_id=condition_id,
        old_data=dict(old_row),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072


# ----------------------------------------------------------------------------
# condition_aliases (tenant-scoped via parent condition)
# ----------------------------------------------------------------------------


@router.get(
    "/conditions/{condition_id}/aliases",
    response_model=list[ConditionAliasResponse],
    dependencies=[Depends(require_permission("conditions.view"))],
)
async def list_condition_aliases(
    condition_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    # 親 condition がこのテナントのものであることを確認
    parent = await db.execute(
        text("SELECT 1 FROM public.conditions WHERE id = :id AND tenant_id = :tid"),
        {"id": condition_id, "tid": tenant_id},
    )
    if not parent.fetchone():
        raise HTTPException(status_code=404, detail="状態が見つかりません")
    result = await db.execute(
        text(
            f"SELECT {_ALIAS_COLS} FROM public.condition_aliases "
            "WHERE condition_id = :cid ORDER BY id"
        ),
        {"cid": condition_id},
    )
    return [ConditionAliasResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/conditions/{condition_id}/aliases",
    response_model=ConditionAliasResponse,
    status_code=201,
    dependencies=[Depends(require_permission("conditions.update"))],
)
async def create_condition_alias(
    condition_id: int,
    data: ConditionAliasCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    if data.condition_id != condition_id:
        raise HTTPException(
            status_code=400,
            detail="URL の condition_id と body の condition_id が一致しません",
        )
    # 親 condition の所有確認
    parent = await db.execute(
        text("SELECT 1 FROM public.conditions WHERE id = :id AND tenant_id = :tid"),
        {"id": condition_id, "tid": tenant_id},
    )
    if not parent.fetchone():
        raise HTTPException(status_code=404, detail="状態が見つかりません")
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.condition_aliases "
                f"(condition_id, alias_text, lang) "
                f"VALUES (:condition_id, :alias_text, :lang) "
                f"RETURNING {_ALIAS_COLS}"
            ),
            data.model_dump(),
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"重複または FK 違反: {exc.orig}")
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return ConditionAliasResponse(**dict(row))


@router.delete(
    "/conditions/aliases/{alias_id}",
    status_code=204,
    dependencies=[Depends(require_permission("conditions.delete"))],
)
async def delete_condition_alias(
    alias_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    # テナントの condition_aliases のみ削除可（JOIN で所有確認）
    result = await db.execute(
        text(
            "DELETE FROM public.condition_aliases ca "
            "USING public.conditions c "
            "WHERE ca.id = :id AND ca.condition_id = c.id AND c.tenant_id = :tid"
        ),
        {"id": alias_id, "tid": tenant_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="別名が見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
