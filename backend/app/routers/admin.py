from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, reset_tenant_context
from app.database import get_admin_db, get_db
from app.models import Tenant, User
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.audit import record_audit_log
from app.services.tenant import create_tenant_schema

router = APIRouter()


@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def register_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    admin_db: AsyncSession = Depends(get_admin_db),
    current_user: User = Depends(get_current_user),
):
    """
    テナント（契約企業）を登録し、専用スキーマを自動生成する。

    フロー:
      ① tenant_codeの重複チェック
      ② public.tenants にテナント情報を保存
      ③ tenant_{id:03d} スキーマを自動作成
      ④ スキーマ内に業務テーブル（companies, deals, orders, audit_logs）を作成
      ⑤ Row Level Security（RLS）ポリシーを自動適用

    注意:
      - tenant_codeは英小文字・数字・ハイフンのみ（例: "demo-a", "company-123"）
      - 管理者（role="admin"）のみ実行可能
    """
    # 管理者権限チェック
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="テナント作成は管理者のみ可能です",
        )

    # tenant_codeの重複チェック
    result = await db.execute(
        select(Tenant).where(Tenant.tenant_code == data.tenant_code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"テナントコード '{data.tenant_code}' は既に使用されています",
        )

    # テナント作成（autobegun トランザクションを継続使用。auth.py/companies.py と同パターン）
    # create_tenant_schema が途中で失敗した場合は except で明示ロールバックし、
    # tenant レコードが残らないよう保証する。
    try:
        tenant = Tenant(
            tenant_name=data.tenant_name,
            tenant_code=data.tenant_code,
            is_active=True,
        )
        db.add(tenant)
        await db.flush()  # IDを確定させる（commit前にIDが必要）

        # seed_system_roles / seed_default_channel_masters は RLS 有効スキーマへの
        # INSERT を含む。salesanchor_app（NOBYPASSRLS）で接続しているため、
        # WITH CHECK が app.tenant_id と行の tenant_id を比較する。
        # 新テナントの ID に切り替えないと 42501 になる。
        await db.execute(text(f"SET app.tenant_id = '{int(tenant.id)}'"))

        # 専用スキーマを自動生成（テーブル + RLSポリシー込み）
        schema_name = await create_tenant_schema(db, tenant.id, admin_db=admin_db)

        # 監査ログは呼び出し元（管理者）テナントに書くため、
        # app.tenant_id を current_user.tenant_id に戻す。
        await db.execute(text(f"SET app.tenant_id = '{int(current_user.tenant_id)}'"))

        # 監査ログ記録
        await record_audit_log(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="create",
            table_name="tenants",
            record_id=tenant.id,
            new_data={
                "tenant_name": tenant.tenant_name,
                "tenant_code": tenant.tenant_code,
                "schema_name": schema_name,
            },
        )
        await db.commit()
        # ADR-072: commit 後に管理者テナントのコンテキストを再設定する。
        # SQLAlchemy は commit 後に別コネクションを払い出す可能性があるため
        # search_path / app.tenant_id を再 SET しておく。
        await reset_tenant_context(db, current_user.tenant_id)
    except Exception:
        await db.rollback()
        raise

    return TenantResponse(
        id=tenant.id,
        tenant_name=tenant.tenant_name,
        tenant_code=tenant.tenant_code,
        is_active=tenant.is_active,
        schema_name=schema_name,
    )
