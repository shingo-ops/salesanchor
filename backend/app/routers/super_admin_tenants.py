"""
super_admin 用テナント論理削除 / 物理削除 API。

API:
  DELETE /api/v1/super-admin/tenants/{tenant_id}          — 論理削除
  DELETE /api/v1/super-admin/tenants/{tenant_id}/physical — 物理削除

設計根拠:
  - admin.router は get_current_tenant + get_current_admin がルーターレベルで付与されているため不使用
  - super_admin_dex.py 等の既存パターン（prefix="/api/v1" + EP レベルで require_super_admin）に準拠
  - reset_tenant_context() 不使用: get_current_tenant を付けない設計のため context は設定されない
  - DROP → admin_db.commit() → public.tenants DELETE の順（recon A-3 / C-9）
  - 監査ログは public.tenant_deletion_audit に保存（DROP 後も残る）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_admin_db, get_db

router = APIRouter()


class TenantDeleteRequest(BaseModel):
    confirm: str  # "DELETE:{tenant_code}" の完全一致を要求


# ── 論理削除 ──────────────────────────────────────────────────────────────
@router.delete("/super-admin/tenants/{tenant_id}")
async def delete_tenant_logical(
    tenant_id: int,
    body: TenantDeleteRequest,
    current_user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """テナントを論理削除する（is_active=False）。可逆操作。"""
    # SELECT〜UPDATE〜audit INSERT を同一トランザクション内に収める（TOCTOU 防止）
    async with db.begin():
        row = (
            await db.execute(
                text(
                    "SELECT id, tenant_code, tenant_name, is_active"
                    " FROM public.tenants WHERE id = :id"
                ),
                {"id": tenant_id},
            )
        ).mappings().one_or_none()
        if not row:
            raise HTTPException(404, "テナントが見つかりません")

        if body.confirm != f"DELETE:{row['tenant_code']}":
            raise HTTPException(
                400,
                f"confirm 文字列不一致。期待値: DELETE:{row['tenant_code']}",
            )

        if not row["is_active"]:
            raise HTTPException(400, "すでに論理削除済みです")

        await db.execute(
            text("UPDATE public.tenants SET is_active = FALSE WHERE id = :id"),
            {"id": tenant_id},
        )
        await db.execute(
            text(
                "INSERT INTO public.tenant_deletion_audit"
                "    (tenant_id, tenant_code, tenant_name, mode, status,"
                "     actor_id, actor_email, executed_at, completed_at)"
                " VALUES"
                "    (:tenant_id, :tenant_code, :tenant_name, 'logical', 'succeeded',"
                "     :actor_id, :actor_email, NOW(), NOW())"
            ),
            {
                "tenant_id": tenant_id,
                "tenant_code": row["tenant_code"],
                "tenant_name": row["tenant_name"],
                "actor_id": current_user.id,
                "actor_email": current_user.email,
            },
        )
    # get_current_tenant を使わない設計のため reset_tenant_context() 不要
    # get_db finally 句が context をクリアする

    return {"status": "ok", "tenant_id": tenant_id, "mode": "logical"}


# ── 物理削除 ──────────────────────────────────────────────────────────────
@router.delete("/super-admin/tenants/{tenant_id}/physical")
async def delete_tenant_physical(
    tenant_id: int,
    body: TenantDeleteRequest,
    current_user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    admin_db: AsyncSession = Depends(get_admin_db),
) -> dict:
    """テナントを物理削除する（DROP SCHEMA CASCADE）。不可逆操作。論理削除済みのみ実行可。"""
    # 1. 対象確認
    row = (
        await db.execute(
            text(
                "SELECT id, tenant_code, tenant_name, is_active"
                " FROM public.tenants WHERE id = :id"
            ),
            {"id": tenant_id},
        )
    ).mappings().one_or_none()
    if not row:
        raise HTTPException(404, "テナントが見つかりません")

    if body.confirm != f"DELETE:{row['tenant_code']}":
        raise HTTPException(
            400,
            f"confirm 文字列不一致。期待値: DELETE:{row['tenant_code']}",
        )

    if row["is_active"]:
        raise HTTPException(400, "論理削除（is_active=False）が先に必要です")

    schema_name = f"tenant_{tenant_id:03d}"

    # スキーマ名は整数から生成しているが念のため確認
    if not schema_name.replace("_", "").isalnum():
        raise HTTPException(400, "不正な tenant_id")

    # 3. 監査ログ: status=started を DROP 前に記録
    audit_result = await db.execute(
        text(
            "INSERT INTO public.tenant_deletion_audit"
            "    (tenant_id, tenant_code, tenant_name, mode, status,"
            "     actor_id, actor_email, executed_at)"
            " VALUES"
            "    (:tenant_id, :tenant_code, :tenant_name, 'physical', 'started',"
            "     :actor_id, :actor_email, NOW())"
            " RETURNING id"
        ),
        {
            "tenant_id": tenant_id,
            "tenant_code": row["tenant_code"],
            "tenant_name": row["tenant_name"],
            "actor_id": current_user.id,
            "actor_email": current_user.email,
        },
    )
    audit_id = audit_result.scalar_one()
    await db.commit()
    # reset_tenant_context() 不要（get_current_tenant なし）

    try:
        # 4. DROP SCHEMA CASCADE
        await admin_db.execute(
            text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")  # noqa: S608
        )
        # 5. admin_db を明示 commit（get_admin_db に success-commit がないため必須 recon C-9）
        await admin_db.commit()

        # 6. public.tenants DELETE（CASCADE → public.users 連鎖削除）
        async with db.begin():
            await db.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": tenant_id},
            )

        # 7. 監査ログ: status=succeeded + completed_at
        async with db.begin():
            await db.execute(
                text(
                    "UPDATE public.tenant_deletion_audit"
                    " SET status = 'succeeded', completed_at = NOW()"
                    " WHERE id = :id"
                ),
                {"id": audit_id},
            )

    except Exception as exc:
        # 失敗時: 監査ログを failed に更新
        try:
            async with db.begin():
                await db.execute(
                    text(
                        "UPDATE public.tenant_deletion_audit"
                        " SET status = 'failed', error_message = :err, completed_at = NOW()"
                        " WHERE id = :id"
                    ),
                    {"id": audit_id, "err": str(exc)[:2000]},
                )
        except Exception:
            pass
        raise

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "mode": "physical",
        "schema_dropped": schema_name,
    }
