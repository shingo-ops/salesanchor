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
    custom_id: Optional[str] = None,
) -> dict:
    """請求書金額で PayPal 注文を作成し、顧客が支払う承認 URL を返す。

    custom_id は webhook ルーティング用（"tenant_id:invoice_id"）。
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
    if custom_id:
        purchase_unit["custom_id"] = custom_id

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
    "make_return_token",
    "parse_return_token",
    "register_webhook",
    "verify_webhook",
    "get_webhook_id",
    "save_webhook_id",
    "create_and_send_invoice",
    "get_invoice_status",
]


# ---------------------------------------------------------------------------
# 戻りURL用の改ざん防止トークン（Fernet 流用）— Increment 2
# ---------------------------------------------------------------------------


def make_return_token(tenant_id: int, invoice_id: int) -> str:
    """戻りURLに載せる改ざん防止トークン（Fernet 暗号＝URLセーフ・改ざん不可）。"""
    return encryption.encrypt(f"{tenant_id}:{invoice_id}")


def parse_return_token(token: str) -> Optional[tuple[int, int]]:
    """戻りトークンを検証し (tenant_id, invoice_id) を返す。改ざん/不正は None。"""
    try:
        raw = encryption.decrypt(token)
        tid_s, iid_s = raw.split(":", 1)
        return int(tid_s), int(iid_s)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Webhook（テナント毎に自動登録＋署名検証）— Increment 2.5
# ---------------------------------------------------------------------------


async def get_webhook_id(db, tenant_id: int) -> Optional[str]:
    """テナントの保存済 webhook_id を返す（未登録なら None）。"""
    row = await db.execute(
        text("SELECT webhook_id FROM tenant_paypal_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    rec = row.first()
    return rec[0] if rec and rec[0] else None


async def save_webhook_id(db, tenant_id: int, webhook_id: str) -> None:
    """webhook_id を保存する。"""
    await db.execute(
        text("UPDATE tenant_paypal_config SET webhook_id = :wid, updated_at = NOW() "
             "WHERE tenant_id = :tid"),
        {"tid": tenant_id, "wid": webhook_id},
    )
    await db.commit()


def _find_existing_webhook(base: str, headers: dict, webhook_url: str) -> Optional[str]:
    """既存 webhook 一覧から URL 一致の id を探す。"""
    try:
        resp = httpx.get(f"{base}/v1/notifications/webhooks", headers=headers, timeout=_TIMEOUT)
        if resp.status_code == 200:
            for wh in resp.json().get("webhooks", []):
                if wh.get("url") == webhook_url:
                    return wh.get("id")
    except Exception:  # noqa: BLE001
        return None
    return None


def register_webhook(env: str, client_id: str, client_secret: str, webhook_url: str) -> dict:
    """テナントの PayPal アプリに webhook を作成し webhook_id を返す（INVOICING.INVOICE.PAID 購読）。

    既存 URL（既登録）は既存 webhook の id を返す。Returns: {"ok", "webhook_id", "message"}。
    """
    base = _BASE_URLS[_norm_env(env)]
    token = _get_token(env, client_id, client_secret)
    if not token:
        return {"ok": False, "webhook_id": None, "message": "PayPal 認証に失敗しました"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"url": webhook_url, "event_types": [{"name": "INVOICING.INVOICE.PAID"}]}
    try:
        resp = httpx.post(
            f"{base}/v1/notifications/webhooks", json=body, headers=headers, timeout=_TIMEOUT
        )
    except httpx.HTTPError as e:
        logger.warning("[paypal] webhook 登録通信エラー: %s", e)
        return {"ok": False, "webhook_id": None, "message": "通信エラー"}

    if resp.status_code in (200, 201):
        try:
            wid = resp.json().get("id")
        except Exception:  # noqa: BLE001
            wid = None
        if wid:
            return {"ok": True, "webhook_id": wid, "message": "webhook を登録しました"}
    if resp.status_code in (400, 409):  # WEBHOOK_URL_ALREADY_EXISTS 等
        existing = _find_existing_webhook(base, headers, webhook_url)
        if existing:
            return {"ok": True, "webhook_id": existing, "message": "既存 webhook を再利用しました"}
    return {"ok": False, "webhook_id": None, "message": f"webhook 登録失敗（HTTP {resp.status_code}）"}


def verify_webhook(
    env: str,
    client_id: str,
    client_secret: str,
    webhook_id: str,
    transmission_id: str,
    transmission_time: str,
    cert_url: str,
    auth_algo: str,
    transmission_sig: str,
    webhook_event: dict,
) -> bool:
    """受信 webhook の署名を verify-webhook-signature API で検証（SUCCESS で True）。

    通信エラー（検証不能）は例外を送出 → 呼び出し側で 500（PayPal 再送）にする。
    """
    base = _BASE_URLS[_norm_env(env)]
    token = _get_token(env, client_id, client_secret)
    if not token:
        return False
    body = {
        "auth_algo": auth_algo,
        "cert_url": cert_url,
        "transmission_id": transmission_id,
        "transmission_sig": transmission_sig,
        "transmission_time": transmission_time,
        "webhook_id": webhook_id,
        "webhook_event": webhook_event,
    }
    resp = httpx.post(
        f"{base}/v1/notifications/verify-webhook-signature",
        json=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=_TIMEOUT,
    )
    if resp.status_code == 200:
        try:
            return resp.json().get("verification_status") == "SUCCESS"
        except Exception:  # noqa: BLE001
            return False
    return False


# ---------------------------------------------------------------------------
# Invoicing API（PayPal が請求書をメール送付＋ホスト決済）— ADR-101 改訂 2026-06-12
# ---------------------------------------------------------------------------


def _fetch_recipient_view_url(base: str, headers: dict, pp_invoice_id: str, send_resp) -> Optional[str]:
    """send レスポンス or GET から顧客の支払いページ URL(recipient_view_url)を取り出す。"""
    try:
        for link in send_resp.json().get("links", []):
            if link.get("rel") in ("recipient-view", "payer-view"):
                return link.get("href")
    except Exception:  # noqa: BLE001
        pass
    try:
        g = httpx.get(
            f"{base}/v2/invoicing/invoices/{pp_invoice_id}",
            headers={"Authorization": headers["Authorization"]},
            timeout=_TIMEOUT,
        )
        if g.status_code == 200:
            return g.json().get("detail", {}).get("metadata", {}).get("recipient_view_url")
    except Exception:  # noqa: BLE001
        return None
    return None


def create_and_send_invoice(
    env: str,
    client_id: str,
    client_secret: str,
    *,
    invoice_number: str,
    currency: str,
    amount,
    recipient_email: str,
    reference: str,
    item_name: str = "Sales Anchor Invoice",
) -> dict:
    """PayPal Invoice を作成・送付し、顧客が支払うホストURL(recipient_view_url)を返す。

    invoicer は接続済アカウントの事業者情報が使われるため省略。
    Returns: {"ok", "paypal_invoice_id", "recipient_view_url", "status_code", "message"}
    """
    base = _BASE_URLS[_norm_env(env)]
    token = _get_token(env, client_id, client_secret)
    if not token:
        return {"ok": False, "paypal_invoice_id": None, "recipient_view_url": None,
                "status_code": 401, "message": "PayPal 認証に失敗しました（認証情報を確認）"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    ccy = (currency or "JPY").upper()
    body = {
        "detail": {
            "currency_code": ccy,
            "invoice_number": invoice_number,
            "reference": reference,
        },
        "primary_recipients": [
            {"billing_info": {"email_address": recipient_email}}
        ],
        "items": [
            {
                "name": item_name,
                "quantity": "1",
                "unit_amount": {"currency_code": ccy, "value": _fmt_amount(amount, currency)},
            }
        ],
    }
    # 1. 作成（draft）
    try:
        resp = httpx.post(f"{base}/v2/invoicing/invoices", json=body, headers=headers, timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        logger.warning("[paypal] invoice 作成通信エラー: %s", e)
        return {"ok": False, "paypal_invoice_id": None, "recipient_view_url": None,
                "status_code": None, "message": "通信エラー（ネットワーク/URL を確認）"}
    if resp.status_code not in (200, 201):
        return {"ok": False, "paypal_invoice_id": None, "recipient_view_url": None,
                "status_code": resp.status_code,
                "message": f"PayPal 請求書作成に失敗（HTTP {resp.status_code}）"}
    try:
        pp_invoice_id = resp.json().get("id")
    except Exception:  # noqa: BLE001
        pp_invoice_id = None
    if not pp_invoice_id:
        return {"ok": False, "paypal_invoice_id": None, "recipient_view_url": None,
                "status_code": resp.status_code, "message": "PayPal 請求書 ID を取得できませんでした"}

    # 2. 送付（顧客にメール＋決済リンク）
    try:
        send_resp = httpx.post(
            f"{base}/v2/invoicing/invoices/{pp_invoice_id}/send",
            json={"send_to_recipient": True},
            headers=headers, timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning("[paypal] invoice 送付通信エラー: %s", e)
        return {"ok": False, "paypal_invoice_id": pp_invoice_id, "recipient_view_url": None,
                "status_code": None, "message": "通信エラー（送付）"}
    if send_resp.status_code not in (200, 201, 202):
        return {"ok": False, "paypal_invoice_id": pp_invoice_id, "recipient_view_url": None,
                "status_code": send_resp.status_code,
                "message": f"PayPal 請求書送付に失敗（HTTP {send_resp.status_code}）"}

    recipient_view_url = _fetch_recipient_view_url(base, headers, pp_invoice_id, send_resp)
    return {"ok": True, "paypal_invoice_id": pp_invoice_id,
            "recipient_view_url": recipient_view_url,
            "status_code": send_resp.status_code, "message": "PayPal 請求書を送付しました"}


def get_invoice_status(env: str, client_id: str, client_secret: str, paypal_invoice_id: str) -> dict:
    """PayPal Invoice のステータスを取得（PAID なら paid=True）。

    Returns: {"ok", "status", "paid", "fee", "status_code", "message"}
    """
    base = _BASE_URLS[_norm_env(env)]
    token = _get_token(env, client_id, client_secret)
    if not token:
        return {"ok": False, "status": None, "paid": False, "fee": None,
                "status_code": 401, "message": "PayPal 認証に失敗しました"}
    try:
        resp = httpx.get(
            f"{base}/v2/invoicing/invoices/{paypal_invoice_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning("[paypal] invoice status 通信エラー: %s", e)
        return {"ok": False, "status": None, "paid": False, "fee": None,
                "status_code": None, "message": "通信エラー"}
    if resp.status_code != 200:
        return {"ok": False, "status": None, "paid": False, "fee": None,
                "status_code": resp.status_code,
                "message": f"PayPal 請求書取得に失敗（HTTP {resp.status_code}）"}
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        data = {}
    st = data.get("status")
    fee = None
    try:
        fee = (data.get("payments", {}).get("transactions", [{}])[0]
               .get("paypal_fee", {}).get("value"))
    except (KeyError, IndexError, TypeError):
        fee = None
    return {"ok": True, "status": st, "paid": st == "PAID", "fee": fee,
            "status_code": 200, "message": "OK"}
