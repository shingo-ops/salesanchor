"""
顧客登録トークン API（ADR-SA-03）。

担当者がリードに個別登録リンクを発行し、顧客が自分で住所・連絡先を登録する仕組み。
テナントはトークン（HMAC-SHA256 署名）が決める——フォーム入力ではなく構造で分離。

エンドポイント:
  POST /api/v1/registration-tokens       — 認証必須。担当者がリンク発行
  GET  /api/v1/public/register           — 公開。トークン検証してフォーム用データ返却
  POST /api/v1/public/register           — 公開。顧客入力を登録
  POST /api/v1/public/register/address   — 公開。住所追加（append、上書きしない）

セキュリティ:
  - /public/ エンドポイントは JWT 認証不要
  - テナント ID・リード ID はトークンから確定（ボディから受け付けない）
  - ADR-072: write の db.commit() 直後に reset_tenant_context() を呼ぶ
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.registration_token import (
    AddAddressRequest,
    CreateTokenRequest,
    CreateTokenResponse,
    RegisterRequest,
    RegisterResponse,
    TokenVerifyResponse,
)
from app.services.registration_token import (
    create_registration_token,
    mark_token_used,
    verify_token,
)

logger = logging.getLogger(__name__)

# 認証必須エンドポイント用ルーター
router = APIRouter()

# 公開エンドポイント用ルーター（JWT 認証不要）
public_router = APIRouter()


# --- 認証必須: 担当者がトークン発行 ---


@router.post(
    "/registration-tokens",
    response_model=CreateTokenResponse,
    status_code=201,
)
async def create_token(
    data: CreateTokenRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """担当者がリード向けに登録リンクを発行する。

    期限 7 日・単回使用。顧客に raw_token を含む URL を送付する。
    """
    raw_token, expires_at = await create_registration_token(
        db,
        tenant_id=tenant_id,
        lead_id=data.lead_id,
        created_by=current_user.id,
        token_type=data.type.value,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    # 登録 URL を組み立て
    base_url = os.getenv("FRONTEND_URL", "https://app.salesanchor.jp").rstrip("/")
    if data.type.value == "add_address":
        registration_url = f"{base_url}/register/address?token={raw_token}"
    else:
        registration_url = f"{base_url}/register?token={raw_token}"

    return CreateTokenResponse(
        token=raw_token,
        registration_url=registration_url,
        expires_at=expires_at,
    )


# --- 公開: トークン検証（フォーム表示用データ返却） ---


@public_router.get(
    "/public/register",
    response_model=TokenVerifyResponse,
)
async def verify_registration_token(
    token: str = Query(..., description="登録トークン"),
    db: AsyncSession = Depends(get_db),
):
    """トークンを検証してフォーム用データを返す。

    トークンが無効（改ざん・期限切れ・使用済み）の場合は 403。
    """
    token_info = await verify_token(db, token)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無効または期限切れのトークンです",
        )

    # テナントスキーマに切り替えてリード情報を取得
    tenant_id = token_info["tenant_id"]
    lead_id = token_info["lead_id"]
    schema_name = f"tenant_{int(tenant_id):03d}"
    await db.execute(text(f"SET search_path = {schema_name}, public"))

    # リードに紐づく会社名を取得（存在しない場合もある）
    company_name = None
    result = await db.execute(
        text("""
            SELECT c.name
            FROM companies c
            JOIN leads l ON l.company_id = c.id
            WHERE l.id = :lead_id
        """),
        {"lead_id": lead_id},
    )
    row = result.first()
    if row:
        company_name = row[0]

    return TokenVerifyResponse(
        valid=True,
        company_name=company_name,
        lead_id=lead_id,
        token_type=token_info["type"],
    )


# --- 公開: 顧客登録 ---


@public_router.post(
    "/public/register",
    response_model=RegisterResponse,
)
async def register_customer(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """顧客がフォームから住所・連絡先を登録する。

    テナント ID・リード ID はトークンから確定（ボディから受け付けない）。
    トークン改ざん・期限切れ・使用済みの場合は 403。
    """
    token_info = await verify_token(db, data.token)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無効または期限切れのトークンです",
        )

    tenant_id = token_info["tenant_id"]
    lead_id = token_info["lead_id"]
    token_id = token_info["id"]

    # テナントスキーマに切り替え
    schema_name = f"tenant_{int(tenant_id):03d}"
    await db.execute(text(f"SET search_path = {schema_name}, public"))

    # リードに紐づく会社 ID を取得
    result = await db.execute(
        text("SELECT company_id FROM leads WHERE id = :lead_id"),
        {"lead_id": lead_id},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="リードに紐づく会社が見つかりません",
        )
    company_id = row[0]

    # 住所を登録
    for addr in data.addresses:
        await db.execute(
            text("""
                INSERT INTO company_addresses (
                    company_id, address_type, branch_name,
                    name, email, telephone, tax_id,
                    address_line_1, address_line_2, address_line_3,
                    city, state, zip, country_code, is_default
                ) VALUES (
                    :cid, :atype, :branch,
                    :name, :email, :telephone, :tax_id,
                    :l1, :l2, :l3, :city, :state, :zip, :country, :is_default
                )
            """),
            {
                "cid": company_id,
                "atype": addr.address_type,
                "branch": addr.branch_name,
                "name": addr.name,
                "email": addr.email,
                "telephone": addr.telephone,
                "tax_id": addr.tax_id,
                "l1": addr.address_line_1,
                "l2": addr.address_line_2,
                "l3": addr.address_line_3,
                "city": addr.city,
                "state": addr.state,
                "zip": addr.zip,
                "country": addr.country_code,
                "is_default": addr.is_default,
            },
        )

    # 担当者情報を contacts に登録（入力がある場合）
    if data.contact_name or data.contact_email or data.contact_telephone:
        await db.execute(
            text("""
                INSERT INTO contacts (
                    company_id, name, email, telephone,
                    is_primary_contact
                ) VALUES (
                    :cid, :name, :email, :telephone, FALSE
                )
            """),
            {
                "cid": company_id,
                "name": data.contact_name or "",
                "email": data.contact_email,
                "telephone": data.contact_telephone,
            },
        )

    # トークンを使用済みにマーク
    await mark_token_used(db, str(token_id))

    await db.commit()
    await reset_tenant_context(db, tenant_id)

    return RegisterResponse(
        success=True,
        message="登録が完了しました",
    )


# --- 公開: 住所追加 ---


@public_router.post(
    "/public/register/address",
    response_model=RegisterResponse,
)
async def add_address(
    data: AddAddressRequest,
    db: AsyncSession = Depends(get_db),
):
    """顧客が住所を追加する（append、上書きしない）。

    テナント ID・リード ID はトークンから確定（ボディから受け付けない）。
    トークン改ざん・期限切れ・使用済みの場合は 403。
    """
    token_info = await verify_token(db, data.token)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無効または期限切れのトークンです",
        )

    tenant_id = token_info["tenant_id"]
    lead_id = token_info["lead_id"]
    token_id = token_info["id"]

    # テナントスキーマに切り替え
    schema_name = f"tenant_{int(tenant_id):03d}"
    await db.execute(text(f"SET search_path = {schema_name}, public"))

    # リードに紐づく会社 ID を取得
    result = await db.execute(
        text("SELECT company_id FROM leads WHERE id = :lead_id"),
        {"lead_id": lead_id},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="リードに紐づく会社が見つかりません",
        )
    company_id = row[0]

    addr = data.address
    await db.execute(
        text("""
            INSERT INTO company_addresses (
                company_id, address_type, branch_name,
                name, email, telephone, tax_id,
                address_line_1, address_line_2, address_line_3,
                city, state, zip, country_code, is_default
            ) VALUES (
                :cid, :atype, :branch,
                :name, :email, :telephone, :tax_id,
                :l1, :l2, :l3, :city, :state, :zip, :country, :is_default
            )
        """),
        {
            "cid": company_id,
            "atype": addr.address_type,
            "branch": addr.branch_name,
            "name": addr.name,
            "email": addr.email,
            "telephone": addr.telephone,
            "tax_id": addr.tax_id,
            "l1": addr.address_line_1,
            "l2": addr.address_line_2,
            "l3": addr.address_line_3,
            "city": addr.city,
            "state": addr.state,
            "zip": addr.zip,
            "country": addr.country_code,
            "is_default": addr.is_default,
        },
    )

    # トークンを使用済みにマーク
    await mark_token_used(db, str(token_id))

    await db.commit()
    await reset_tenant_context(db, tenant_id)

    return RegisterResponse(
        success=True,
        message="住所を追加しました",
    )
