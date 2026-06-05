from __future__ import annotations

"""API連携（外部サービス連携）ルーター。

現状は Googleドライブ連携（OAuth ユーザー委任方式）の動作確認用:
  Public（認証不要・Google からのリダイレクト）:
    GET  /integrations/google-drive/connect/callback   OAuth callback

  Tenant 認証必須:
    GET    /integrations/google-drive/connect/start     OAuth URL 返却（admin）
    DELETE /integrations/google-drive/connect           接続解除（admin）
    GET    /integrations/google-drive/status            接続状態
    POST   /integrations/google-drive/test-upload       テスト PDF を保存

設計は google_calendar.py に準拠（テナント共通接続・Fernet 暗号化トークン）。
サービスアカウント方式と違い「接続した人のドライブ」に保存するため Workspace 不要。

変更履歴:
  2026-06-06: OAuth ユーザー委任方式へ全面切替（旧サービスアカウント方式を置換）
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services import google_drive_oauth as drive_svc
from app.services.test_pdf import render_test_pdf

logger = logging.getLogger(__name__)

# Public ルーター（main.py で認証なしに登録）
public_router = APIRouter()
# 認証必須ルーター（main.py で get_current_tenant 付きに登録）
router = APIRouter()

_TEST_PDF_FILENAME = "salesanchor-test.pdf"


def _frontend_base_url() -> str:
    explicit = os.getenv("FRONTEND_BASE_URL", "")
    if explicit:
        return explicit.rstrip("/")
    origins = os.getenv("ALLOWED_ORIGINS", "")
    first = next((o.strip() for o in origins.split(",") if o.strip()), "")
    return (first or "https://app.salesanchor.jp").rstrip("/")


def _drive_page_url() -> str:
    return f"{_frontend_base_url()}/management-center/integrations/google-drive"


def _require_admin(user: User) -> None:
    if getattr(user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作は管理者のみ実行できます",
        )


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------


class DriveStatus(BaseModel):
    oauth_configured: bool  # サーバーに OAuth クライアント設定があるか
    connected: bool  # テナントが Google アカウントを接続済みか
    account_email: str | None = None
    connected_at: str | None = None


class TestUploadRequest(BaseModel):
    drive_url: str | None = None  # 空ならマイドライブ直下に保存


class TestUploadResponse(BaseModel):
    file_id: str
    file_name: str
    web_view_link: str | None = None


# ---------------------------------------------------------------------------
# Public: OAuth callback（Google から Bearer なしでリダイレクト）
# ---------------------------------------------------------------------------


@public_router.get(
    "/integrations/google-drive/connect/callback",
    tags=["integrations"],
    include_in_schema=False,
)
async def connect_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Google から認可コードを受け取り、トークンを DB に保存する（認証不要）。"""
    page = _drive_page_url()
    try:
        result = await drive_svc.exchange_code(code, state)
    except ValueError as e:
        logger.warning("Google Drive callback: state 検証失敗 %s", e)
        return RedirectResponse(f"{page}?connected=false&error=invalid_state")
    except RuntimeError as e:
        logger.error("Google Drive callback: token 交換失敗 %s", e)
        return RedirectResponse(f"{page}?connected=false&error=token_exchange")

    from app.services.encryption import encrypt

    try:
        await db.execute(
            text(
                """
                INSERT INTO tenant_google_drive_config
                  (tenant_id, access_token_encrypted, refresh_token_encrypted,
                   token_expiry, account_email, connected_by_user_id, connected_at, updated_at)
                VALUES
                  (:tid, :at, :rt, :exp, :email, :uid, NOW(), NOW())
                ON CONFLICT (tenant_id) DO UPDATE SET
                  access_token_encrypted  = EXCLUDED.access_token_encrypted,
                  refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                  token_expiry            = EXCLUDED.token_expiry,
                  account_email           = EXCLUDED.account_email,
                  connected_by_user_id    = EXCLUDED.connected_by_user_id,
                  connected_at            = NOW(),
                  updated_at              = NOW()
                """
            ),
            {
                "tid": result["tenant_id"],
                "at": encrypt(result["access_token"]),
                "rt": encrypt(result["refresh_token"]),
                "exp": result["expiry"],
                "email": result.get("account_email"),
                "uid": result["user_id"],
            },
        )
        await db.commit()
        await reset_tenant_context(db, result["tenant_id"])  # ADR-072 Phase 2.5
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        logger.error("Google Drive callback: DB 保存失敗 %s", e)
        return RedirectResponse(f"{page}?connected=false&error=db_error")

    return RedirectResponse(f"{page}?connected=true")


# ---------------------------------------------------------------------------
# Authenticated
# ---------------------------------------------------------------------------


@router.get("/integrations/google-drive/connect/start", tags=["integrations"])
async def connect_start(
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Google OAuth 同意画面の URL を返す（admin 専用）。"""
    _require_admin(user)
    try:
        auth_url = await drive_svc.get_auth_url(tenant_id, user.id)
    except RuntimeError:
        # 例外文には未設定の環境変数名等が含まれ得るためクライアントへは固定文言を返す
        logger.exception("[integrations] Google Drive OAuth URL 生成に失敗")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="連携の準備に失敗しました。サーバー設定をご確認ください（管理者へ連絡）。",
        )
    return {"auth_url": auth_url}


@router.delete(
    "/integrations/google-drive/connect",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["integrations"],
)
async def disconnect(
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Google ドライブ接続を解除する（admin 専用）。"""
    _require_admin(user)
    await db.execute(
        text("DELETE FROM tenant_google_drive_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5


@router.get(
    "/integrations/google-drive/status",
    response_model=DriveStatus,
    tags=["integrations"],
)
async def drive_status(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """サーバー設定（OAuthクライアント）と接続状態を返す。"""
    conn = await drive_svc.get_connection(db, tenant_id)
    return DriveStatus(
        oauth_configured=drive_svc.is_oauth_configured(),
        connected=conn is not None,
        account_email=conn["account_email"] if conn else None,
        connected_at=(conn["connected_at"].isoformat() if conn and conn["connected_at"] else None),
    )


@router.post(
    "/integrations/google-drive/test-upload",
    response_model=TestUploadResponse,
    tags=["integrations"],
)
async def test_upload(
    payload: TestUploadRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """「テスト」PDF を生成し、接続アカウントのドライブに保存する。"""
    folder_id = drive_svc.extract_folder_id(payload.drive_url) if payload.drive_url else None
    if payload.drive_url and not folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="フォルダの URL が正しくありません。フォルダの URL を貼り付けるか、空欄にしてください。",
        )

    pdf_bytes = await run_in_threadpool(render_test_pdf, "テスト")
    try:
        result = await drive_svc.upload_pdf(db, tenant_id, pdf_bytes, _TEST_PDF_FILENAME, folder_id)
    except RuntimeError as e:
        # 未接続など利用側起因
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:  # noqa: BLE001 — google API 例外（機微情報を含み得るためクライアントに返さない）
        logger.exception("[integrations] Google Drive へのアップロードに失敗")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ドライブへの保存に失敗しました。フォルダの権限やアクセス権をご確認ください。",
        )

    return TestUploadResponse(
        file_id=result["id"],
        file_name=result["name"],
        web_view_link=result.get("web_view_link"),
    )
