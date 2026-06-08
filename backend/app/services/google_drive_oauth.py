from __future__ import annotations

"""
Google Drive OAuth 2.0 + Drive API サービス（ユーザー委任方式）。

担当範囲:
  - OAuth 認証 URL 生成（state 発行 → Google 同意画面 URL 返却）
  - code → access/refresh token 交換（OAuth callback）
  - アクセストークン自動更新（1時間失効 → refresh_token で更新）
  - テナント接続情報の DB 読み書き（Fernet 暗号化）
  - 接続アカウントのドライブへ PDF をアップロード

設計判断（google_calendar.py に準拠）:
  - テナント共通接続: 管理者が1回接続 → public.tenant_google_drive_config に保存
    → 全スタッフの操作で同一アカウントのドライブに保存される
  - サービスアカウント方式と違い、保存先は「接続した人のドライブ」なので
    Google Workspace / 共有ドライブが不要（ユーザー自身の容量を使う）
  - スコープは drive.file（非機密）: アプリが作成/開いたファイルのみアクセス。
    制限付き(restricted)スコープ審査・CASA を回避できる。
  - OAuth State は `google_drive_oauth_state:` プレフィックスで Redis に保存
  - トークンは METADATA_FERNET_KEY (shared Fernet key) で暗号化保存

環境変数:
  GOOGLE_DRIVE_CLIENT_ID        - OAuth 2.0 クライアント ID（カレンダーと同一クライアント可）
  GOOGLE_DRIVE_CLIENT_SECRET    - OAuth 2.0 クライアントシークレット
  GOOGLE_DRIVE_REDIRECT_URI     - callback URL（Google Console に登録済みであること）
  METADATA_FERNET_KEY           - 暗号化鍵（Meta / Calendar と共通）

変更履歴:
  2026-06-06: 初版（API連携 Googleドライブ OAuth 保存）
"""

import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Optional

from app.cache import get_redis
from app.services import encryption

logger = logging.getLogger(__name__)

# drive.file = アプリが作成/開いたファイルのみ（非機密スコープ）
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_REDIS_KEY_PREFIX = "google_drive_oauth_state:"
_STATE_TTL_SECONDS = 600  # 10 分

# Drive のフォルダ/共有ドライブ URL から ID を取り出す
_FOLDER_URL_RE = re.compile(r"/folders/([a-zA-Z0-9_-]+)")
_BARE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{10,}$")


# ---------------------------------------------------------------------------
# 環境変数ヘルパー
# ---------------------------------------------------------------------------


def _get_client_id() -> str:
    v = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "")
    if not v:
        raise RuntimeError("GOOGLE_DRIVE_CLIENT_ID が未設定です")
    return v


def _get_client_secret() -> str:
    v = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "")
    if not v:
        raise RuntimeError("GOOGLE_DRIVE_CLIENT_SECRET が未設定です")
    return v


def _get_redirect_uri() -> str:
    v = os.getenv("GOOGLE_DRIVE_REDIRECT_URI", "")
    if not v:
        raise RuntimeError("GOOGLE_DRIVE_REDIRECT_URI が未設定です")
    return v


def is_oauth_configured() -> bool:
    """OAuth クライアントの環境変数が揃っているか（サーバー設定の有無）。"""
    return bool(
        os.getenv("GOOGLE_DRIVE_CLIENT_ID")
        and os.getenv("GOOGLE_DRIVE_CLIENT_SECRET")
        and os.getenv("GOOGLE_DRIVE_REDIRECT_URI")
    )


# ---------------------------------------------------------------------------
# URL → フォルダ ID
# ---------------------------------------------------------------------------


def extract_folder_id(url_or_id: str) -> Optional[str]:
    """ドライブのフォルダ URL または ID から ID を抽出する。空なら None。"""
    s = (url_or_id or "").strip()
    if not s:
        return None
    m = _FOLDER_URL_RE.search(s)
    if m:
        return m.group(1)
    if _BARE_ID_RE.match(s):
        return s
    return None


# ---------------------------------------------------------------------------
# OAuth State（CSRF 防止）
# ---------------------------------------------------------------------------


async def issue_state(tenant_id: int, user_id: int) -> str:
    """CSRF 防止用 state を発行して Redis に保存する（10 分 TTL）。"""
    r = get_redis()
    if r is None:
        raise RuntimeError("Redis 未接続のため OAuth state を発行できません")

    state = secrets.token_urlsafe(32)
    payload = json.dumps(
        {"tenant_id": int(tenant_id), "user_id": int(user_id), "nonce": secrets.token_hex(8)},
        separators=(",", ":"),
    )
    encrypted = encryption.encrypt(payload)
    await r.setex(f"{_REDIS_KEY_PREFIX}{state}", _STATE_TTL_SECONDS, encrypted)
    return state


async def consume_state(state: str) -> Optional[dict]:
    """state を検証して payload を返す（同時に Redis から削除 → 1回限り使用）。"""
    if not state:
        return None
    r = get_redis()
    if r is None:
        raise RuntimeError("Redis 未接続のため OAuth state を検証できません")

    key = f"{_REDIS_KEY_PREFIX}{state}"
    async with r.pipeline(transaction=True) as pipe:
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()
    encrypted = results[0]
    if not encrypted:
        return None
    try:
        return json.loads(encryption.decrypt(encrypted))
    except Exception:
        logger.exception("Google Drive OAuth state の復号 / parse に失敗")
        return None


# ---------------------------------------------------------------------------
# OAuth URL 生成 / code 交換
# ---------------------------------------------------------------------------


def _flow(state: Optional[str] = None):
    from google_auth_oauthlib.flow import Flow  # type: ignore[import]

    return Flow.from_client_config(
        {
            "web": {
                "client_id": _get_client_id(),
                "client_secret": _get_client_secret(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [_get_redirect_uri()],
            }
        },
        scopes=_SCOPES,
        redirect_uri=_get_redirect_uri(),
        state=state,
    )


async def get_auth_url(tenant_id: int, user_id: int) -> str:
    """Google OAuth 同意画面 URL を生成する。"""
    state = await issue_state(tenant_id, user_id)
    flow = _flow()
    # PKCE 無効化（confidential client は client_secret で認証）。
    # autogenerate_code_verifier を False にしないと、authorization_url が
    # code_verifier を自動生成して code_challenge を送ってしまい、別インスタンスの
    # exchange_code 側で verifier を渡せず "Missing code verifier" で失敗する。
    flow.autogenerate_code_verifier = False
    flow.code_verifier = None
    auth_url, _ = flow.authorization_url(
        state=state,
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent",  # refresh_token を確実に取得するため毎回 consent を要求
    )
    return auth_url


def _fetch_account_email(creds) -> Optional[str]:
    """drive about.get で接続アカウントのメールを取得する（失敗しても None）。"""
    try:
        from googleapiclient.discovery import build  # type: ignore[import]

        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        about = service.about().get(fields="user(emailAddress)").execute()
        return (about.get("user") or {}).get("emailAddress")
    except Exception:  # noqa: BLE001
        logger.warning("[google_drive_oauth] account email の取得に失敗", exc_info=True)
        return None


async def exchange_code(code: str, state: str) -> dict:
    """認可コードを access_token / refresh_token と交換する。

    Returns: {tenant_id, user_id, access_token, refresh_token, expiry, account_email}
    Raises:
        ValueError: state が無効（CSRF or 期限切れ）
        RuntimeError: token 交換失敗 / refresh_token 取得失敗
    """
    payload = await consume_state(state)
    if payload is None:
        raise ValueError("OAuth state が無効です（CSRF または期限切れ）")

    flow = _flow(state=state)
    try:
        flow.fetch_token(code=code)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Google token 交換に失敗: {e}") from e

    creds = flow.credentials
    if not creds.refresh_token:
        raise RuntimeError(
            "refresh_token が取得できませんでした。Google アカウントのアクセス権を一度削除してから再接続してください"
        )

    expiry: Optional[datetime] = None
    if creds.expiry:
        expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry.tzinfo is None else creds.expiry

    return {
        "tenant_id": payload["tenant_id"],
        "user_id": payload["user_id"],
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": expiry,
        "account_email": _fetch_account_email(creds),
    }


# ---------------------------------------------------------------------------
# アクセストークン自動更新
# ---------------------------------------------------------------------------


def _build_credentials(access_token: str, refresh_token: str, expiry: Optional[datetime]):
    from google.oauth2.credentials import Credentials  # type: ignore[import]

    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_get_client_id(),
        client_secret=_get_client_secret(),
        scopes=_SCOPES,
        expiry=expiry,
    )


def _is_token_expired(expiry: Optional[datetime]) -> bool:
    if expiry is None:
        return True
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return now >= expiry - timedelta(minutes=5)  # 5 分前に更新


async def _refresh_if_needed(
    db,
    tenant_id: int,
    access_token_encrypted: str,
    refresh_token_encrypted: str,
    token_expiry: Optional[datetime],
) -> str:
    """アクセストークンが失効していれば refresh して DB を更新し、有効な access token を返す。"""
    access_token = encryption.decrypt(access_token_encrypted)
    refresh_token = encryption.decrypt(refresh_token_encrypted)

    if not _is_token_expired(token_expiry):
        return access_token

    from google.auth.transport.requests import Request  # type: ignore[import]
    from sqlalchemy import text

    creds = _build_credentials(access_token, refresh_token, token_expiry)
    try:
        creds.refresh(Request())
    except Exception as e:  # noqa: BLE001
        # 例外文に OAuth エラー詳細が含まれ得るため、クライアント返却用メッセージには含めない
        # （詳細は from e でスタックに保持され、ルーター側 logger.exception で記録される）
        raise RuntimeError("アクセストークンの更新に失敗しました。Google アカウントを再接続してください。") from e

    new_expiry = creds.expiry
    if new_expiry and new_expiry.tzinfo is None:
        new_expiry = new_expiry.replace(tzinfo=timezone.utc)

    await db.execute(
        text(
            "UPDATE tenant_google_drive_config"
            " SET access_token_encrypted = :at, token_expiry = :exp, updated_at = NOW()"
            " WHERE tenant_id = :tid"
        ),
        {"at": encryption.encrypt(creds.token), "exp": new_expiry, "tid": tenant_id},
    )
    await db.commit()
    return creds.token


# ---------------------------------------------------------------------------
# 接続情報の読み出し / アップロード
# ---------------------------------------------------------------------------


async def get_connection(db, tenant_id: int) -> Optional[dict]:
    """テナントの接続情報を返す（未接続なら None）。"""
    from sqlalchemy import text

    row = await db.execute(
        text("SELECT account_email, folder_id, connected_at FROM tenant_google_drive_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    record = row.first()
    if record is None:
        return None
    return {
        "account_email": record[0],
        "folder_id": record[1],
        "connected_at": record[2],
    }


async def _get_drive_service(db, tenant_id: int):
    """Drive API サービスを返す（トークン自動更新込み）。未接続なら RuntimeError。"""
    from googleapiclient.discovery import build  # type: ignore[import]
    from sqlalchemy import text

    row = await db.execute(
        text(
            "SELECT access_token_encrypted, refresh_token_encrypted, token_expiry"
            " FROM tenant_google_drive_config WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    record = row.first()
    if record is None:
        raise RuntimeError("Google ドライブが接続されていません")

    access_token = await _refresh_if_needed(db, tenant_id, record[0], record[1], record[2])
    refresh_token = encryption.decrypt(record[1])
    creds = _build_credentials(access_token, refresh_token, None)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


async def upload_pdf(
    db,
    tenant_id: int,
    pdf_bytes: bytes,
    filename: str,
    folder_id: Optional[str] = None,
) -> dict:
    """接続アカウントのドライブに PDF を保存する。folder_id 未指定ならマイドライブ直下。

    Returns: {"id", "name", "web_view_link"}
    Raises:
        RuntimeError: 未接続
        Exception: Google API 由来のエラー（呼び出し側で握る）
    """
    import io

    from googleapiclient.http import MediaIoBaseUpload  # type: ignore[import]

    service = await _get_drive_service(db, tenant_id)
    metadata: dict = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False)
    created = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )
    return {
        "id": created.get("id"),
        "name": created.get("name"),
        "web_view_link": created.get("webViewLink"),
    }


__all__ = [
    "is_oauth_configured",
    "extract_folder_id",
    "get_auth_url",
    "exchange_code",
    "get_connection",
    "upload_pdf",
]
