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
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    set_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services import carrier_credentials as carriers
from app.services import google_drive_oauth as drive_svc
from app.services import paypal_payments
from app.services.audit import record_audit_log
from app.services.test_pdf import render_test_pdf

logger = logging.getLogger(__name__)

# Public ルーター（main.py で認証なしに登録）
public_router = APIRouter()

# Increment 2.5: 公開 webhook/return の本番ベース URL（env で上書き可）。
_API_BASE_URL = os.getenv("API_BASE_URL", "https://api.salesanchor.jp").rstrip("/")
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
    old_result = await db.execute(
        text("""
            SELECT id, tenant_id, account_email, folder_id,
                   connected_by_user_id, connected_at
            FROM tenant_google_drive_config
            WHERE tenant_id = :tid
        """),
        {"tid": tenant_id},
    )
    old_row = old_result.mappings().first()
    await db.execute(
        text("DELETE FROM tenant_google_drive_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    if old_row:
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=user.id,
            action="delete", table_name="tenant_google_drive_config",
            record_id=old_row["id"], old_data=dict(old_row), new_data=None,
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


# ===========================================================================
# 配送キャリア（FedEx / DHL / UPS）接続テスト — テナント別認証情報
# ===========================================================================


class CarrierStatus(BaseModel):
    carrier: str
    configured: bool
    environment: str
    # ADR-125 UX: フィールド別登録ヒント（シークレット平文は返さない）
    client_id_hint: str | None = None
    secret_configured: bool = False
    account_number_hint: str | None = None  # 例: "******011"


class CarrierCredentialsRequest(BaseModel):
    client_id: str  # FedEx/UPS=APIキー, DHL=API Key
    client_secret: str  # FedEx/UPS=シークレットキー, DHL=API Secret
    # ADR-125 UX: environment は顧客UIから受け取らず production 固定（フィールド削除）
    # 内部テスト用に受け取ってもサーバー側で上書きする
    environment: str = "production"
    # ADR-125 D2: FedEx / UPS 配送アカウント番号（Rates/Ship API に必須）
    # None = 未入力（既存値を保持する）
    account_number: str | None = None


class CarrierTestResponse(BaseModel):
    ok: bool
    status_code: int | None = None
    message: str


def _validate_carrier(carrier: str) -> None:
    if not carriers.is_valid_carrier(carrier):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未対応のキャリアです")


@router.get(
    "/integrations/carriers/{carrier}/status",
    response_model=CarrierStatus,
    dependencies=[Depends(require_permission("erp.view"))],
)
async def carrier_status(
    carrier: str,
    environment: str = Query("production"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> CarrierStatus:
    """キャリアの認証情報の設定状況とフィールド別登録ヒント（シークレット平文は返さない）。
    ADR-129: environment クエリパラメータで本番/Sandbox を切り替え可能。
    """
    _validate_carrier(carrier)
    st = await carriers.get_status(db, tenant_id, carrier, environment=environment)
    return CarrierStatus(
        carrier=carrier,
        configured=st["configured"],
        environment=st["environment"],
        client_id_hint=st["client_id_hint"],
        secret_configured=st["secret_configured"],
        account_number_hint=st["account_number_hint"],
    )


@router.put(
    "/integrations/carriers/{carrier}/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def save_carrier_credentials(
    carrier: str,
    payload: CarrierCredentialsRequest,
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """キャリア認証情報を保存（暗号化）。admin 専用。"""
    _validate_carrier(carrier)
    _require_admin(user)
    if not payload.client_id or not payload.client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="認証ID・シークレットの両方を入力してください。",
        )
    # 変更前の非機密情報を取得（機密値は記録しない）
    # ADR-129: payload.environment で本番/Sandbox を区別して保存
    old_status = await carriers.get_status(db, tenant_id, carrier, environment=payload.environment)
    audit_action = "update" if old_status["configured"] else "create"
    old_audit = {
        "carrier": carrier,
        "environment": old_status["environment"],
        "account_number_hint": old_status["account_number_hint"],
    } if old_status["configured"] else None

    await carriers.save_credentials(
        db,
        tenant_id,
        carrier,
        payload.client_id,
        payload.client_secret,
        payload.environment,  # ADR-129: 環境を受け取り（旧: production 固定）
        user.id,
        account_number=payload.account_number,
    )
    # NOTE: save_credentials は内部で db.commit() 済み（carrier_credentials.py:182）。
    # audit は別 tx になる（既知の構造的制約: 設計doc §5 参照）。
    new_status = await carriers.get_status(db, tenant_id, carrier, environment=payload.environment)
    new_audit = {
        "carrier": carrier,
        "environment": new_status["environment"],
        "account_number_hint": new_status["account_number_hint"],
    }
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=user.id,
        action=audit_action, table_name="tenant_carrier_credentials",
        record_id=None, old_data=old_audit, new_data=new_audit,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5


@router.delete(
    "/integrations/carriers/{carrier}/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_carrier_credentials(
    carrier: str,
    environment: str = Query("production"),
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """キャリア認証情報を削除。admin 専用。ADR-129: environment クエリパラメータで本番/Sandbox を指定。"""
    _validate_carrier(carrier)
    _require_admin(user)
    # 削除前の非機密情報を取得（機密値は記録しない）
    old_status = await carriers.get_status(db, tenant_id, carrier, environment=environment)
    old_audit = {
        "carrier": carrier,
        "environment": old_status["environment"],
        "account_number_hint": old_status["account_number_hint"],
    } if old_status["configured"] else None

    await carriers.delete_credentials(db, tenant_id, carrier, environment=environment)
    # NOTE: delete_credentials は内部で db.commit() 済み（carrier_credentials.py:190）。
    # audit は別 tx になる（既知の構造的制約: 設計doc §5 参照）。
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=user.id,
        action="delete", table_name="tenant_carrier_credentials",
        record_id=None, old_data=old_audit, new_data=None,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5


@router.post(
    "/integrations/carriers/{carrier}/test-connection",
    response_model=CarrierTestResponse,
    dependencies=[Depends(require_permission("erp.view"))],
)
async def carrier_test_connection(
    carrier: str,
    environment: str = Query("production"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> CarrierTestResponse:
    """保存済みの認証情報で各社 API への疎通（認証）を確認する。
    ADR-129: environment クエリパラメータで本番/Sandbox を切り替え可能。
    """
    _validate_carrier(carrier)
    creds = await carriers.get_credentials(db, tenant_id, carrier, environment=environment)
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="認証情報が未設定です。先に保存してください。",
        )
    result = await run_in_threadpool(
        carriers.test_connection,
        carrier,
        creds["environment"],
        creds["client_id"],
        creds["client_secret"],
    )
    return CarrierTestResponse(ok=result["ok"], status_code=result.get("status_code"), message=result["message"])


# ===========================================================================
# PayPal 決済連携（テナント別認証情報・Model A）
# ===========================================================================


class PaypalStatus(BaseModel):
    configured: bool
    environment: str


class PaypalCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    environment: str = "sandbox"


class PaypalTestResponse(BaseModel):
    ok: bool
    status_code: int | None = None
    message: str


@router.get(
    "/integrations/paypal/status",
    response_model=PaypalStatus,
    dependencies=[Depends(require_permission("erp.view"))],
)
async def paypal_status(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> PaypalStatus:
    """PayPal 認証情報の設定状況（シークレットは返さない）。"""
    st = await paypal_payments.get_status(db, tenant_id)
    return PaypalStatus(configured=st["configured"], environment=st["environment"])


@router.put(
    "/integrations/paypal/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def save_paypal_credentials(
    payload: PaypalCredentialsRequest,
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """PayPal 認証情報を保存（暗号化）。admin 専用。"""
    _require_admin(user)
    if not payload.client_id or not payload.client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client ID・Client Secret の両方を入力してください。",
        )
    await paypal_payments.save_credentials(
        db, tenant_id, payload.client_id, payload.client_secret, payload.environment, user.id
    )
    # Increment 2.5: PayPal webhook を自動登録（best-effort・失敗しても接続は成功させる）。
    webhook_url = f"{_API_BASE_URL}/api/v1/integrations/paypal/webhook"
    try:
        reg = await run_in_threadpool(
            paypal_payments.register_webhook,
            payload.environment, payload.client_id, payload.client_secret, webhook_url,
        )
        if reg.get("ok") and reg.get("webhook_id"):
            await paypal_payments.save_webhook_id(db, tenant_id, reg["webhook_id"])
        else:
            logger.warning("[paypal] webhook 自動登録できず（接続は継続）: %s", reg.get("message"))
    except Exception as e:  # noqa: BLE001
        logger.warning("[paypal] webhook 自動登録に失敗（接続は継続）: %s", e)
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5


@router.delete(
    "/integrations/paypal/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_paypal_credentials(
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """PayPal 認証情報を削除。admin 専用。"""
    _require_admin(user)
    await paypal_payments.delete_credentials(db, tenant_id)
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5


@router.post(
    "/integrations/paypal/test-connection",
    response_model=PaypalTestResponse,
    dependencies=[Depends(require_permission("erp.view"))],
)
async def paypal_test_connection(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> PaypalTestResponse:
    """保存済みの認証情報で PayPal API への疎通（認証）を確認する。"""
    creds = await paypal_payments.get_credentials(db, tenant_id)
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="認証情報が未設定です。先に保存してください。",
        )
    result = await run_in_threadpool(
        paypal_payments.test_connection,
        creds["environment"],
        creds["client_id"],
        creds["client_secret"],
    )
    return PaypalTestResponse(ok=result["ok"], status_code=result.get("status_code"), message=result["message"])


class PaypalTestInvoiceResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    amount: float
    currency: str
    approval_url: str


@router.post(
    "/integrations/paypal/test-invoice",
    response_model=PaypalTestInvoiceResponse,
    dependencies=[Depends(require_permission("erp.view"))],
)
async def paypal_test_invoice(
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaypalTestInvoiceResponse:
    """決済テスト用: sandbox 限定でテスト請求書を作成し PayPal 請求書を送付する。admin 専用。

    専用「PayPalテスト」会社/担当者を find-or-create し、¥100 のテスト請求書(issued)を作成→
    PayPal Invoicing で請求書を送付する（ADR-101 改訂 2026-06-12）。webhook自動/手動 の確認用。
    """
    _require_admin(user)
    creds = await paypal_payments.get_credentials(db, tenant_id)
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PayPal が未接続です（先に認証情報を登録してください）",
        )
    if creds["environment"] != "sandbox":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="決済テストは sandbox 環境でのみ実行できます（本番では実課金になります）",
        )

    # 1. 「PayPalテスト」会社 find-or-create（company_code で一意）
    comp_row = (await db.execute(
        text("SELECT id FROM companies WHERE company_code = 'PAYPAL-TEST'")
    )).first()
    if comp_row:
        company_id = comp_row[0]
    else:
        company_id = (await db.execute(
            text("INSERT INTO companies (tenant_id, company_code, name) "
                 "VALUES (:tid, 'PAYPAL-TEST', 'PayPal決済テスト') RETURNING id"),
            {"tid": tenant_id},
        )).scalar_one()

    # 2. テスト担当者 find-or-create（contact_code で一意）。Invoicing は email 必須なので placeholder を設定。
    test_email = "paypal-test@example.com"
    cont_row = (await db.execute(
        text("SELECT id FROM contacts WHERE contact_code = 'PAYPAL-TEST'")
    )).first()
    if cont_row:
        contact_id = cont_row[0]
        await db.execute(
            text("UPDATE contacts SET primary_email = COALESCE(primary_email, :em) WHERE id = :id"),
            {"id": contact_id, "em": test_email},
        )
    else:
        contact_id = (await db.execute(
            text("INSERT INTO contacts (tenant_id, company_id, contact_code, display_name, primary_email) "
                 "VALUES (:tid, :cid, 'PAYPAL-TEST', 'PayPal Test', :em) RETURNING id"),
            {"tid": tenant_id, "cid": company_id, "em": test_email},
        )).scalar_one()

    # 3. ¥100 テスト請求書を issued で作成
    next_id = (await db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM invoices"))).scalar()
    invoice_number = f"IN-{next_id:04d}-01"
    erp_key = str(uuid.uuid4())[:8].upper()
    invoice_id = (await db.execute(
        text("""
            INSERT INTO invoices (
                tenant_id, invoice_number, company_id, contact_id, currency,
                subtotal, shipping_fee, tax_amount, total_amount,
                payment_method, status, branch_number, erp_key, issued_at, created_by
            ) VALUES (
                :tid, :num, :cid, :coid, 'JPY',
                100, 0, 0, 100,
                'paypal', 'issued', 1, :erp, NOW(), :uid
            ) RETURNING id
        """),
        {"tid": tenant_id, "num": invoice_number, "cid": company_id,
         "coid": contact_id, "erp": erp_key, "uid": user.id},
    )).scalar_one()
    await db.execute(
        text("INSERT INTO invoice_items "
             "(invoice_id, product_name, quantity, unit_price, subtotal, sort_order) "
             "VALUES (:iid, 'PayPal決済テスト', 1, 100, 100, 0)"),
        {"iid": invoice_id},
    )

    # 4. PayPal 請求書を送付（本番 issue_paypal_link と同じ Invoicing フローを使用）
    result = await run_in_threadpool(
        paypal_payments.create_and_send_invoice,
        creds["environment"], creds["client_id"], creds["client_secret"],
        invoice_number=invoice_number,
        currency="JPY",
        amount=100,
        recipient_email=test_email,
        reference=f"{tenant_id}:{invoice_id}",
    )
    if not result.get("ok"):
        await db.rollback()  # 請求書を中途半端に残さない（atomic）
        await reset_tenant_context(db, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("message", "PayPal 請求書の発行に失敗しました"),
        )

    await db.execute(
        text("UPDATE invoices SET paypal_order_id = :oid, paypal_approval_url = :url, "
             "updated_at = NOW() WHERE id = :id"),
        {"id": invoice_id, "oid": result["paypal_invoice_id"], "url": result["recipient_view_url"]},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    return PaypalTestInvoiceResponse(
        invoice_id=invoice_id, invoice_number=invoice_number,
        amount=100, currency="JPY", approval_url=result["recipient_view_url"],
    )


# ---------------------------------------------------------------------------
# Public: PayPal 戻りURL自動 capture（Increment 2・Bearer 不要）
# 顧客が決済リンクで支払い→承認後ここへ戻る→自動 capture→請求書 paid＋受注 sourcing。
# 多重防御: ①Fernet 署名トークン ②PayPal token と保存 order_id の一致 ③capture は承認済のみ成功 ④冪等。
# ---------------------------------------------------------------------------


def _paypal_html(title_ja: str, title_en: str, status_code: int = 200) -> HTMLResponse:
    """顧客向けの最小 HTML（React 外＝i18n 対象外。ADR-101 に従い英語併記）。"""
    body = (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title_en}</title></head>"
        '<body style="font-family:sans-serif;max-width:480px;margin:64px auto;'
        'padding:0 24px;text-align:center;color:#2b2b2b">'
        f'<h2 style="margin-bottom:8px">{title_ja}</h2>'
        f'<p style="color:#6b6b6b">{title_en}</p>'
        "</body></html>"
    )
    return HTMLResponse(content=body, status_code=status_code)


@public_router.get("/integrations/paypal/return", include_in_schema=False)
async def paypal_return(
    t: str = Query(...),
    token: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    """顧客が PayPal で支払い後に戻る公開エンドポイント。自動 capture して請求書を paid にする。"""
    parsed = paypal_payments.parse_return_token(t)
    if not parsed:
        return _paypal_html("リンクが無効です", "Invalid or expired link", status_code=400)
    tenant_id, invoice_id = parsed

    await set_tenant_context(db, tenant_id)
    try:
        inv = await db.execute(
            text("SELECT id, status, paypal_order_id FROM invoices WHERE id = :id"),
            {"id": invoice_id},
        )
        row = inv.mappings().first()
        if not row or not row["paypal_order_id"] or (token and row["paypal_order_id"] != token):
            return _paypal_html("注文が見つかりません", "Order not found", status_code=404)
        if row["status"] == "paid":
            return _paypal_html("お支払いは完了しています", "Payment already completed")
        if row["status"] not in ("issued", "overdue"):
            return _paypal_html("この請求書は支払い対象外です", "This invoice is not payable", status_code=400)

        creds = await paypal_payments.get_credentials(db, tenant_id)
        if not creds:
            return _paypal_html("決済設定が見つかりません", "Payment configuration not found", status_code=400)

        result = await run_in_threadpool(
            paypal_payments.capture_order,
            creds["environment"], creds["client_id"], creds["client_secret"],
            row["paypal_order_id"],
        )
        if not result.get("captured"):
            return _paypal_html("お支払いを確認できませんでした", "Payment could not be confirmed", status_code=409)

        await db.execute(
            text("UPDATE invoices SET status='paid', paid_at=NOW(), payment_fee=:fee, "
                 "payment_method='paypal', updated_at=NOW() "
                 "WHERE id=:id AND status IN ('issued','overdue')"),
            {"id": invoice_id, "fee": result.get("fee")},
        )
        # ADR-104: 紐づく受注を 支払い待ち→仕入れ中 へ自動遷移（awaiting_payment のみ）
        await db.execute(
            text("UPDATE orders SET status='sourcing', paid_at=NOW(), updated_at=NOW() "
                 "WHERE invoice_id=:iid AND status='awaiting_payment'"),
            {"iid": invoice_id},
        )
        await db.commit()
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        logger.error("[paypal] return capture 失敗: %s", e)
        return _paypal_html("処理中にエラーが発生しました", "An error occurred", status_code=500)
    finally:
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5

    return _paypal_html("お支払いありがとうございました", "Thank you, your payment was received")


@public_router.get("/integrations/paypal/cancel", include_in_schema=False)
async def paypal_cancel():
    """顧客が PayPal でキャンセルしたときの公開戻り先。"""
    return _paypal_html("お支払いはキャンセルされました", "Payment was cancelled")


# ---------------------------------------------------------------------------
# Public: PayPal Webhook（Increment 2.5・Bearer 不要）
# 顧客が戻らなくても CHECKOUT.ORDER.APPROVED 受信で当方 capture→請求書 paid＋受注 sourcing。
# 防御: 署名検証（verify-webhook-signature）／custom_id でテナント固定／order_id 一致／冪等。
# ---------------------------------------------------------------------------


def _parse_custom_id(custom_id) -> tuple[int, int] | None:
    """create_order で埋めた custom_id "tenant_id:invoice_id" を解析する。"""
    if not custom_id or ":" not in str(custom_id):
        return None
    try:
        tid_s, iid_s = str(custom_id).split(":", 1)
        return int(tid_s), int(iid_s)
    except (ValueError, TypeError):
        return None


def _parse_invoicing_paid(resource: dict) -> tuple[int, int, str] | None:
    """INVOICING.INVOICE.PAID の resource から (tenant_id, invoice_id, PayPal Invoice ID) を取り出す。

    resource 構造は `resource.invoice.{id,detail.reference}` または `resource.{id,detail.reference}`
    の両方に防御的に対応する（PayPal の payload 差異吸収）。
    """
    if not isinstance(resource, dict):
        return None
    inv_obj = resource.get("invoice") if isinstance(resource.get("invoice"), dict) else resource
    detail = inv_obj.get("detail") or {}
    reference = detail.get("reference")
    pp_invoice_id = inv_obj.get("id")
    parsed = _parse_custom_id(reference)  # "tenant_id:invoice_id"（custom_id と同形式）
    if not parsed or not pp_invoice_id:
        return None
    return parsed[0], parsed[1], pp_invoice_id


@public_router.post("/integrations/paypal/webhook", include_in_schema=False)
async def paypal_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """PayPal webhook（INVOICING.INVOICE.PAID）。署名検証→status再取得→請求書 paid＋受注 sourcing。

    ADR-101 改訂 2026-06-12: Invoicing 方式。detail.reference("tenant:invoice") でルーティング。
    """
    try:
        event = await request.json()
    except Exception:  # noqa: BLE001
        return Response(status_code=400)
    if not isinstance(event, dict) or event.get("event_type") != "INVOICING.INVOICE.PAID":
        return Response(status_code=200)  # 対象外イベントは無視

    parsed = _parse_invoicing_paid(event.get("resource") or {})
    if not parsed:
        return Response(status_code=200)  # ルーティング不能は無視（PayPal 再送防止）
    tenant_id, invoice_id, pp_invoice_id = parsed

    # creds / webhook_id は public.tenant_paypal_config（テナント文脈不要）
    creds = await paypal_payments.get_credentials(db, tenant_id)
    webhook_id = await paypal_payments.get_webhook_id(db, tenant_id)
    if not creds or not webhook_id:
        return Response(status_code=200)  # 未設定テナントは無視

    h = request.headers
    try:
        valid = await run_in_threadpool(
            paypal_payments.verify_webhook,
            creds["environment"], creds["client_id"], creds["client_secret"], webhook_id,
            h.get("paypal-transmission-id", ""), h.get("paypal-transmission-time", ""),
            h.get("paypal-cert-url", ""), h.get("paypal-auth-algo", ""),
            h.get("paypal-transmission-sig", ""), event,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[paypal] webhook 署名検証不能: %s", e)
        return Response(status_code=500)  # 検証不能 → PayPal 再送
    if not valid:
        return Response(status_code=400)  # 不正署名

    await set_tenant_context(db, tenant_id)
    try:
        inv = await db.execute(
            text("SELECT id, status, paypal_order_id FROM invoices WHERE id = :id"),
            {"id": invoice_id},
        )
        row = inv.mappings().first()
        if not row or row["paypal_order_id"] != pp_invoice_id:
            return Response(status_code=200)  # 不一致は無視
        if row["status"] == "paid":
            return Response(status_code=200)  # 冪等（既に確定）
        if row["status"] not in ("issued", "overdue"):
            return Response(status_code=200)

        # webhook body だけを信用せず、PayPal に status を再確認（防御）。PAID のみ確定。
        result = await run_in_threadpool(
            paypal_payments.get_invoice_status,
            creds["environment"], creds["client_id"], creds["client_secret"], pp_invoice_id,
        )
        if result.get("paid"):
            await db.execute(
                text("UPDATE invoices SET status='paid', paid_at=NOW(), payment_fee=:fee, "
                     "payment_method='paypal', updated_at=NOW() "
                     "WHERE id=:id AND status IN ('issued','overdue')"),
                {"id": invoice_id, "fee": result.get("fee")},
            )
            # ADR-104: 紐づく受注を 支払い待ち→仕入れ中 へ自動遷移
            await db.execute(
                text("UPDATE orders SET status='sourcing', paid_at=NOW(), updated_at=NOW() "
                     "WHERE invoice_id=:iid AND status='awaiting_payment'"),
                {"iid": invoice_id},
            )
            await db.commit()
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        logger.error("[paypal] webhook 処理失敗: %s", e)
        return Response(status_code=500)
    finally:
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5

    return Response(status_code=200)
