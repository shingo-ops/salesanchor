"""PayPal Orders API（決済リンク発行 / 入金確認）サービステスト。

httpx はモック。_get_token はトークン取得を別途モックして Orders/Capture ロジックを単離検証。
対応 AC: design.md (#1 リンク発行 / #3 capture COMPLETED→fee / #4 未承認→不確定) + 金額整形。
"""

from unittest.mock import patch

from app.services import paypal_payments as svc


def _resp(status_code, json_body=None):
    from unittest.mock import MagicMock

    r = MagicMock()
    r.status_code = status_code
    r.json = MagicMock(return_value=json_body or {})
    return r


_ORDER_OK = {
    "id": "ORDER-1",
    "links": [
        {"rel": "self", "href": "https://x/self"},
        {"rel": "approve", "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-1"},
    ],
}

_CAPTURE_COMPLETED = {
    "status": "COMPLETED",
    "purchase_units": [
        {"payments": {"captures": [
            {"seller_receivable_breakdown": {"paypal_fee": {"value": "0.50"}}}
        ]}}
    ],
}


# ── create_order ───────────────────────────────────────────────
def test_create_order_success_jpy_integer():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(201, _ORDER_OK)) as p:
        out = svc.create_order("sandbox", "id", "sec", 1000, "JPY", "INV-1",
                               "https://app/return", "https://app/cancel")
    assert out["ok"] is True
    assert out["order_id"] == "ORDER-1"
    assert "checkoutnow" in out["approval_url"]
    # JPY はゼロ小数通貨＝整数文字列で送る
    _, kwargs = p.call_args
    amount = kwargs["json"]["purchase_units"][0]["amount"]
    assert amount["value"] == "1000"
    assert amount["currency_code"] == "JPY"


def test_create_order_usd_two_decimals():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(201, _ORDER_OK)) as p:
        svc.create_order("sandbox", "id", "sec", 10, "USD", None, "https://r", "https://c")
    _, kwargs = p.call_args
    assert kwargs["json"]["purchase_units"][0]["amount"]["value"] == "10.00"


def test_create_order_token_fail_returns_401():
    with patch.object(svc, "_get_token", return_value=None):
        out = svc.create_order("sandbox", "id", "bad", 1000, "JPY", "INV-1",
                               "https://r", "https://c")
    assert out["ok"] is False
    assert out["status_code"] == 401


def test_create_order_http_error_status():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(400, {"name": "INVALID_REQUEST"})):
        out = svc.create_order("sandbox", "id", "sec", 1000, "JPY", "INV-1",
                               "https://r", "https://c")
    assert out["ok"] is False
    assert out["status_code"] == 400


# ── capture_order ──────────────────────────────────────────────
def test_capture_order_completed_extracts_fee():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(201, _CAPTURE_COMPLETED)):
        out = svc.capture_order("sandbox", "id", "sec", "ORDER-1")
    assert out["ok"] is True
    assert out["captured"] is True
    assert out["fee"] == "0.50"


def test_capture_order_not_approved_422_not_captured():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(422, {"name": "UNPROCESSABLE_ENTITY"})):
        out = svc.capture_order("sandbox", "id", "sec", "ORDER-1")
    assert out["ok"] is True
    assert out["captured"] is False
    assert out["status_code"] == 422


def test_capture_order_pending_not_completed():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(201, {"status": "PENDING"})):
        out = svc.capture_order("sandbox", "id", "sec", "ORDER-1")
    assert out["captured"] is False


def test_capture_order_token_fail_returns_401():
    with patch.object(svc, "_get_token", return_value=None):
        out = svc.capture_order("sandbox", "id", "bad", "ORDER-1")
    assert out["ok"] is False
    assert out["status_code"] == 401


# ── 金額整形 ────────────────────────────────────────────────────
def test_fmt_amount_zero_decimal_currency():
    assert svc._fmt_amount(1000, "JPY") == "1000"
    assert svc._fmt_amount("1500.4", "JPY") == "1500"


def test_fmt_amount_two_decimal_currency():
    assert svc._fmt_amount(10, "USD") == "10.00"
    assert svc._fmt_amount("9.5", "EUR") == "9.50"
