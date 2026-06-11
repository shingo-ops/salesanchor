from __future__ import annotations

"""PayPal 決済連携サービス（テナント別認証情報・Model A）。

各テナントが自社の PayPal アプリの API 認証情報（Client ID / Secret）を画面から入力・保存し、
「認証が通るか（＝連携の最初の疎通）」を確認するためのサービス。
決済作成（Orders API）等の実機能は別途（Phase B）。

認証情報はテナント別に DB（public.tenant_paypal_config）へ Fernet 暗号化して保存
（tenant_carrier_credentials と同方針）。各テナントの顧客の支払いはそのテナントの PayPal に入金（Model A）。
将来 Model B（Multiparty / Connect with PayPal）へはこのテーブル/サービスを基点に拡張できる。

接続テスト = OAuth2 client_credentials でアクセストークン取得（Client ID/Secret が正しいか確認）。
環境(env): "sandbox"（練習用）/ "live"（本番）。

変更履歴:
  2026-06-10: 初版（テナント別・接続テストページ・Model A）
"""

import base64
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

import httpx
from sqlalchemy import text

from app.services import encryption

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0

# env -> base URL
_BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}


def _norm_env(env: Optional[str]) -> str:
    return "live" if env == "live" else "sandbox"


# ---------------------------------------------------------------------------
# DB CRUD（テナント別・Fernet 暗号化）
# ---------------------------------------------------------------------------


async def get_status(db, tenant_id: int) -> dict:
    """設定状況を返す（シークレットは返さない）。{"configured", "environment"}。"""
    row = await db.execute(
        text("SELECT environment FROM tenant_paypal_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    rec = row.first()
    if rec is None:
        return {"configured": False, "environment": "sandbox"}
    return {"configured": True, "environment": rec[0] or "sandbox"}


async def get_credentials(db, tenant_id: int) -> Optional[dict]:
    """復号した認証情報を返す（未設定なら None）。{"client_id", "client_secret", "environment"}。"""
    row = await db.execute(
        text(
            "SELECT client_id_encrypted, client_secret_encrypted, environment"
            " FROM tenant_paypal_config WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    rec = row.first()
    if rec is None:
        return None
    return {
        "client_id": encryption.decrypt(rec[0]),
        "client_secret": encryption.decrypt(rec[1]),
        "environment": rec[2] or "sandbox",
    }


async def save_credentials(
    db,
    tenant_id: int,
    client_id: str,
    client_secret: str,
    environment: str,
    user_id: int,
) -> None:
    """認証情報を暗号化して upsert する。"""
    await db.execute(
        text(
            """
            INSERT INTO tenant_paypal_config
              (tenant_id, client_id_encrypted, client_secret_encrypted,
               environment, updated_by_user_id, created_at, updated_at)
            VALUES (:tid, :cid, :csec, :env, :uid, NOW(), NOW())
            ON CONFLICT (tenant_id) DO UPDATE SET
              client_id_encrypted     = EXCLUDED.client_id_encrypted,
              client_secret_encrypted = EXCLUDED.client_secret_encrypted,
              environment             = EXCLUDED.environment,
              updated_by_user_id      = EXCLUDED.updated_by_user_id,
              updated_at              = NOW()
            """
        ),
        {
            "tid": tenant_id,
            "cid": encryption.encrypt(client_id),
            "csec": encryption.encrypt(client_secret),
            "env": _norm_env(environment),
            "uid": user_id,
        },
    )
    await db.commit()


async def delete_credentials(db, tenant_id: int) -> None:
    await db.execute(
        text("DELETE FROM tenant_paypal_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
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


def test_connection(env: str, client_id: str, client_secret: str) -> dict:
    """PayPal の OAuth2 client_credentials でアクセストークン取得を試す。

    Returns: {"ok": bool, "status_code": int | None, "message": str}
    ※ シークレット値・例外スタックはクライアントに返さない（status_code と定型メッセージのみ）。
    """
    base = _BASE_URLS[_norm_env(env)]
    token = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        resp = httpx.post(
            f"{base}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning("[paypal] 接続テスト通信エラー: %s", e)
        return {"ok": False, "status_code": None, "message": "通信エラー（ネットワーク/URL を確認）"}

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


# ---------------------------------------------------------------------------
# Orders API（決済リンク発行・入金確認）— ADR-101 §6 PayPal mode1
# httpx 同期・呼び出し側で run_in_threadpool 推奨
# ---------------------------------------------------------------------------

# PayPal のゼロ小数通貨（value は整数文字列で送る。JPY に "1000.00" を送ると 400）
_ZERO_DECIMAL_CCY = {"JPY", "HUF", "TWD"}


def _fmt_amount(amount, currency: str) -> str:
    """PayPal の amount.value 文字列を通貨の小数桁に合わせて整形する。"""
    dec = Decimal(str(amount))
    if (currency or "").upper() in _ZERO_DECIMAL_CCY:
        return str(int(dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
    return str(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _get_token(env: str, client_id: str, client_secret: str) -> Optional[str]:
    """OAuth2 client_credentials でアクセストークンを取得（失敗時 None）。"""
    base = _BASE_URLS[_norm_env(env)]
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        resp = httpx.post(
            f"{base}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning("[paypal] token 取得通信エラー: %s", e)
        return None
    if resp.status_code == 200:
        return _access_token(resp)
    logger.warning("[paypal] token 取得失敗: HTTP %s", resp.status_code)
    return None


def create_order(
    env: str,
    client_id: str,
    client_secret: str,
    amount,
    currency: str,
    invoice_number: Optional[str],
    return_url: str,
    cancel_url: str,
) -> dict:
    """請求書金額で PayPal 注文を作成し、顧客が支払う承認 URL を返す。

    Returns: {"ok", "order_id", "approval_url", "status_code", "message"}
    """
    base = _BASE_URLS[_norm_env(env)]
    token = _get_token(env, client_id, client_secret)
    if not token:
        return {
            "ok": False, "order_id": None, "approval_url": None,
            "status_code": 401, "message": "PayPal 認証に失敗しました（認証情報を確認）",
        }

    purchase_unit = {
        "amount": {
            "currency_code": (currency or "JPY").upper(),
            "value": _fmt_amount(amount, currency),
        },
    }
    if invoice_number:
        purchase_unit["invoice_id"] = invoice_number

    body = {
        "intent": "CAPTURE",
        "purchase_units": [purchase_unit],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "shipping_preference": "NO_SHIPPING",
            "user_action": "PAY_NOW",
        },
    }
    try:
        resp = httpx.post(
            f"{base}/v2/checkout/orders",
            json=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning("[paypal] 注文作成通信エラー: %s", e)
        return {
            "ok": False, "order_id": None, "approval_url": None,
            "status_code": None, "message": "通信エラー（ネットワーク/URL を確認）",
        }

    if resp.status_code in (200, 201):
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            data = {}
        order_id = data.get("id")
        approval = next(
            (link.get("href") for link in data.get("links", []) if link.get("rel") == "approve"),
            None,
        )
        if order_id and approval:
            return {
                "ok": True, "order_id": order_id, "approval_url": approval,
                "status_code": resp.status_code, "message": "決済リンクを発行しました",
            }
    return {
        "ok": False, "order_id": None, "approval_url": None,
        "status_code": resp.status_code,
        "message": f"PayPal 注文作成に失敗（HTTP {resp.status_code}）",
    }


def _extract_fee(data: dict) -> Optional[str]:
    """capture レスポンスから PayPal 手数料（paypal_fee.value）を取り出す。"""
    try:
        cap = data["purchase_units"][0]["payments"]["captures"][0]
        return cap.get("seller_receivable_breakdown", {}).get("paypal_fee", {}).get("value")
    except (KeyError, IndexError, TypeError):
        return None


def capture_order(env: str, client_id: str, client_secret: str, order_id: str) -> dict:
    """承認済みの PayPal 注文を capture（確定）する。

    Returns: {"ok", "captured", "fee", "status_code", "message"}
    captured=True は status==COMPLETED。未承認(422)は captured=False。
    """
    base = _BASE_URLS[_norm_env(env)]
    token = _get_token(env, client_id, client_secret)
    if not token:
        return {
            "ok": False, "captured": False, "fee": None,
            "status_code": 401, "message": "PayPal 認証に失敗しました（認証情報を確認）",
        }
    try:
        resp = httpx.post(
            f"{base}/v2/checkout/orders/{order_id}/capture",
            json={},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning("[paypal] capture 通信エラー: %s", e)
        return {
            "ok": False, "captured": False, "fee": None,
            "status_code": None, "message": "通信エラー（ネットワーク/URL を確認）",
        }

    if resp.status_code in (200, 201):
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            data = {}
        if data.get("status") == "COMPLETED":
            return {
                "ok": True, "captured": True, "fee": _extract_fee(data),
                "status_code": resp.status_code, "message": "入金を確認しました",
            }
        return {
            "ok": True, "captured": False, "fee": None,
            "status_code": resp.status_code,
            "message": "まだ入金が確認できません（顧客の支払い完了待ち）",
        }
    if resp.status_code == 422:  # ORDER_NOT_APPROVED 等
        return {
            "ok": True, "captured": False, "fee": None,
            "status_code": 422, "message": "まだ顧客が支払いを承認していません",
        }
    return {
        "ok": False, "captured": False, "fee": None,
        "status_code": resp.status_code,
        "message": f"PayPal 入金確認に失敗（HTTP {resp.status_code}）",
    }


__all__ = [
    "get_status",
    "get_credentials",
    "save_credentials",
    "delete_credentials",
    "test_connection",
    "create_order",
    "capture_order",
]
