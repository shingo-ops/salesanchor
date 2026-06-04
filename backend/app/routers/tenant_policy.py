from __future__ import annotations

"""
テナントポリシー設定 API (ADR-106: 標準エンジン + テナント変数の土台)。

public.tenant_settings のポリシー列を GET / PUT する。
  - GET  /admin/tenant-policy — 取得
  - PUT  /admin/tenant-policy — 更新

権限・テナント:
  - require_permission("tenant.profile.view") for GET
  - require_permission("tenant.profile.edit") for PUT
  - Depends(get_current_tenant) で tenant_id を取得

設計:
  public.tenant_settings は migration 070 で作成済み。
  ポリシー列は migration 20260604_050000 で追加。
  テナント作成時に create_tenant_schema で初期行が seed される。
"""

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.schemas.tenant_policy import TenantPolicyRead, TenantPolicyUpdate
from app.services.audit import record_audit_log

router = APIRouter()

_POLICY_COLS = (
    "inventory_agg_filter, agg_price_threshold_jpy, agg_qty_threshold, "
    "quote_validity_days, default_currency, document_language, "
    "duty_incoterms, issue_mode"
)


@router.get(
    "/admin/tenant-policy",
    response_model=TenantPolicyRead,
    dependencies=[Depends(require_permission("tenant.profile.view"))],
)
async def get_tenant_policy(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """テナントポリシー設定を取得する。

    public.tenant_settings の1行を返す。
    migration 070 + create_tenant_schema で初期行が seed されているため
    通常 404 にはならない。
    """
    row = (
        await db.execute(
            text(
                f"SELECT {_POLICY_COLS} "
                "FROM public.tenant_settings "
                "WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tenant_settings が初期化されていません (migration 070 適用要)",
        )
    return TenantPolicyRead(**dict(row))


@router.put(
    "/admin/tenant-policy",
    response_model=TenantPolicyRead,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def update_tenant_policy(
    data: TenantPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """テナントポリシー設定を更新する。

    PATCH 相当: 送信されたフィールドのみ更新する。
    ADR-072: db.commit() 直後に reset_tenant_context() を呼ぶ。
    """
    # 既存行を確認
    existing = (
        await db.execute(
            text(
                f"SELECT tenant_id, {_POLICY_COLS} "
                "FROM public.tenant_settings "
                "WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().first()

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tenant_settings が初期化されていません (migration 070 適用要)",
        )

    payload = data.model_dump(exclude_unset=True)
    if not payload:
        # 何も指定されていない場合は現状をそのまま返す
        return TenantPolicyRead(**{k: existing[k] for k in TenantPolicyRead.model_fields})

    # 動的 SET 節を組み立て
    set_clauses = []
    params: dict = {"tenant_id": tenant_id}
    for k, v in payload.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = v
    set_sql = ", ".join(set_clauses)

    await db.execute(
        text(
            f"UPDATE public.tenant_settings SET {set_sql} "
            "WHERE tenant_id = :tenant_id"
        ),
        params,
    )

    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=int(current_user.id),
        action="update",
        table_name="tenant_settings",
        record_id=tenant_id,
        old_data={k: existing[k] for k in payload},
        new_data=payload,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    # 更新後の値を返す
    updated = (
        await db.execute(
            text(
                f"SELECT {_POLICY_COLS} "
                "FROM public.tenant_settings "
                "WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().first()
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="tenant_settings の読み込みに失敗しました",
        )
    return TenantPolicyRead(**dict(updated))
