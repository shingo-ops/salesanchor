from __future__ import annotations

"""配送キャリア（FedEx / DHL / UPS）接続テストサービス（テナント別認証情報）。

各テナントが自社の配送キャリア API 認証情報を画面から入力・保存し、
「認証が通るか（＝連携の最初の疎通）」を確認するためのサービス。
送料見積・ラベル発行・追跡などの実機能は別途（ADR-021 のキャリアアダプタ層で個別追加）。

認証情報はテナント別に DB（public.tenant_carrier_credentials）へ Fernet 暗号化して保存
（tenant_google_drive_config と同方針）。アプリ共通 env シークレットは使わない。
  FedEx/UPS: Client ID / Client Secret（OAuth2 client_credentials）
  DHL:       API Key / API Secret（MyDHL API: per-request Basic 認証）

環境(env): "sandbox"（練習用）/ "production"（本番）。

注意: 各社 API の細部（特に DHL の疎通判定）は実認証情報での検証が未了。
      接続情報入力後に実機で確認・微調整する前提（接続テストページの初版）。

変更履歴:
  2026-06-08: 初版（テナント別・接続テストページ）
"""

import base64
import logging
from typing import Optional

import httpx
from sqlalchemy import text

from app.services import encryption

logger = logging.getLogger(__name__)

CARRIERS = ("fedex", "dhl", "ups")
_TIMEOUT = 15.0

# carrier -> {env -> base URL}
_BASE_URLS = {
    "fedex": {
        "sandbox": "https://apis-sandbox.fedex.com",
        "production": "https://apis.fedex.com",
    },
    "ups": {
        "sandbox": "https://wwwcie.ups.com",
        "production": "https://onlinetools.ups.com",
    },
    "dhl": {
        "sandbox": "https://express.api.dhl.com/mydhlapi/test",
        "production": "https://express.api.dhl.com/mydhlapi",
    },
}


def is_valid_carrier(carrier: str) -> bool:
    return carrier in CARRIERS


def _norm_env(env: Optional[str]) -> str:
    return "production" if env == "production" else "sandbox"


# ---------------------------------------------------------------------------
# DB CRUD（テナント別・Fernet 暗号化）
# ---------------------------------------------------------------------------


async def get_status(db, tenant_id: int, carrier: str, environment: str = "production") -> dict:
    """設定状況とフィールド別登録ヒントを返す（シークレット平文は返さない）。

    Args:
        environment: "production" または "sandbox"（ADR-129: 環境別レコード対応）

    Returns:
        configured: bool
        environment: str
        client_id_hint: str | None  -- 先頭4桁+末尾4桁のヒント（例: l79e...ec3d）
        secret_configured: bool     -- シークレット登録済みか
        account_number_hint: str | None  -- 末尾3桁マスク（例: ******011）
    """
    row = await db.execute(
        text(
            "SELECT client_id_encrypted, environment, account_number_encrypted,"
            "       last_tested_at, last_test_ok, last_test_message"
            " FROM tenant_carrier_credentials"
            " WHERE tenant_id = :tid AND carrier = :c AND environment = :env"
        ),
        {"tid": tenant_id, "c": carrier, "env": _norm_env(environment)},
    )
    rec = row.first()
    if rec is None:
        return {
            "configured": False,
            "environment": "production",
            "client_id_hint": None,
            "secret_configured": False,
            "account_number_hint": None,
            "last_tested_at": None,
            "last_test_ok": None,
            "last_test_message": None,
        }
    client_id = encryption.decrypt(rec[0])
    account_number: Optional[str] = (
        encryption.decrypt(rec[2]) if rec[2] is not None else None
    )
    account_number_hint: Optional[str] = None
    if account_number:
        suffix = account_number[-3:] if len(account_number) >= 3 else account_number
        account_number_hint = f"******{suffix}"
    return {
        "configured": True,
        "environment": rec[1] or "production",
        "client_id_hint": f"{client_id[:4]}...{client_id[-4:]}" if len(client_id) >= 8 else client_id,
        "secret_configured": True,
        "account_number_hint": account_number_hint,
        "last_tested_at": rec[3],
        "last_test_ok": rec[4],
        "last_test_message": rec[5],
    }


async def get_credentials(db, tenant_id: int, carrier: str, environment: str = "production") -> Optional[dict]:
    """復号した認証情報を返す（未設定なら None）。

    Args:
        environment: "production" または "sandbox"（ADR-129: 環境別レコード対応）。
                     デフォルト "production" — 既存の Ship/Pickup ルーターへの後方互換を保つ。

    Returns:
        {
            "client_id": str,
            "client_secret": str,
            "environment": str,
            "account_number": str | None,  # ADR-125 D2 追加（NULL = 未設定）
        }
    """
    row = await db.execute(
        text(
            "SELECT client_id_encrypted, client_secret_encrypted, environment,"
            "       account_number_encrypted"
            " FROM tenant_carrier_credentials"
            " WHERE tenant_id = :tid AND carrier = :c AND environment = :env"
        ),
        {"tid": tenant_id, "c": carrier, "env": _norm_env(environment)},
    )
    rec = row.first()
    if rec is None:
        return None
    account_number: Optional[str] = (
        encryption.decrypt(rec[3]) if rec[3] is not None else None
    )
    return {
        "client_id": encryption.decrypt(rec[0]),
        "client_secret": encryption.decrypt(rec[1]),
        "environment": rec[2] or "production",  # NULL 安全フォールバック（ADR-125: 既存行は production）
        "account_number": account_number,
    }


async def save_credentials(
    db,
    tenant_id: int,
    carrier: str,
    client_id: str,
    client_secret: str,
    environment: str,
    user_id: int,
    account_number: Optional[str] = None,
) -> None:
    """認証情報を暗号化して upsert する。account_number は Optional（未入力時は変更なし）。"""
    enc_account: Optional[str] = encryption.encrypt(account_number) if account_number else None
    await db.execute(
        text(
            """
            INSERT INTO tenant_carrier_credentials
              (tenant_id, carrier, client_id_encrypted, client_secret_encrypted,
               environment, account_number_encrypted, updated_by_user_id, created_at, updated_at)
            VALUES (:tid, :c, :cid, :csec, :env, :acct, :uid, NOW(), NOW())
            ON CONFLICT (tenant_id, carrier, environment) DO UPDATE SET
              client_id_encrypted      = EXCLUDED.client_id_encrypted,
              client_secret_encrypted  = EXCLUDED.client_secret_encrypted,
              environment              = EXCLUDED.environment,
              account_number_encrypted = COALESCE(EXCLUDED.account_number_encrypted,
                                                  tenant_carrier_credentials.account_number_encrypted),
              updated_by_user_id       = EXCLUDED.updated_by_user_id,
              updated_at               = NOW()
            """
        ),
        {
            "tid": tenant_id,
            "c": carrier,
            "cid": encryption.encrypt(client_id),
            "csec": encryption.encrypt(client_secret),
            "env": _norm_env(environment),
            "acct": enc_account,
            "uid": user_id,
        },
    )
    await db.commit()


async def delete_credentials(db, tenant_id: int, carrier: str, environment: str = "production") -> None:
    """指定環境の認証情報を削除する（ADR-129: 環境別レコード対応）。"""
    await db.execute(
        text(
            "DELETE FROM tenant_carrier_credentials"
            " WHERE tenant_id = :tid AND carrier = :c AND environment = :env"
        ),
        {"tid": tenant_id, "c": carrier, "env": _norm_env(environment)},
    )
    await db.commit()


_MAX_MESSAGE_LEN = 500


async def save_test_result(
    db,
    tenant_id: int,
    carrier: str,
    environment: str,
    ok: bool,
    message: str,
) -> None:
    """接続テスト結果を tenant_carrier_credentials に保存する（A4）。

    UPDATE のみ（INSERT しない）。credentials が存在しない場合は何もしない。
    API key / secret / account number の平文を message に含めないこと。
    """
    await db.execute(
        text(
            "UPDATE tenant_carrier_credentials"
            " SET last_tested_at = NOW(),"
            "     last_test_ok = :ok,"
            "     last_test_message = :msg"
            " WHERE tenant_id = :tid AND carrier = :c AND environment = :env"
        ),
        {
            "tid": tenant_id,
            "c": carrier,
            "env": _norm_env(environment),
            "ok": ok,
            "msg": message[:_MAX_MESSAGE_LEN],
        },
    )
    await db.commit()


# ---------------------------------------------------------------------------
# 接続テスト（httpx 同期・呼び出し側で run_in_threadpool 推奨）
# ---------------------------------------------------------------------------


def _access_token(resp: httpx.Response) -> Optional[str]:
    try:
        return resp.json().get("access_token")
    except Exception:  # noqa: BLE001
        return None


def test_connection(carrier: str, env: str, client_id: str, client_secret: str) -> dict:
    """各社の認証が通るか確認する。

    Returns: {"ok": bool, "status_code": int | None, "message": str}
    ※ シークレット値・例外スタックはクライアントに返さない（status_code と定型メッセージのみ）。
    """
    base = _BASE_URLS[carrier][_norm_env(env)]
    try:
        if carrier == "fedex":
            return _test_oauth_token(f"{base}/oauth/token", client_id, client_secret, use_basic=False)
        if carrier == "ups":
            return _test_oauth_token(f"{base}/security/v1/oauth/token", client_id, client_secret, use_basic=True)
        return _test_dhl(base, client_id, client_secret)
    except httpx.HTTPError as e:
        logger.warning("[carriers] %s 接続テスト通信エラー: %s", carrier, e)
        return {"ok": False, "status_code": None, "message": "通信エラー（ネットワーク/URL を確認）"}


def _test_oauth_token(url: str, cid: str, csec: str, *, use_basic: bool) -> dict:
    """OAuth2 client_credentials でトークン取得を試す（FedEx / UPS 共通）。"""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    if use_basic:
        token = base64.b64encode(f"{cid}:{csec}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    else:
        data["client_id"] = cid
        data["client_secret"] = csec

    resp = httpx.post(url, data=data, headers=headers, timeout=_TIMEOUT)
    if resp.status_code == 200 and _access_token(resp):
        return {"ok": True, "status_code": 200, "message": "認証成功（トークン取得）"}
    if resp.status_code in (401, 403):
        return {
            "ok": False,
            "status_code": resp.status_code,
            "message": "認証情報が正しくありません",
        }
    return {
        "ok": False,
        "status_code": resp.status_code,
        "message": f"想定外の応答（HTTP {resp.status_code}）",
    }


def _test_dhl(base: str, key: str, secret: str) -> dict:
    """MyDHL API はトークン無しの per-request Basic 認証。軽量な認証付きリクエストを投げ、
    401/403 = 認証NG、それ以外（2xx / 400 / 422 等・認証は通過）= 疎通OK と判定する。
    ※ エンドポイント/判定は実認証情報での要検証。"""
    token = base64.b64encode(f"{key}:{secret}".encode()).decode()
    resp = httpx.get(
        f"{base}/rates",
        headers={"Authorization": f"Basic {token}"},
        timeout=_TIMEOUT,
    )
    if resp.status_code in (401, 403):
        return {
            "ok": False,
            "status_code": resp.status_code,
            "message": "認証情報が正しくありません",
        }
    if resp.status_code < 500:
        return {"ok": True, "status_code": resp.status_code, "message": "認証成功（API疎通）"}
    return {
        "ok": False,
        "status_code": resp.status_code,
        "message": f"想定外の応答（HTTP {resp.status_code}）",
    }


__all__ = [
    "CARRIERS",
    "is_valid_carrier",
    "get_status",
    "get_credentials",
    "save_credentials",
    "delete_credentials",
    "save_test_result",
    "test_connection",
]
